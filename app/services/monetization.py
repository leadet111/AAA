"""
变现业务逻辑层
处理会员升级、affiliate 链接注入、积分兑换、邀请奖励
"""

from datetime import datetime, timedelta
from app import db
from app.models.membership import (
    UserMembership, MembershipTier, UserPoint, PointTransaction, Invitation
)
from app.models.affiliate import ProductLink
from app.models.analytics import UserEvent, DailyStats


class MonetizationService:
    """变现服务"""

    @staticmethod
    def get_user_plan(user_id):
        """获取用户当前会员方案"""
        um = UserMembership.get_or_create(user_id)
        wallet = UserPoint.get_or_create(user_id)
        return {
            'membership': um.to_dict(),
            'points': wallet.to_dict(),
        }

    @staticmethod
    def upgrade_user(user_id, tier_code, duration_months=1):
        """
        升级用户会员（预留支付回调入口）
        实际项目中由支付回调调用
        """
        tier = MembershipTier.query.filter_by(code=tier_code, is_active=True).first()
        if not tier:
            return None, '会员等级不存在'

        um = UserMembership.get_or_create(user_id)
        um.tier_code = tier_code
        um.started_at = datetime.utcnow()
        um.expires_at = datetime.utcnow() + timedelta(days=30 * duration_months)
        um.payment_status = 'paid'
        db.session.commit()

        # 埋点
        UserEvent.track(
            user_id=user_id,
            event_type='membership_upgrade',
            data={'tier': tier_code, 'months': duration_months},
        )

        # 更新今日统计
        stats = DailyStats.get_or_create_today()
        stats.revenue_cents += (tier.monthly_price_cny if duration_months == 1 else tier.yearly_price_cny)
        db.session.commit()

        return um.to_dict(), None

    @staticmethod
    def downgrade_expired_users():
        """将过期会员降级为免费版（可放在定时任务中）"""
        expired = UserMembership.query.filter(
            UserMembership.tier_code != 'free',
            UserMembership.expires_at < datetime.utcnow()
        ).all()
        for um in expired:
            um.tier_code = 'free'
            um.payment_status = 'none'
        db.session.commit()
        return len(expired)

    @staticmethod
    def inject_affiliate(result, user_id, analysis_type):
        """
        在分析结果中注入 affiliate 商品推荐
        返回带 affiliate 字段的结果副本
        """
        um = UserMembership.get_or_create(user_id)
        is_premium = um.tier_code != 'free' and um.is_active()

        # 提取用户特征
        traits = result.get('traits', {})
        user_traits = {
            'face_shape': traits.get('faceShape'),
            'body_type': traits.get('bodyType'),
            'skin_tone': traits.get('skinTone'),
        }

        categories = []
        if analysis_type in ('outfit', 'full'):
            categories.append('outfit')
        if analysis_type in ('hair', 'full'):
            categories.append('hair')

        affiliate_data = {}
        for cat in categories:
            products = ProductLink.match_for_user(
                category=cat,
                user_traits=user_traits,
                is_premium=is_premium,
                limit=3,
            )
            affiliate_data[cat] = [p.to_dict(include_affiliate=is_premium) for p in products]

        # 在结果中追加 affiliate 区块
        result_with_affiliate = dict(result)
        result_with_affiliate['affiliate'] = affiliate_data
        result_with_affiliate['upgrade_hint'] = None if is_premium else {
            'message': '高级会员可查看专属优惠商品链接',
            'action': 'upgrade',
        }
        return result_with_affiliate

    @staticmethod
    def generate_invite_data(user_id):
        """生成用户的邀请数据"""
        from app.models import User
        user = User.query.get(user_id)
        if not user:
            return None

        # 生成邀请码
        invite_code = Invitation.get_invite_code(user_id)
        # 查询已邀请人数
        invited_count = Invitation.query.filter_by(inviter_id=user_id).count()
        # 查询已获奖励积分
        wallet = UserPoint.get_or_create(user_id)

        return {
            'invite_code': invite_code,
            'invited_count': invited_count,
            'points_earned_from_invite': wallet.total_earned,  # 简化，实际应查流水
            'reward_rules': {
                'inviter_get': 50,
                'invitee_get': 20,
                'threshold': '被邀请人完成首次分析后发放',
            }
        }

    @staticmethod
    def use_invite_code(invitee_id, invite_code):
        """用户使用邀请码注册"""
        invite_code = invite_code.strip().upper()
        # 反推邀请人
        inviter_id = Invitation.resolve_inviter_from_code(invite_code)
        if not inviter_id:
            return None, '邀请码无效'
        if inviter_id == invitee_id:
            return None, '不能使用自己的邀请码'
        # 检查是否已被使用
        existing = Invitation.query.filter_by(invitee_id=invitee_id).first()
        if existing:
            return None, '您已经使用过邀请码'

        # 创建邀请关系
        inv = Invitation.create_invitation(inviter_id, invitee_id, invite_code)

        # 给被邀请人即时奖励（注册即得）
        invitee_wallet = UserPoint.get_or_create(invitee_id)
        invitee_wallet.add_points(20, '使用邀请码注册')

        # 埋点
        UserEvent.track(
            user_id=invitee_id,
            event_type='invite_code_used',
            data={'inviter_id': inviter_id, 'code': invite_code},
        )
        stats = DailyStats.get_or_create_today()
        stats.invite_codes_used += 1
        db.session.commit()

        return inv.to_dict(), None

    @staticmethod
    def check_and_reward_first_analysis(user_id):
        """检查被邀请人是否完成首次分析，触发邀请人奖励"""
        inv = Invitation.query.filter_by(invitee_id=user_id, status='registered').first()
        if not inv:
            return
        inv.status = 'first_analyzed'
        db.session.commit()

        # 发放邀请人奖励
        inviter_wallet = UserPoint.get_or_create(inv.inviter_id)
        inviter_wallet.add_points(50, '邀请的好友完成首次分析')
        inv.status = 'rewarded'
        inv.rewarded_at = datetime.utcnow()
        inv.points_rewarded_to_inviter = 50
        inv.points_rewarded_to_invitee = 20
        db.session.commit()

        UserEvent.track(
            user_id=inv.inviter_id,
            event_type='invite_rewarded',
            data={'invitee_id': user_id, 'points': 50},
        )

    @staticmethod
    def spend_points_for_analysis(user_id):
        """用积分兑换一次额外分析（当免费次数用完时）"""
        COST = 30  # 每次30积分
        wallet = UserPoint.get_or_create(user_id)
        if wallet.spend_points(COST, '兑换额外分析次数'):
            return True, None
        return False, f'积分不足（需要 {COST} 积分）'
