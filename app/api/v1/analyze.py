"""
分析 API v1
核心接口：上传图片 + 问卷 → 返回穿搭/发型推荐
兼容 PWA 和原生APP
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app import db
from app.models import User, AnalysisHistory
from app.services import StyleAnalyzer, StorageService

# 初始化分析引擎（单例）
analyzer = StyleAnalyzer()


@api_v1.route('/analyze', methods=['POST'])
@jwt_required(optional=True)
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
    
    # 保存分析历史
    record = AnalysisHistory.create_record(
        user_id=user_id,
        analysis_type=analysis_type,
        survey=survey,
        image_path=image_path,
        result=result,
        client_type=client_type,
    )
    
    return jsonify({
        'id': record.id,
        'result': result,
    })


# ============ 兼容旧版 PWA 路径 ============

def analyze_image_legacy():
    """
    兼容旧版 /api/analyze 路径（PWA前端当前使用）
    直接调用 v1 接口逻辑
    """
    data = request.get_json() or {}
    
    image_data = data.get('image')
    survey = data.get('survey', {})
    analysis_type = data.get('type', 'full')
    
    if not any([survey.get('faceShape'), survey.get('bodyType'), survey.get('skinTone')]):
        return jsonify({'needSurvey': True, 'message': '请补充基本信息'})
    
    # 保存图片
    image_path = None
    storage = StorageService(current_app.config)
    if image_data and isinstance(image_data, str) and image_data.startswith('data:image'):
        result = storage.save(image_data, folder='analysis')
        image_path = result['path']
    
    # 分析
    result = analyzer.analyze(survey, analysis_type)
    
    # 尝试保存记录（如果有游客token）
    from flask_jwt_extended import verify_jwt_in_request_optional
    try:
        verify_jwt_in_request_optional()
        user_id = get_jwt_identity()
        if user_id:
            AnalysisHistory.create_record(
                user_id=int(user_id),
                analysis_type=analysis_type,
                survey=survey,
                image_path=image_path,
                result=result,
                client_type='pwa',
            )
    except Exception:
        pass
    
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
