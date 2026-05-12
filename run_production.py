"""
生产环境启动入口
使用 Waitress WSGI 服务器（跨平台，无需额外配置）

启动方式:
    python run_production.py

或指定端口:
    PORT=8080 python run_production.py
"""

import os
import sys

# 加载环境变量
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

from waitress import serve
from run import app

# 生产环境校验
if app.config.get('DEBUG'):
    print("WARNING: DEBUG 模式已开启，建议在生产环境关闭")
    print("         设置环境变量 FLASK_ENV=production")

if app.config.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
    print("WARNING: 正在使用默认 SECRET_KEY，请在 .env 中设置强密钥")

if app.config.get('JWT_SECRET_KEY') == 'dev-jwt-secret-key':
    print("WARNING: 正在使用默认 JWT_SECRET_KEY，请在 .env 中设置强密钥")

# 获取配置
host = os.environ.get('HOST', '127.0.0.1')  # 生产环境建议绑定 127.0.0.1，由 Nginx 反向代理
port = int(os.environ.get('PORT', 5001))
threads = int(os.environ.get('THREADS', 4))

print(f"=" * 50)
print(f"穿搭发型顾问 - 生产环境")
print(f"监听地址: {host}:{port}")
print(f"工作线程: {threads}")
print(f"DEBUG 模式: {app.config.get('DEBUG', False)}")
print(f"=" * 50)

# 启动 Waitress
serve(app, host=host, port=port, threads=threads)
