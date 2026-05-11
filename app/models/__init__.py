"""
数据模型层
原生APP和PWA共用同一套数据模型
"""

from app import db
from .user import User
from .analysis import AnalysisHistory

__all__ = ['User', 'AnalysisHistory', 'db']
