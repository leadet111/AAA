"""
数据埋点 API
前端上报用户行为事件
"""

from flask import request, jsonify
from app.api.v1 import api_v1
from app.models.analytics import UserEvent, DailyStats
from flask_jwt_extended import jwt_required, get_jwt_identity


@api_v1.route('/events/track', methods=['POST'])
def track_event():
    """
    上报事件
    支持游客（通过 X-Session-ID 关联）和已登录用户
    """
    data = request.get_json() or {}
    event_type = data.get('event_type')
    event_data = data.get('data')
    page_path = data.get('page_path')
    device_info = data.get('device_info')
    session_id = data.get('session_id') or request.headers.get('X-Session-ID')

    if not event_type:
        return jsonify({'error': 'event_type 必填'}), 400

    user_id = None
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            user_id = int(uid)
    except Exception:
        pass

    event = UserEvent.track(
        user_id=user_id,
        session_id=session_id,
        event_type=event_type,
        data=event_data,
        client_type=request.headers.get('X-Client-Type', 'pwa'),
        page_path=page_path or request.path,
        device_info=device_info,
        ip_address=request.remote_addr,
    )

    return jsonify({'success': True, 'event_id': event.id})


@api_v1.route('/events/batch', methods=['POST'])
def track_events_batch():
    """
    批量上报事件（减少前端请求数）
    """
    data = request.get_json() or {}
    events = data.get('events', [])
    if not isinstance(events, list) or len(events) == 0:
        return jsonify({'error': 'events 必须为非空数组'}), 400
    if len(events) > 100:
        return jsonify({'error': '单次最多100条'}), 400

    user_id = None
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            user_id = int(uid)
    except Exception:
        pass

    session_id = request.headers.get('X-Session-ID')
    client_type = request.headers.get('X-Client-Type', 'pwa')

    created_ids = []
    for ev in events:
        event = UserEvent.track(
            user_id=user_id,
            session_id=session_id or ev.get('session_id'),
            event_type=ev.get('event_type'),
            data=ev.get('data'),
            client_type=client_type,
            page_path=ev.get('page_path'),
            device_info=ev.get('device_info'),
            ip_address=request.remote_addr,
        )
        created_ids.append(event.id)

    return jsonify({'success': True, 'count': len(created_ids), 'event_ids': created_ids})


@api_v1.route('/stats/today', methods=['GET'])
def get_today_stats():
    """
    获取今日运营数据（预留管理后台用，可加管理员权限校验）
    """
    stats = DailyStats.get_or_create_today()
    return jsonify({
        'date': stats.date.isoformat() if stats.date else None,
        'new_users': stats.new_users,
        'new_guests': stats.new_guests,
        'active_users': stats.active_users,
        'total_analyses': stats.total_analyses,
        'total_favorites': stats.total_favorites,
        'total_shares': stats.total_shares,
        'upgrade_clicks': stats.upgrade_clicks,
        'affiliate_clicks': stats.affiliate_clicks,
        'invite_codes_used': stats.invite_codes_used,
        'revenue_cents': stats.revenue_cents,
    })
