"""
用户模型
支持 PWA 游客模式和原生APP注册用户
新增：gender 性别字段（AI自动识别）
"""

from datetime import datetime
from app import db


class User(db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    
    # 形象档案（可手动维护，也可由AI分析自动填充）
    face_shape = db.Column(db.String(20), nullable=True)
    body_type = db.Column(db.String(20), nullable=True)
    skin_tone = db.Column(db.String(20), nullable=True)
    height = db.Column(db.Integer, nullable=True)  # cm
    weight = db.Column(db.Integer, nullable=True)  # kg
    
    # AI识别的性别（male/female/unisex/unknown）
    gender = db.Column(db.String(10), nullable=True)
    
    # 用户偏好
    style_preference = db.Column(db.String(50), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # 关系
    analyses = db.relationship('AnalysisHistory', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'phone': self.phone,
            'avatar_url': self.avatar_url,
            'profile': {
                'face_shape': self.face_shape,
                'body_type': self.body_type,
                'skin_tone': self.skin_tone,
                'height': self.height,
                'weight': self.weight,
                'gender': self.gender,
            },
            'style_preference': self.style_preference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def create_guest():
        """创建游客用户（PWA未登录时使用）"""
        user = User()
        db.session.add(user)
        db.session.commit()
        return user
