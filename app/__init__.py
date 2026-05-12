"""
Flask 应用工厂
原生APP和PWA共用同一个后端
"""

import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flasgger import Swagger

# 初始化扩展（先不绑定app）
db = SQLAlchemy()
jwt = JWTManager()
swagger = Swagger()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    from config import config_map
    config_class = config_map.get(config_name, config_map['default'])

    app = Flask(
        __name__,
        static_folder='../static',
        template_folder='../templates',
        static_url_path='/static'
    )
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)

    # Swagger API 文档（原生APP开发参考）
    swagger.template = {
        "swagger": "2.0",
        "info": {
            "title": "穿搭发型顾问 API",
            "description": "PWA 和原生APP共用接口文档",
            "version": "1.0.0",
        },
        "basePath": "/api/v1",
    }
    swagger.init_app(app)

    # 注册蓝图
    from app.api.v1 import api_v1
    app.register_blueprint(api_v1, url_prefix='/api/v1')

    # 兼容旧版路径（PWA前端已用）
    from app.api.v1.analyze import analyze_image_legacy
    app.route('/api/analyze', methods=['POST'])(analyze_image_legacy)

    # 根路由（PWA入口）
    @app.route('/')
    def index():
        from datetime import datetime
        return render_template('index.html', year=datetime.now().year)

    # 数据库表创建和种子数据（SQLite 简单方案）
    with app.app_context():
        db.create_all()
        from app.models.membership import MembershipTier
        MembershipTier.seed_defaults()

    return app


# 避免循环导入，延迟导入
from flask import render_template
