"""
通用工具装饰器：付费墙、频率限制、游客转正
"""

from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.membership import UserMembership, MembershipTier


def require_premium(feature=None):
    """
    付费墙装饰器
    检查用户是否为高级会员，否则返回 402 升级提示
    :param feature: 功能标识，用于返回具体的升级文案
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = int(get_jwt_identity())
            um = UserMembership.get_or_create(user_id)

            if not um.is_active() or um.tier_code == 'free':
                return jsonify({
                    'error': 'PREMIUM_REQUIRED',
                    'message': '此功能需要高级会员',
                    'feature': feature or fn.__name__,
                    'upgrade': {
                        'title': '升级高级版',
                        'subtitle': '解锁无限分析、高级推荐、专属分享卡片',
                        'monthly_price': 1980,
                        'yearly_price': 16800,
                        'currency': 'CNY',
                    }
                }), 402

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_active_membership():
    """
    检查会员是否有效（包括免费版）
    用于任何需要登录态的接口
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = int(get_jwt_identity())
            um = UserMembership.get_or_create(user_id)
            if not um.is_active():
                return jsonify({
                    'error': 'MEMBERSHIP_EXPIRED',
                    'message': '会员已过期，请续费',
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def analysis_limit():
    """
    分析次数限制装饰器
    根据会员等级限制每日 analyze 调用次数
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required(optional=True)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            if user_id:
                um = UserMembership.get_or_create(int(user_id))
                if not um.can_analyze_today():
                    tier = MembershipTier.query.filter_by(code=um.tier_code).first()
                    limit = tier.max_analyses_per_day if tier else 3
                    return jsonify({
                        'error': 'DAILY_LIMIT_REACHED',
                        'message': f'今日分析次数已用完（{limit}次）',
                        'usage_today': um.total_analyses_today,
                        'limit': limit,
                        'upgrade': {
                            'title': '解锁无限分析',
                            'subtitle': '高级会员每日不限次数',
                        }
                    }), 429
                # 计数+1
                um.increment_analysis()

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def track_event(event_type, data_key=None):
    """
    自动埋点装饰器
    在接口调用成功后记录事件
    :param event_type: 事件类型
    :param data_key: 从请求JSON中取该字段作为事件数据
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            try:
                from app.models.analytics import UserEvent
                user_id = None
                session_id = None
                try:
                    from flask_jwt_extended import get_jwt_identity
                    uid = get_jwt_identity()
                    if uid:
                        user_id = int(uid)
                except Exception:
                    pass

                # 尝试从请求头取 session_id（前端生成）
                session_id = request.headers.get('X-Session-ID')

                event_data = None
                if data_key and request.is_json:
                    body = request.get_json(silent=True) or {}
                    event_data = body.get(data_key)

                UserEvent.track(
                    user_id=user_id,
                    session_id=session_id,
                    event_type=event_type,
                    data=event_data,
                    client_type=request.headers.get('X-Client-Type', 'pwa'),
                    page_path=request.path,
                    ip_address=request.remote_addr,
                )
            except Exception:
                # 埋点失败不影响主业务
                pass
            return result
        return wrapper
    return decorator
