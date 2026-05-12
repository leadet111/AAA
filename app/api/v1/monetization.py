"""
变现 / 会员 / 积分 API
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app.services.monetization import MonetizationService
from app.utils.decorators import require_premium, require_active_membership


@api_v1.route('/membership/plan', methods=['GET'])
@jwt_required()
def get_membership_plan():
    """
    获取当前用户的会员方案和积分余额
    """
    user_id = int(get_jwt_identity())
    plan = MonetizationService.get_user_plan(user_id)
    return jsonify(plan)


@api_v1.route('/membership/upgrade', methods=['POST'])
@jwt_required()
def upgrade_membership():
    """
    升级会员（预留：实际对接支付网关后由回调触发）
    当前仅模拟升级流程
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    tier_code = data.get('tier', 'premium')
    months = data.get('months', 1)

    result, error = MonetizationService.upgrade_user(user_id, tier_code, months)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True, 'membership': result})


@api_v1.route('/membership/tiers', methods=['GET'])
def list_membership_tiers():
    """
    获取所有可用会员等级（无需认证，供前端展示定价页）
    """
    from app.models.membership import MembershipTier
    tiers = MembershipTier.query.filter_by(is_active=True).order_by(MembershipTier.sort_order.asc()).all()
    return jsonify({'tiers': [t.to_dict() for t in tiers]})


@api_v1.route('/points/balance', methods=['GET'])
@jwt_required()
def get_points_balance():
    """
    获取积分余额
    """
    from app.models.membership import UserPoint
    user_id = int(get_jwt_identity())
    wallet = UserPoint.get_or_create(user_id)
    return jsonify(wallet.to_dict())


@api_v1.route('/points/transactions', methods=['GET'])
@jwt_required()
def list_point_transactions():
    """
    积分流水
    """
    from app.models.membership import PointTransaction
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = PointTransaction.query \
        .filter_by(user_id=user_id) \
        .order_by(PointTransaction.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [
            {
                'id': tx.id,
                'amount': tx.amount,
                'type': tx.type,
                'reason': tx.reason,
                'created_at': tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in pagination.items
        ],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@api_v1.route('/points/exchange/analysis', methods=['POST'])
@jwt_required()
def exchange_points_for_analysis():
    """
    用积分兑换一次额外分析
    """
    user_id = int(get_jwt_identity())
    ok, error = MonetizationService.spend_points_for_analysis(user_id)
    if not ok:
        return jsonify({'error': error}), 400
    return jsonify({'success': True, 'message': '兑换成功，今日额外获得1次分析机会'})
