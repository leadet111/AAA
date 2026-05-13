"""
分析 API v1
核心接口：上传图片 + 问卷 → 返回穿搭/发型推荐
兼容 PWA 和原生APP
新增：AI性别识别、三种性别方案
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app import db
from app.models import User, AnalysisHistory, UserMembership, MembershipTier
from app.services import StyleAnalyzer, StorageService
from app.services.gender_recognition import recognize_gender, GenderRecognitionResult
from app.services.product_search import search_outfit_items, search_hair_products
from app.services.monetization import MonetizationService
from app.utils.decorators import analysis_limit, track_event

# 初始化分析引擎（单例）
analyzer = StyleAnalyzer()


def _inject_product_links(result: dict) -> dict:
    """
    为分析结果注入商品搜索链接
    每个穿搭单品和发型都会附带购买链接
    """
    schemes = result.get('genderSchemes', {})
    
    for scheme_key, scheme in schemes.items():
        # 穿搭商品链接
        if 'outfit' in scheme and 'items' in scheme['outfit']:
            for item in scheme['outfit']['items']:
                items_dict = item.get('items', {})
                if items_dict:
                    links = search_outfit_items(items_dict)
                    item['product_links'] = [l.to_dict() for l in links[:9]]
        
        # 穿搭备选商品链接
        if 'outfit' in scheme and 'other_choices' in scheme['outfit']:
            for choice in scheme['outfit']['other_choices']:
                links = search_outfit_items({'套装': choice.get('name', '')})
                choice['product_links'] = [l.to_dict() for l in links[:3]]
        
        # 发型商品链接
        if 'hair' in scheme and 'items' in scheme['hair']:
            for item in scheme['hair']['items']:
                hs_name = item.get('name', '')
                links = search_hair_products(hs_name)
                item['product_links'] = [l.to_dict() for l in links[:6]]
        
        # 发型备选商品链接
        if 'hair' in scheme and 'other_choices' in scheme['hair']:
            for choice in scheme['hair']['other_choices']:
                links = search_hair_products(choice.get('name', ''))
                choice['product_links'] = [l.to_dict() for l in links[:3]]
    
    return result


@api_v1.route('/analyze', methods=['POST'])
@jwt_required(optional=True)
@analysis_limit()
@track_event('analyze_complete', data_key='survey')
def analyze_image():
    """
    形象分析接口（v1）
    上传图片 + 问卷，返回穿搭/发型推荐（含三种性别方案）
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
              description: base64 编码的图片（可选，用于AI性别识别）
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
        description: 分析结果（含 detected_gender 和 genderSchemes）
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
    
    # 必须上传照片（AI性别识别需要面部数据）
    if not image_data or not isinstance(image_data, str) or not image_data.startswith('data:image'):
        return jsonify({
            'error': 'IMAGE_REQUIRED',
            'message': '请上传照片以获得AI性别识别和精准推荐',
            'hint': '上传正面清晰的头像或全身照，AI将自动分析你的性别特征并生成三种个性化方案'
        }), 400
    
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
    
    # ===== AI性别识别 =====
    gender_result = None
    if image_data and isinstance(image_data, str) and image_data.startswith('data:image'):
        try:
            gender_result = recognize_gender(image_data)
            # 更新用户档案中的性别（如果用户已登录且之前未设置）
            if user_id and gender_result and gender_result.gender in ('male', 'female'):
                user = User.query.get(user_id)
                if user and not user.gender:
                    user.gender = gender_result.gender
                    db.session.commit()
        except Exception as e:
            print(f'[Analyze] 性别识别失败: {e}')
            gender_result = GenderRecognitionResult('unknown', 0.0, 'error')
    
    # 如果无法识别，尝试从用户档案读取
    user_gender = 'unknown'
    if gender_result and gender_result.gender in ('male', 'female', 'unisex'):
        user_gender = gender_result.gender
    elif user_id:
        user = User.query.get(user_id)
        if user and user.gender:
            user_gender = user.gender
    
    # 执行分析（传入性别参数）
    result = analyzer.analyze(survey, analysis_type, user_gender)
    
    # 在结果中注入性别识别信息
    if gender_result:
        result['detected_gender'] = gender_result.to_dict()
    
    # 注入商品搜索链接
    result = _inject_product_links(result)
    
    # 注入 affiliate 商品推荐（如果用户有会员权益）
    if user_id:
        result = MonetizationService.inject_affiliate(result, user_id, analysis_type)
        MonetizationService.check_and_reward_first_analysis(user_id)
    
    # 保存分析历史
    record = AnalysisHistory.create_record(
        user_id=user_id,
        analysis_type=analysis_type,
        survey=survey,
        image_path=image_path,
        result=result,
        client_type=client_type,
        gender_result=gender_result,
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
    
    # 必须上传照片
    if not image_data or not isinstance(image_data, str) or not image_data.startswith('data:image'):
        return jsonify({
            'error': 'IMAGE_REQUIRED',
            'message': '请上传照片以获得AI性别识别和精准推荐',
            'hint': '上传正面清晰的头像或全身照，AI将自动分析你的性别特征并生成三种个性化方案'
        }), 400
    
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
    
    # ===== AI性别识别 =====
    gender_result = None
    if image_data and isinstance(image_data, str) and image_data.startswith('data:image'):
        try:
            gender_result = recognize_gender(image_data)
            if user_id and gender_result and gender_result.gender in ('male', 'female'):
                user = User.query.get(user_id)
                if user and not user.gender:
                    user.gender = gender_result.gender
                    db.session.commit()
        except Exception as e:
            print(f'[AnalyzeLegacy] 性别识别失败: {e}')
            gender_result = GenderRecognitionResult('unknown', 0.0, 'error')
    
    user_gender = 'unknown'
    if gender_result and gender_result.gender in ('male', 'female', 'unisex'):
        user_gender = gender_result.gender
    elif user_id:
        user = User.query.get(user_id)
        if user and user.gender:
            user_gender = user.gender
    
    # 分析
    result = analyzer.analyze(survey, analysis_type, user_gender)
    
    if gender_result:
        result['detected_gender'] = gender_result.to_dict()
    
    # 注入商品搜索链接
    result = _inject_product_links(result)
    
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
            gender_result=gender_result,
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
