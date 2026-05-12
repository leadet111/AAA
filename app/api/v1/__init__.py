"""
API v1 蓝图注册
所有接口兼容 PWA 和原生APP
"""

from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__)

# 导入各模块路由（必须在 Blueprint 创建之后）
from . import auth, analyze, user, monetization, invitation, analytics
