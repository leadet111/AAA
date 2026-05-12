"""
推荐商品 / Affiliate 占位模型
为未来电商变现做准备
"""

from datetime import datetime
from app import db


class ProductLink(db.Model):
    """商品链接表（affiliate / 自营商品占位）"""
    __tablename__ = 'product_links'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # 商品分类
    category = db.Column(db.String(50), nullable=False, index=True)  # outfit / hair / accessory
    # 适用标签（匹配用户特征）
    match_tags = db.Column(db.String(500), nullable=True)  # 逗号分隔，如 "warm,oval,daily"
    # 链接
    platform = db.Column(db.String(30), nullable=False, default='taobao')  # taobao / jd / amazon / custom
    external_url = db.Column(db.String(800), nullable=True)   # 外链
    affiliate_code = db.Column(db.String(200), nullable=True)  # affiliate 跟踪码
    # 定价展示
    display_price = db.Column(db.String(20), nullable=True)  # 如 "199"
    original_price = db.Column(db.String(20), nullable=True)
    currency = db.Column(db.String(10), default='CNY')
    # 媒体
    image_url = db.Column(db.String(500), nullable=True)
    # 统计
    click_count = db.Column(db.Integer, default=0)
    # 状态
    is_active = db.Column(db.Boolean, default=True)
    is_premium_only = db.Column(db.Boolean, default=False)  # 仅高级会员可见
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_affiliate=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'platform': self.platform,
            'display_price': self.display_price,
            'original_price': self.original_price,
            'currency': self.currency,
            'image_url': self.image_url,
            'is_premium_only': self.is_premium_only,
        }
        if include_affiliate:
            data['external_url'] = self._build_affiliate_url()
            data['affiliate_code'] = self.affiliate_code
        return data

    def _build_affiliate_url(self):
        """构建带跟踪码的链接"""
        if not self.external_url:
            return None
        if self.affiliate_code:
            # 简单拼接，实际根据各平台规则处理
            separator = '&' if '?' in self.external_url else '?'
            return f"{self.external_url}{separator}track={self.affiliate_code}"
        return self.external_url

    def record_click(self):
        self.click_count += 1
        db.session.commit()

    @classmethod
    def match_for_user(cls, category, user_traits, is_premium=False, limit=5):
        """根据用户特征匹配商品"""
        query = cls.query.filter_by(category=category, is_active=True)
        if not is_premium:
            query = query.filter_by(is_premium_only=False)
        # 简单标签匹配（后续可用更复杂的推荐算法）
        items = query.order_by(cls.sort_order.asc()).limit(limit * 2).all()
        matched = []
        for item in items:
            score = 0
            if item.match_tags and user_traits:
                tags = [t.strip().lower() for t in item.match_tags.split(',')]
                for trait in user_traits.values():
                    if trait and str(trait).lower() in tags:
                        score += 1
            matched.append((score, item))
        matched.sort(key=lambda x: (-x[0], x[1].sort_order))
        return [m[1] for m in matched[:limit]]
