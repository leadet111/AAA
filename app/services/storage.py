"""
文件存储服务
抽象接口：本地存储 / 阿里云OSS / AWS S3
原生APP和PWA上传的图片统一由此服务管理
"""

import os
import uuid
from datetime import datetime


class StorageService:
    """文件存储抽象服务"""
    
    def __init__(self, app_config):
        self.driver = app_config.get('STORAGE_DRIVER', 'local')
        self.local_folder = app_config.get('UPLOAD_FOLDER', 'data/user_uploads')
        self._ensure_local_dir()
    
    def _ensure_local_dir(self):
        if self.driver == 'local':
            os.makedirs(self.local_folder, exist_ok=True)
    
    def save(self, file_data, original_filename=None, folder='uploads'):
        """
        保存文件
        :param file_data: bytes 或 base64 字符串
        :param original_filename: 原始文件名
        :param folder: 子目录
        :return: 文件访问URL和存储路径
        """
        ext = self._get_extension(original_filename) or '.jpg'
        filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}{ext}"
        
        if self.driver == 'local':
            return self._save_local(file_data, filename, folder)
        
        # 预留：阿里云OSS / AWS S3
        # elif self.driver == 'oss':
        #     return self._save_oss(file_data, filename, folder)
        # elif self.driver == 's3':
        #     return self._save_s3(file_data, filename, folder)
        
        return self._save_local(file_data, filename, folder)
    
    def _save_local(self, file_data, filename, folder):
        save_dir = os.path.join(self.local_folder, folder)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        if isinstance(file_data, str) and file_data.startswith('data:image'):
            # base64 图片
            import base64
            header, encoded = file_data.split(',', 1)
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(encoded))
        else:
            with open(filepath, 'wb') as f:
                f.write(file_data)
        
        # 返回相对URL路径和绝对路径
        relative_url = f"/uploads/{folder}/{filename}"
        return {
            'url': relative_url,
            'path': filepath,
            'filename': filename,
        }
    
    def get_url(self, path_or_url):
        """获取文件访问URL"""
        if self.driver == 'local':
            if path_or_url.startswith('/uploads/'):
                return path_or_url
            # 将绝对路径转为相对URL
            rel = os.path.relpath(path_or_url, self.local_folder)
            return f"/uploads/{rel.replace(os.sep, '/')}"
        return path_or_url
    
    def delete(self, path_or_url):
        """删除文件"""
        if self.driver == 'local':
            if os.path.exists(path_or_url):
                os.remove(path_or_url)
                return True
        return False
    
    @staticmethod
    def _get_extension(filename):
        if not filename:
            return '.jpg'
        ext = os.path.splitext(filename)[1].lower()
        return ext if ext else '.jpg'
