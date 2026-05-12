"""
认证 API
支持：游客登录、手机号登录、JWT Token 刷新、游客转正、积分初始化
原生APP和PWA共用同一套认证体系
"""

from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app import db
from app.models import User
from app.models.membership import UserMembership, UserPoint, Invitation
from app.models.analytics import DailyStats


@api_v1.route('/auth/guest', methods=['POST'])
def guest_login():
    """
    游客登录（无需注册）
    PWA 首次访问时自动调用
    新增：自动初始化会员状态和积分账户
    ---
    responses:
      200:
        description: 返回游客 token 和用户信息
    """
    user = User.create_guest()
    token = create_access_token(identity=str(user.id))
    
    # 初始化会员状态（免费版）
    UserMembership.get_or_create(user.id)
    UserPoint.get_or_create(user.id)
    
    # 统计
    stats = DailyStats.get_or_create_today()
    stats.new_guests += 1
    db.session.commit()
    
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
    invite_code = data.get('invite_code', '').strip().upper()
    
    if not phone:
        return jsonify({'error': '手机号不能为空'}), 400
    
    user = User.query.filter_by(phone=phone).first()
    is_new = False
    if not user:
        user = User(phone=phone)
        db.session.add(user)
        db.session.commit()
        is_new = True
    
    token = create_access_token(identity=str(user.id))
    
    # 初始化会员和积分
    UserMembership.get_or_create(user.id)
    UserPoint.get_or_create(user.id)
    
    # 处理邀请码
    if invite_code:
        from app.services.monetization import MonetizationService
        MonetizationService.use_invite_code(user.id, invite_code)
    
    # 统计
    if is_new:
        stats = DailyStats.get_or_create_today()
        stats.new_users += 1
        db.session.commit()
    
    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'is_guest': False,
        'is_new_user': is_new,
    })


@api_v1.route('/auth/me', methods=['GET'])
@jwt_required(optional=True)
def get_current_user():
    """
    获取当前用户信息
    新增：附带会员状态和积分余额
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
    
    # 查询会员和积分
    um = UserMembership.query.filter_by(user_id=user.id).first()
    wallet = UserPoint.query.filter_by(user_id=user.id).first()
    
    user_data = user.to_dict()
    user_data['membership'] = um.to_dict() if um else None
    user_data['points'] = wallet.to_dict() if wallet else None
    
    return jsonify({
        'logged_in': True,
        'user': user_data,
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


@api_v1.route('/auth/convert', methods=['POST'])
@jwt_required()
def convert_guest():
    """
    游客转正（绑定手机号）
    保留原有游客数据
    ---
    security:
      - Bearer: []
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    if not phone:
        return jsonify({'error': '手机号不能为空'}), 400
    
    # 检查手机号是否已被注册
    existing = User.query.filter_by(phone=phone).first()
    if existing and existing.id != user.id:
        return jsonify({'error': '该手机号已被绑定'}), 409
    
    user.phone = phone
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'message': '游客转正成功',
    })
