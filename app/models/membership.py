"""
会员、积分、邀请关系模型
支撑变现体系：免费/高级推荐、affiliate 占位、邀请返利
"""

from datetime import datetime
from app import db


class MembershipTier(db.Model):
    """会员等级配置表（可运营后台调整）"""
    __tablename__ = 'membership_tiers'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    # 权益
    max_analyses_per_day = db.Column(db.Integer, default=3)       # 每日分析次数上限
    max_favorites = db.Column(db.Integer, default=10)            # 收藏上限
    can_see_advanced_recommendations = db.Column(db.Boolean, default=False)
    can_generate_share_card = db.Column(db.Boolean, default=False)
    can_see_affiliate_links = db.Column(db.Boolean, default=False)  # 是否展示商品外链
    affiliate_discount_rate = db.Column(db.Float, default=0.0)   # affiliate 佣金折扣率
    # 定价
    monthly_price_cny = db.Column(db.Integer, default=0)         # 月费，单位分
    yearly_price_cny = db.Column(db.Integer, default=0)          # 年费，单位分
    # 排序权重
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'limits': {
                'max_analyses_per_day': self.max_analyses_per_day,
                'max_favorites': self.max_favorites,
            },
            'features': {
                'advanced_recommendations': self.can_see_advanced_recommendations,
                'share_card': self.can_generate_share_card,
                'affiliate_links': self.can_see_affiliate_links,
            },
            'pricing': {
                'monthly': self.monthly_price_cny,
                'yearly': self.yearly_price_cny,
            } if self.monthly_price_cny > 0 or self.yearly_price_cny > 0 else None,
        }

    @classmethod
    def seed_defaults(cls):
        """初始化默认会员等级"""
        defaults = [
            {
                'code': 'free',
                'name': '免费版',
                'description': '每日3次基础分析，基础穿搭/发型推荐',
                'max_analyses_per_day': 3,
                'max_favorites': 10,
                'can_see_advanced_recommendations': False,
                'can_generate_share_card': False,
                'can_see_affiliate_links': False,
                'sort_order': 1,
            },
            {
                'code': 'premium',
                'name': '高级版',
                'description': '无限次分析、高级推荐、专属分享卡片、affiliate 优惠',
                'max_analyses_per_day': 9999,
                'max_favorites': 9999,
                'can_see_advanced_recommendations': True,
                'can_generate_share_card': True,
                'can_see_affiliate_links': True,
                'monthly_price_cny': 1980,    # 19.8元/月
                'yearly_price_cny': 16800,     # 168元/年
                'sort_order': 2,
            },
        ]
        for d in defaults:
            existing = cls.query.filter_by(code=d['code']).first()
            if not existing:
                db.session.add(cls(**d))
        db.session.commit()


class UserMembership(db.Model):
    """用户会员状态表"""
    __tablename__ = 'user_memberships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    tier_code = db.Column(db.String(20), db.ForeignKey('membership_tiers.code'), nullable=False, default='free')
    # 生效时间
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # null 表示永久/免费
    # 支付相关（预留）
    payment_status = db.Column(db.String(20), default='none')  # none / pending / paid / refunded
    # 统计
    total_analyses_today = db.Column(db.Integer, default=0)
    analysis_count_reset_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tier = db.relationship('MembershipTier', foreign_keys=[tier_code],
                           primaryjoin='UserMembership.tier_code == MembershipTier.code')

    def to_dict(self):
        tier_dict = self.tier.to_dict() if self.tier else None
        return {
            'tier': tier_dict,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active(),
            'usage_today': self.total_analyses_today,
        }

    def is_active(self):
        if self.tier_code == 'free':
            return True
        if self.expires_at is None:
            return True
        return self.expires_at > datetime.utcnow()

    def can_analyze_today(self):
        """检查今日是否还能继续分析"""
        if not self.is_active():
            return False
        # 重置每日计数
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if self.analysis_count_reset_at is None or self.analysis_count_reset_at < today:
            self.total_analyses_today = 0
            self.analysis_count_reset_at = datetime.utcnow()
        tier = MembershipTier.query.filter_by(code=self.tier_code).first()
        if not tier:
            return False
        return self.total_analyses_today < tier.max_analyses_per_day

    def increment_analysis(self):
        self.total_analyses_today += 1
        db.session.commit()

    @classmethod
    def get_or_create(cls, user_id):
        um = cls.query.filter_by(user_id=user_id).first()
        if not um:
            um = cls(user_id=user_id, tier_code='free')
            db.session.add(um)
            db.session.commit()
        return um


class UserPoint(db.Model):
    """用户积分账户"""
    __tablename__ = 'user_points'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    balance = db.Column(db.Integer, default=0)
    total_earned = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'balance': self.balance,
            'total_earned': self.total_earned,
            'total_spent': self.total_spent,
        }

    @classmethod
    def get_or_create(cls, user_id):
        up = cls.query.filter_by(user_id=user_id).first()
        if not up:
            up = cls(user_id=user_id)
            db.session.add(up)
            db.session.commit()
        return up

    def add_points(self, amount, reason=''):
        self.balance += amount
        self.total_earned += amount
        db.session.commit()
        # 记录流水
        PointTransaction.record(self.user_id, amount, 'earn', reason)

    def spend_points(self, amount, reason=''):
        if self.balance < amount:
            return False
        self.balance -= amount
        self.total_spent += amount
        db.session.commit()
        PointTransaction.record(self.user_id, -amount, 'spend', reason)
        return True


class PointTransaction(db.Model):
    """积分流水"""
    __tablename__ = 'point_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)  # 正数收入，负数支出
    type = db.Column(db.String(20), nullable=False)  # earn / spend / refund
    reason = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def record(cls, user_id, amount, type_, reason=''):
        tx = cls(user_id=user_id, amount=amount, type=type_, reason=reason)
        db.session.add(tx)
        db.session.commit()
        return tx


class Invitation(db.Model):
    """邀请关系表"""
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    invitee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    invite_code = db.Column(db.String(20), nullable=False, index=True)
    status = db.Column(db.String(20), default='pending')  # pending / registered / first_analyzed / rewarded
    # 奖励
    points_rewarded_to_inviter = db.Column(db.Integer, default=0)
    points_rewarded_to_invitee = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rewarded_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('invitee_id', name='uq_invitation_invitee'),
    )

    def to_dict(self):
        return {
            'inviter_id': self.inviter_id,
            'invitee_id': self.invitee_id,
            'invite_code': self.invite_code,
            'status': self.status,
            'points_to_inviter': self.points_rewarded_to_inviter,
            'points_to_invitee': self.points_rewarded_to_invitee,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def get_invite_code(cls, user_id):
        """生成/获取用户的固定邀请码（基于 user_id 确定性生成）"""
        import hashlib
        # 基于 user_id 生成固定 6 位邀请码
        raw = hashlib.sha256(f"style_invite_{user_id}_salt".encode()).hexdigest().upper()
        code = raw[:6]
        # 确保纯数字字母且不含易混淆字符
        confusing = '0O1IL'
        for c in confusing:
            code = code.replace(c, 'X')
        return code

    @classmethod
    def resolve_inviter_from_code(cls, invite_code):
        """从邀请码反推邀请人 user_id（暴力匹配，生产环境可优化）"""
        # 简单方案：检查最近1000个用户的邀请码
        from app.models import User
        users = User.query.order_by(User.id.desc()).limit(2000).all()
        for u in users:
            if cls.get_invite_code(u.id) == invite_code.upper():
                return u.id
        return None

    @classmethod
    def create_invitation(cls, inviter_id, invitee_id, invite_code):
        # 检查是否已存在
        existing = cls.query.filter_by(invitee_id=invitee_id).first()
        if existing:
            return existing
        inv = cls(inviter_id=inviter_id, invitee_id=invitee_id, invite_code=invite_code, status='registered')
        db.session.add(inv)
        db.session.commit()
        return inv

    @classmethod
    def complete_reward(cls, invitation_id, inviter_points=50, invitee_points=20):
        """完成邀请奖励发放"""
        inv = cls.query.get(invitation_id)
        if not inv or inv.status == 'rewarded':
            return None
        inviter_wallet = UserPoint.get_or_create(inv.inviter_id)
        invitee_wallet = UserPoint.get_or_create(inv.invitee_id)
        inviter_wallet.add_points(inviter_points, '邀请奖励')
        invitee_wallet.add_points(invitee_points, '被邀请奖励')
        inv.status = 'rewarded'
        inv.points_rewarded_to_inviter = inviter_points
        inv.points_rewarded_to_invitee = invitee_points
        inv.rewarded_at = datetime.utcnow()
        db.session.commit()
        return inv
