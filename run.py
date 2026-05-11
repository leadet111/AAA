"""
启动入口
"""

import os
from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

from app import create_app, db
from app.models import User, AnalysisHistory
from flask_migrate import Migrate

# 确保目录存在（SQLite 需要先有父目录）
import os
os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'data', 'user_uploads'), exist_ok=True)

app = create_app(os.environ.get('FLASK_ENV', 'development'))
migrate = Migrate(app, db)

# 初始化数据库
with app.app_context():
    db.create_all()

# CLI 命令
@app.cli.command('init-db')
def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        print('数据库已初始化')


@app.cli.command('seed')
def seed_data():
    """导入穿搭知识库到数据库（预留）"""
    print('知识库已就绪（JSON 格式）')


if __name__ == '__main__':
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # 确保数据目录存在
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
    
    print(f"服务启动中...")
    print(f"API 文档: http://127.0.0.1:5001/apidocs/")
    app.run(host='0.0.0.0', port=5001, debug=app.config.get('DEBUG', True))
