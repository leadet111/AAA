"""
用户 API v1
用户数据管理、偏好设置
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app.models import User


@api_v1.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """
    获取用户公开信息
    """
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@api_v1.route('/users/me/favorites', methods=['GET', 'POST'])
@jwt_required()
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
    
    if request.method == 'GET':
        # 预留：从数据库查询收藏
        return jsonify({'items': [], 'total': 0})
    
    # POST
    data = request.get_json() or {}
    # 预留：保存收藏逻辑
    return jsonify({'success': True, 'message': '收藏成功'})


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
