"""
认证 API
支持：游客登录、手机号登录、JWT Token 刷新
原生APP和PWA共用同一套认证体系
"""

from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app import db
from app.models import User


@api_v1.route('/auth/guest', methods=['POST'])
def guest_login():
    """
    游客登录（无需注册）
    PWA 首次访问时自动调用
    ---
    responses:
      200:
        description: 返回游客 token 和用户信息
    """
    user = User.create_guest()
    token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'is_guest': True,
    })


@api_v1.route('/auth/phone', methods=['POST'])
def phone_login():
    """
    手机号登录（预留）
    原生APP通常使用手机号 + 验证码登录
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            phone:
              type: string
            code:
              type: string
    """
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    # code = data.get('code', '')  # 验证码逻辑预留
    
    if not phone:
        return jsonify({'error': '手机号不能为空'}), 400
    
    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(phone=phone)
        db.session.add(user)
        db.session.commit()
    
    token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'is_guest': False,
    })


@api_v1.route('/auth/me', methods=['GET'])
@jwt_required(optional=True)
def get_current_user():
    """
    获取当前用户信息
    ---
    security:
      - Bearer: []
    """
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({'logged_in': False}), 200
    
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    return jsonify({
        'logged_in': True,
        'user': user.to_dict(),
    })


@api_v1.route('/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    更新用户形象档案
    原生APP和PWA都可以调用
    ---
    security:
      - Bearer: []
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    data = request.get_json() or {}
    
    # 允许更新的字段
    allowed_fields = ['username', 'face_shape', 'body_type', 'skin_tone', 
                      'height', 'weight', 'style_preference']
    for field in allowed_fields:
        if field in data:
            setattr(user, field, data[field])
    
    db.session.commit()
    return jsonify({'user': user.to_dict()})
