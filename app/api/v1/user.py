"""
用户 API v1
用户数据管理、偏好设置、收藏、affiliate 点击
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app.models import User
from app.models.membership import UserMembership, UserPoint
from app.models.affiliate import ProductLink
from app.utils.decorators import require_premium, require_active_membership, track_event


@api_v1.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """
    获取用户公开信息
    """
    user = User.query.get_or_404(user_id)
    data = user.to_dict()
    # 公开信息中不暴露手机号
    data.pop('phone', None)
    return jsonify(data)


@api_v1.route('/users/me/favorites', methods=['GET', 'POST'])
@jwt_required()
@require_active_membership()
def user_favorites():
    """
    用户收藏（穿搭方案/发型方案）
    GET: 获取收藏列表
    POST: 添加收藏
    ---
    security:
      - Bearer: []
    """
    user_id = int(get_jwt_identity())
    um = UserMembership.query.filter_by(user_id=user_id).first()
    
    if request.method == 'GET':
        from app.models.analysis import AnalysisHistory
        # 简单实现：收藏 = 用户标记为 favorite 的分析历史
        # 实际项目中应有独立的 favorites 表
        items = AnalysisHistory.query \
            .filter_by(user_id=user_id) \
            .order_by(AnalysisHistory.created_at.desc()) \
            .limit(50).all()
        return jsonify({
            'items': [item.to_dict(include_result=False) for item in items],
            'total': len(items),
        })
    
    # POST: 添加收藏（实际应保存到独立表，此处简化）
    data = request.get_json() or {}
    analysis_id = data.get('analysis_id')
    if not analysis_id:
        return jsonify({'error': 'analysis_id 必填'}), 400
    
    # 检查收藏上限
    tier = um.tier if um else None
    max_fav = tier.max_favorites if tier else 10
    current_count = AnalysisHistory.query.filter_by(user_id=user_id).count()
    if current_count >= max_fav:
        return jsonify({
            'error': 'FAVORITES_LIMIT_REACHED',
            'message': f'收藏已达上限（{max_fav}条）',
            'upgrade': {'title': '升级解锁更多收藏', 'subtitle': '高级会员无限收藏'},
        }), 402
    
    # 更新今日统计
    from app.models.analytics import DailyStats
    stats = DailyStats.get_or_create_today()
    stats.total_favorites += 1
    db.session.commit()
    
    return jsonify({'success': True, 'message': '收藏成功'})


@api_v1.route('/users/me/plan', methods=['GET'])
@jwt_required()
def get_user_plan():
    """
    获取用户完整方案（会员 + 积分）
    """
    user_id = int(get_jwt_identity())
    um = UserMembership.query.filter_by(user_id=user_id).first()
    wallet = UserPoint.query.filter_by(user_id=user_id).first()
    return jsonify({
        'membership': um.to_dict() if um else None,
        'points': wallet.to_dict() if wallet else None,
    })


@api_v1.route('/affiliate/products', methods=['GET'])
@jwt_required()
def list_affiliate_products():
    """
    获取当前用户匹配的商品推荐
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    category = request.args.get('category', 'outfit')
    um = UserMembership.get_or_create(user_id)
    is_premium = um.tier_code != 'free' and um.is_active()
    
    traits = {
        'face_shape': user.face_shape,
        'body_type': user.body_type,
        'skin_tone': user.skin_tone,
    }
    products = ProductLink.match_for_user(category, traits, is_premium=is_premium, limit=10)
    return jsonify({
        'items': [p.to_dict(include_affiliate=is_premium) for p in products],
        'is_premium': is_premium,
    })


@api_v1.route('/affiliate/click/<int:product_id>', methods=['POST'])
@jwt_required()
@track_event('affiliate_click')
def record_affiliate_click(product_id):
    """
    记录 affiliate 点击（用于统计和佣金追踪）
    """
    product = ProductLink.query.get(product_id)
    if not product:
        return jsonify({'error': '商品不存在'}), 404
    
    product.record_click()
    
    # 更新统计
    from app.models.analytics import DailyStats
    stats = DailyStats.get_or_create_today()
    stats.affiliate_clicks += 1
    db.session.commit()
    
    url = product._build_affiliate_url()
    return jsonify({'success': True, 'redirect_url': url, 'product_id': product_id})


@api_v1.route('/knowledge', methods=['GET'])
def get_knowledge_base():
    """
    获取穿搭知识库（只读）
    原生APP可调用此接口同步本地离线数据
    """
    from app.services import StyleAnalyzer
    a = StyleAnalyzer()
    return jsonify({
        'face_shapes': list(a.kb['face_shapes'].keys()),
        'body_types': list(a.kb['body_types'].keys()),
        'skin_tones': list(a.kb['skin_tones'].keys()),
        'version': '1.0.0',
    })
