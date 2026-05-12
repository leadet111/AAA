"""
数据模型层
原生APP和PWA共用同一套数据模型
"""

from app import db
from .user import User
from .analysis import AnalysisHistory
from .membership import (
    MembershipTier, UserMembership, UserPoint, PointTransaction, Invitation
)
from .affiliate import ProductLink
from .analytics import UserEvent, DailyStats

__all__ = [
    'db',
    'User', 'AnalysisHistory',
    'MembershipTier', 'UserMembership', 'UserPoint', 'PointTransaction', 'Invitation',
    'ProductLink',
    'UserEvent', 'DailyStats',
]
