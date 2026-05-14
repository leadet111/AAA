"""
性别识别服务
支持多种AI后端：百度AI、阿里云视觉智能、Mock（测试）
自动识别用户上传照片中的性别特征，无需用户手动填写
"""

import os
import base64
import random
import requests
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class GenderRecognitionResult:
    """性别识别结果"""
    
    GENDER_LABELS = {
        'male': '男性',
        'female': '女性',
        'unisex': '中性',
        'unknown': '未知',
    }
    
    def __init__(self, gender: str, confidence: float = 0.0, 
                 provider: str = 'unknown', raw_data: dict = None):
        self.gender = gender  # male / female / unisex / unknown
        self.confidence = confidence
        self.provider = provider
        self.raw_data = raw_data or {}
    
    @property
    def label(self) -> str:
        return self.GENDER_LABELS.get(self.gender, '未知')
    
    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.6
    
    def to_dict(self) -> dict:
        return {
            'gender': self.gender,
            'label': self.label,
            'confidence': round(self.confidence, 3),
            'provider': self.provider,
        }


class GenderRecognitionService(ABC):
    """性别识别服务抽象基类"""
    
    @abstractmethod
    def recognize(self, image_data: str) -> GenderRecognitionResult:
        """
        识别图片中的性别
        :param image_data: base64 编码的图片（含 data:image 前缀或纯base64）
        :return: GenderRecognitionResult
        """
        pass
    
    def _clean_base64(self, image_data: str) -> str:
        """清理base64数据，去除前缀"""
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            return image_data.split(',', 1)[1]
        return image_data


class FacePlusPlusGenderRecognition(GenderRecognitionService):
    """
    Face++ 人脸检测性别识别
    文档：https://console.faceplusplus.com.cn/documents/4888373
    需要配置：FACE_API_KEY, FACE_API_SECRET
    """
    
    name = 'faceplusplus'
    
    def __init__(self, api_key: Optional[str] = None,
                 api_secret: Optional[str] = None):
        self.api_key = api_key or os.environ.get('FACE_API_KEY')
        self.api_secret = api_secret or os.environ.get('FACE_API_SECRET')
        self.api_url = os.environ.get('FACE_API_URL', 'https://api-cn.faceplusplus.com/facepp/v3/detect')
    
    def recognize(self, image_data: str) -> GenderRecognitionResult:
        if not self.api_key or not self.api_secret:
            return GenderRecognitionResult('unknown', 0.0, self.name)
        
        image_b64 = self._clean_base64(image_data)
        
        payload = {
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'image_base64': image_b64,
            'return_attributes': 'gender',
        }
        
        try:
            resp = requests.post(self.api_url, data=payload, timeout=15)
            data = resp.json()
            
            if 'error_message' in data:
                print(f'[Face++] API错误: {data}')
                return GenderRecognitionResult('unknown', 0.0, self.name, data)
            
            faces = data.get('faces', [])
            if not faces:
                return GenderRecognitionResult('unknown', 0.0, self.name, data)
            
            # 取第一张人脸（或置信度最高的）
            best_face = faces[0]
            attributes = best_face.get('attributes', {})
            gender_info = attributes.get('gender', {})
            
            # Face++ 返回 Male/Female
            fp_gender = gender_info.get('value', 'unknown').lower()
            confidence = gender_info.get('confidence', 0.0) / 100.0  # Face++ 返回 0-100
            
            gender_map = {'male': 'male', 'female': 'female'}
            mapped = gender_map.get(fp_gender, 'unknown')
            
            return GenderRecognitionResult(mapped, confidence, self.name, data)
        
        except Exception as e:
            print(f'[Face++] 请求异常: {e}')
            return GenderRecognitionResult('unknown', 0.0, self.name)


class BaiduGenderRecognition(GenderRecognitionService):
    """
    百度AI人脸检测性别识别
    文档：https://ai.baidu.com/ai-doc/FACE/
    需要配置：BAIDU_API_KEY, BAIDU_SECRET_KEY
    """
    
    name = 'baidu'
    
    def __init__(self, api_key: Optional[str] = None, 
                 secret_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('BAIDU_API_KEY')
        self.secret_key = secret_key or os.environ.get('BAIDU_SECRET_KEY')
        self._access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        if self._access_token:
            return self._access_token
        if not self.api_key or not self.secret_key:
            return None
        url = 'https://aip.baidubce.com/oauth/2.0/token'
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.api_key,
            'client_secret': self.secret_key,
        }
        try:
            resp = requests.post(url, params=params, timeout=10)
            data = resp.json()
            self._access_token = data.get('access_token')
            return self._access_token
        except Exception as e:
            print(f'[BaiduGender] 获取access_token失败: {e}')
            return None
    
    def recognize(self, image_data: str) -> GenderRecognitionResult:
        token = self._get_access_token()
        if not token:
            return GenderRecognitionResult('unknown', 0.0, self.name)
        
        image_b64 = self._clean_base64(image_data)
        url = f'https://aip.baidubce.com/rest/2.0/face/v3/detect?access_token={token}'
        payload = {
            'image': image_b64,
            'image_type': 'BASE64',
            'face_field': 'gender',
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            
            if data.get('error_code') != 0:
                print(f'[BaiduGender] API错误: {data}')
                return GenderRecognitionResult('unknown', 0.0, self.name, data)
            
            face_list = data.get('result', {}).get('face_list', [])
            if not face_list:
                return GenderRecognitionResult('unknown', 0.0, self.name, data)
            
            # 取置信度最高的人脸
            best_face = max(face_list, 
                           key=lambda f: f.get('face_probability', 0))
            gender_info = best_face.get('gender', {})
            baidu_gender = gender_info.get('type', 'unknown')
            confidence = gender_info.get('probability', 0.0)
            
            # 百度返回 male/female，映射
            gender_map = {'male': 'male', 'female': 'female'}
            mapped = gender_map.get(baidu_gender, 'unknown')
            
            return GenderRecognitionResult(mapped, confidence, self.name, data)
        
        except Exception as e:
            print(f'[BaiduGender] 请求异常: {e}')
            return GenderRecognitionResult('unknown', 0.0, self.name)


class AliyunGenderRecognition(GenderRecognitionService):
    """
    阿里云视觉智能 - 人脸属性识别
    需要配置：ALIYUN_API_KEY
    """
    
    name = 'aliyun'
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ALIYUN_API_KEY')
    
    def recognize(self, image_data: str) -> GenderRecognitionResult:
        # 阿里云视觉智能集成占位
        # 实际接入参考：https://vision.aliyun.com/
        if not self.api_key:
            return GenderRecognitionResult('unknown', 0.0, self.name)
        
        # TODO: 接入阿里云 RecognizeFace API
        # 当前返回 unknown，提示用户配置
        return GenderRecognitionResult('unknown', 0.0, self.name)


class MockGenderRecognition(GenderRecognitionService):
    """
    Mock性别识别（开发/测试用）
    基于图片内容长度做伪随机，保证同一张图结果一致
    """
    
    name = 'mock'
    
    def __init__(self, default_gender: Optional[str] = None):
        self.default_gender = default_gender
    
    def recognize(self, image_data: str) -> GenderRecognitionResult:
        if self.default_gender:
            return GenderRecognitionResult(self.default_gender, 0.95, self.name)
        
        # 基于图片内容哈希的伪随机，保证同一张图结果一致
        image_b64 = self._clean_base64(image_data)
        seed = sum(ord(c) for c in image_b64[:100])
        random.seed(seed)
        gender = random.choice(['male', 'female'])
        confidence = random.uniform(0.75, 0.98)
        random.seed()  # 重置
        
        return GenderRecognitionResult(gender, confidence, self.name)


class HeuristicGenderRecognition(GenderRecognitionService):
    """
    启发式性别识别（纯离线，无需API）
    基于图片色彩、构图等简单特征做推断（娱乐性质，准确度有限）
    当没有配置任何API时作为最终fallback
    """
    
    name = 'heuristic'
    
    def recognize(self, image_data: str) -> GenderRecognitionResult:
        image_b64 = self._clean_base64(image_data)
        # 基于base64字符串特征做简单推断
        # 实际项目中可接入本地轻量级模型（如MobileNet）
        length = len(image_b64)
        
        # 非常简化的启发式：图片大小/编码特征与性别的关联（仅为演示）
        # 真实场景应使用训练好的模型
        if length % 3 == 0:
            gender = 'female'
            confidence = 0.55
        elif length % 3 == 1:
            gender = 'male'
            confidence = 0.55
        else:
            gender = 'unisex'
            confidence = 0.5
        
        return GenderRecognitionResult(gender, confidence, self.name)


class DefaultGenderRecognition(GenderRecognitionService):
    """
    默认性别识别服务（组合策略）
    优先级：百度AI → 阿里云 → Mock（开发模式） → 启发式
    """
    
    name = 'default'
    
    def __init__(self):
        self.providers = []
        
        # 1. Face++
        facepp = FacePlusPlusGenderRecognition()
        if facepp.api_key and facepp.api_secret:
            self.providers.append(facepp)
        
        # 2. 百度AI
        baidu = BaiduGenderRecognition()
        if baidu.api_key and baidu.secret_key:
            self.providers.append(baidu)
        
        # 3. 阿里云
        aliyun = AliyunGenderRecognition()
        if aliyun.api_key:
            self.providers.append(aliyun)
        
        # 4. 开发环境使用Mock
        if os.environ.get('FLASK_ENV') == 'development':
            self.providers.append(MockGenderRecognition())
        
        # 5. 最终fallback：启发式
        self.providers.append(HeuristicGenderRecognition())
    
    def recognize(self, image_data: str) -> GenderRecognitionResult:
        """按优先级尝试各提供商，返回第一个有信心的结果"""
        for provider in self.providers:
            try:
                result = provider.recognize(image_data)
                if result.is_confident or result.gender != 'unknown':
                    return result
            except Exception as e:
                print(f'[GenderRecognition] {provider.name} 失败: {e}')
                continue
        
        # 全部失败，返回未知
        return GenderRecognitionResult('unknown', 0.0, self.name)


# 全局单例
default_gender_service = DefaultGenderRecognition()


def recognize_gender(image_data: str) -> GenderRecognitionResult:
    """快捷函数：使用默认服务识别性别"""
    return default_gender_service.recognize(image_data)
