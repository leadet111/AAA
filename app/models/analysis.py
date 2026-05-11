"""
分析历史模型
记录每次穿搭/发型分析结果，支持用户回顾和推荐优化
"""

from datetime import datetime
from app import db
import json


class AnalysisHistory(db.Model):
    """分析历史表"""
    __tablename__ = 'analysis_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # 分析类型
    analysis_type = db.Column(db.String(20), nullable=False)  # outfit / hair / full
    
    # 输入数据（JSON存储）
    survey_data = db.Column(db.Text, nullable=True)  # 问卷数据
    image_path = db.Column(db.String(500), nullable=True)  # 上传图片路径
    
    # 分析结果（JSON存储）
    result_data = db.Column(db.Text, nullable=False)
    
    # 特征标签（用于快速检索和推荐）
    face_shape = db.Column(db.String(20), nullable=True)
    body_type = db.Column(db.String(20), nullable=True)
    skin_tone = db.Column(db.String(20), nullable=True)
    
    # 元数据
    client_type = db.Column(db.String(20), default='pwa')  # pwa / ios / android
    ip_address = db.Column(db.String(45), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self, include_result=True):
        data = {
            'id': self.id,
            'analysis_type': self.analysis_type,
            'traits': {
                'face_shape': self.face_shape,
                'body_type': self.body_type,
                'skin_tone': self.skin_tone,
            },
            'client_type': self.client_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_result and self.result_data:
            data['result'] = json.loads(self.result_data)
        return data

    @staticmethod
    def create_record(user_id, analysis_type, survey, image_path, result, client_type='pwa'):
        """创建分析记录"""
        record = AnalysisHistory(
            user_id=user_id,
            analysis_type=analysis_type,
            survey_data=json.dumps(survey) if survey else None,
            image_path=image_path,
            result_data=json.dumps(result, ensure_ascii=False),
            face_shape=survey.get('faceShape'),
            body_type=survey.get('bodyType'),
            skin_tone=survey.get('skinTone'),
            client_type=client_type,
        )
        db.session.add(record)
        db.session.commit()
        return record
