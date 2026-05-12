"""
用户行为数据埋点模型
为后续数据分析和推荐优化做准备
"""

from datetime import datetime
from app import db
import json


class UserEvent(db.Model):
    """用户行为事件表"""
    __tablename__ = 'user_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    # 游客可用 session_id 关联
    session_id = db.Column(db.String(64), nullable=True, index=True)

    event_type = db.Column(db.String(50), nullable=False, index=True)
    # 预定义事件：
    #   page_view, survey_start, survey_complete,
    #   analyze_start, analyze_complete, analyze_result_view,
    #   recommendation_click, favorite_add, favorite_remove,
    #   share_click, upgrade_prompt_view, upgrade_click,
    #   invite_share, invite_code_used, affiliate_click

    event_data = db.Column(db.Text, nullable=True)  # JSON 扩展字段

    # 上下文
    client_type = db.Column(db.String(20), default='pwa')  # pwa / ios / android
    page_path = db.Column(db.String(200), nullable=True)
    referrer = db.Column(db.String(500), nullable=True)

    # 设备/环境（前端可上报）
    device_info = db.Column(db.Text, nullable=True)  # JSON: {os, screen, lang}

    # IP（后端自动记录）
    ip_address = db.Column(db.String(45), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @classmethod
    def track(cls, user_id=None, session_id=None, event_type=None,
              data=None, client_type='pwa', page_path=None,
              device_info=None, ip_address=None):
        """记录事件"""
        event = cls(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            event_data=json.dumps(data, ensure_ascii=False) if data else None,
            client_type=client_type,
            page_path=page_path,
            device_info=json.dumps(device_info, ensure_ascii=False) if device_info else None,
            ip_address=ip_address,
        )
        db.session.add(event)
        db.session.commit()
        return event

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'event_type': self.event_type,
            'data': json.loads(self.event_data) if self.event_data else None,
            'client_type': self.client_type,
            'page_path': self.page_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DailyStats(db.Model):
    """每日聚合统计（供运营后台快速查看）"""
    __tablename__ = 'daily_stats'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, index=True)

    new_users = db.Column(db.Integer, default=0)
    new_guests = db.Column(db.Integer, default=0)
    active_users = db.Column(db.Integer, default=0)
    total_analyses = db.Column(db.Integer, default=0)
    total_favorites = db.Column(db.Integer, default=0)
    total_shares = db.Column(db.Integer, default=0)
    upgrade_clicks = db.Column(db.Integer, default=0)
    affiliate_clicks = db.Column(db.Integer, default=0)
    invite_codes_used = db.Column(db.Integer, default=0)

    revenue_cents = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_or_create_today(cls):
        from datetime import date
        today = date.today()
        stat = cls.query.filter_by(date=today).first()
        if not stat:
            stat = cls(date=today)
            db.session.add(stat)
            db.session.commit()
        return stat
