"""
分析 API v1
核心接口：上传图片 + 问卷 → 返回穿搭/发型推荐
兼容 PWA 和原生APP
新增：付费墙控制、affiliate 商品注入、埋点、邀请奖励触发
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app import db
from app.models import User, AnalysisHistory, UserMembership, MembershipTier
from app.services import StyleAnalyzer, StorageService
from app.services.monetization import MonetizationService
from app.utils.decorators import analysis_limit, track_event

# 初始化分析引擎（单例）
analyzer = StyleAnalyzer()


@api_v1.route('/analyze', methods=['POST'])
@jwt_required(optional=True)
@analysis_limit()
@track_event('analyze_complete', data_key='survey')
def analyze_image():
    """
    形象分析接口（v1）
    上传图片 + 问卷，返回穿搭/发型推荐
    ---
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            image:
              type: string
              description: base64 编码的图片（可选）
            survey:
              type: object
              required: true
            type:
              type: string
              enum: [outfit, hair, full]
            client_type:
              type: string
              enum: [pwa, ios, android]
    responses:
      200:
        description: 分析结果
      402:
        description: 需要升级会员
      429:
        description: 每日次数已用完
    """
    data = request.get_json() or {}
    image_data = data.get('image')
    survey = data.get('survey', {})
    analysis_type = data.get('type', 'full')
    client_type = data.get('client_type', request.headers.get('X-Client-Type', 'pwa'))
    
    # 验证必填
    required = ['faceShape', 'bodyType', 'skinTone']
    missing = [r for r in required if not survey.get(r)]
    if missing:
        return jsonify({'error': f'缺少必填项: {", ".join(missing)}'}), 400
    
    # 获取用户（游客或注册用户）
    user_id = None
    jwt_id = get_jwt_identity()
    if jwt_id:
        user_id = int(jwt_id)
    
    # 保存图片
    image_path = None
    storage = StorageService(current_app.config)
    if image_data and isinstance(image_data, str) and image_data.startswith('data:image'):
        result = storage.save(image_data, folder='analysis')
        image_path = result['path']
    
    # 执行分析
    result = analyzer.analyze(survey, analysis_type)
    
    # 注入 affiliate 商品推荐（如果用户有会员权益）
    if user_id:
        result = MonetizationService.inject_affiliate(result, user_id, analysis_type)
        # 触发邀请奖励检查（首次分析完成）
        MonetizationService.check_and_reward_first_analysis(user_id)
    
    # 保存分析历史
    record = AnalysisHistory.create_record(
        user_id=user_id,
        analysis_type=analysis_type,
        survey=survey,
        image_path=image_path,
        result=result,
        client_type=client_type,
    )
    
    # 更新今日统计
    from app.models.analytics import DailyStats
    stats = DailyStats.get_or_create_today()
    stats.total_analyses += 1
    db.session.commit()
    
    return jsonify({
        'id': record.id,
        'result': result,
    })


# ============ 兼容旧版 PWA 路径 ============

def analyze_image_legacy():
    """
    兼容旧版 /api/analyze 路径（PWA前端当前使用）
    直接调用 v1 接口逻辑（复用付费墙和affiliate逻辑）
    """
    data = request.get_json() or {}
    
    image_data = data.get('image')
    survey = data.get('survey', {})
    analysis_type = data.get('type', 'full')
    
    if not any([survey.get('faceShape'), survey.get('bodyType'), survey.get('skinTone')]):
        return jsonify({'needSurvey': True, 'message': '请补充基本信息'})
    
    # 付费墙检查：游客每日限3次（通过 session 关联）
    user_id = None
    jwt_id = None
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request(optional=True)
        jwt_id = get_jwt_identity()
        if jwt_id:
            user_id = int(jwt_id)
    except Exception:
        pass

    if user_id:
        um = UserMembership.get_or_create(user_id)
        if not um.can_analyze_today():
            tier = MembershipTier.query.filter_by(code=um.tier_code).first()
            limit = tier.max_analyses_per_day if tier else 3
            return jsonify({
                'error': 'DAILY_LIMIT_REACHED',
                'message': f'今日分析次数已用完（{limit}次）',
                'upgrade': {'title': '解锁无限分析', 'subtitle': '高级会员不限次数'}
            }), 429
        um.increment_analysis()
    
    # 保存图片
    image_path = None
    storage = StorageService(current_app.config)
    if image_data and isinstance(image_data, str) and image_data.startswith('data:image'):
        result = storage.save(image_data, folder='analysis')
        image_path = result['path']
    
    # 分析
    result = analyzer.analyze(survey, analysis_type)
    
    # 注入 affiliate（注册用户）
    if user_id:
        result = MonetizationService.inject_affiliate(result, user_id, analysis_type)
        MonetizationService.check_and_reward_first_analysis(user_id)
    
    # 保存记录
    if user_id:
        AnalysisHistory.create_record(
            user_id=user_id,
            analysis_type=analysis_type,
            survey=survey,
            image_path=image_path,
            result=result,
            client_type='pwa',
        )
    
    # 更新今日统计
    from app.models.analytics import DailyStats
    stats = DailyStats.get_or_create_today()
    stats.total_analyses += 1
    db.session.commit()
    
    return jsonify(result)


@api_v1.route('/analyze/history', methods=['GET'])
@jwt_required()
def get_analysis_history():
    """
    获取用户的分析历史
    ---
    security:
      - Bearer: []
    """
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = AnalysisHistory.query \
        .filter_by(user_id=user_id) \
        .order_by(AnalysisHistory.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [item.to_dict(include_result=False) for item in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@api_v1.route('/analyze/history/<int:history_id>', methods=['GET'])
@jwt_required()
def get_history_detail(history_id):
    """
    获取单次分析详情
    ---
    security:
      - Bearer: []
    """
    user_id = int(get_jwt_identity())
    record = AnalysisHistory.query.filter_by(id=history_id, user_id=user_id).first()
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    return jsonify(record.to_dict(include_result=True))
