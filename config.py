"""
配置管理
支持环境变量覆盖，原生APP和PWA共用同一套后端配置
"""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 86400))
    )

    # 数据库（使用绝对路径避免工作目录问题）
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db').replace('\\', '/')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 文件存储
    STORAGE_DRIVER = os.environ.get('STORAGE_DRIVER', 'local')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or \
        os.path.join(basedir, 'data', 'user_uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    # 第三方 AI API（预留）
    BAIDU_API_KEY = os.environ.get('BAIDU_API_KEY')
    BAIDU_SECRET_KEY = os.environ.get('BAIDU_SECRET_KEY')
    ALIYUN_API_KEY = os.environ.get('ALIYUN_API_KEY')

    # API 版本
    API_VERSION = 'v1'


class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True


class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
