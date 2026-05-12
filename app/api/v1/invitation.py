"""
邀请返利 / 分享 API
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1
from app.services.monetization import MonetizationService
from app.models.membership import Invitation


@api_v1.route('/invite/info', methods=['GET'])
@jwt_required()
def get_invite_info():
    """
    获取用户的邀请信息（邀请码、已邀请人数、已获奖励）
    """
    user_id = int(get_jwt_identity())
    data = MonetizationService.generate_invite_data(user_id)
    if not data:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify(data)


@api_v1.route('/invite/use', methods=['POST'])
@jwt_required()
def use_invite_code():
    """
    使用邀请码（被邀请人调用）
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()

    if not code:
        return jsonify({'error': '邀请码不能为空'}), 400

    result, error = MonetizationService.use_invite_code(user_id, code)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True, 'invitation': result})


@api_v1.route('/invite/history', methods=['GET'])
@jwt_required()
def get_invite_history():
    """
    获取邀请历史
    """
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = Invitation.query \
        .filter_by(inviter_id=user_id) \
        .order_by(Invitation.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [inv.to_dict() for inv in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })
