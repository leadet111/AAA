"""
图片生成服务
支持：虚拟试衣、发型效果生成
技术方案：
  - 本地 Stable Diffusion + ControlNet + IP-Adapter（需GPU）
  - Replicate 云API
  - 阿里云/百度AI
  - Mock（开发测试）

核心目标：保留用户面部和身材原型，生成最真实的穿搭/发型预测图
"""

import os
import base64
import json
import uuid
import requests
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from pathlib import Path


class GenerationResult:
    """图片生成结果"""
    
    def __init__(self, image_url: str, image_path: str = None,
                 prompt: str = '', provider: str = 'unknown',
                 metadata: dict = None):
        self.image_url = image_url
        self.image_path = image_path
        self.prompt = prompt
        self.provider = provider
        self.metadata = metadata or {}
    
    def to_dict(self) -> dict:
        return {
            'image_url': self.image_url,
            'image_path': self.image_path,
            'prompt': self.prompt,
            'provider': self.provider,
            'metadata': self.metadata,
        }


class ImageGenerationService(ABC):
    """图片生成服务抽象基类"""
    
    @abstractmethod
    def generate_outfit(self, user_image: str, outfit_description: str,
                        gender: str = 'unisex') -> GenerationResult:
        """
        生成穿搭效果图（虚拟试衣）
        :param user_image: base64 用户照片
        :param outfit_description: 穿搭描述
        :param gender: 性别
        :return: GenerationResult
        """
        pass
    
    @abstractmethod
    def generate_hairstyle(self, user_image: str, hairstyle_description: str,
                           gender: str = 'unisex') -> GenerationResult:
        """
        生成发型效果图
        :param user_image: base64 用户照片
        :param hairstyle_description: 发型描述
        :param gender: 性别
        :return: GenerationResult
        """
        pass
    
    def _clean_base64(self, image_data: str) -> str:
        """清理base64数据"""
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            return image_data.split(',', 1)[1]
        return image_data
    
    def _save_generated_image(self, image_data: bytes, prefix: str = 'gen') -> str:
        """保存生成的图片到本地"""
        upload_dir = os.environ.get('UPLOAD_FOLDER') or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'user_uploads', 'generated'
        )
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{prefix}_{uuid.uuid4().hex[:12]}.png"
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        return filepath


class StableDiffusionLocalBackend(ImageGenerationService):
    """
    本地 Stable Diffusion WebUI / ComfyUI 后端
    需要本地部署 SD WebUI（--api 模式）或 ComfyUI
    环境变量：SD_API_URL（默认 http://127.0.0.1:7860）
    """
    
    name = 'stable_diffusion_local'
    
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = (api_url or os.environ.get('SD_API_URL', 'http://127.0.0.1:7860')).rstrip('/')
    
    def _check_available(self) -> bool:
        try:
            resp = requests.get(f'{self.api_url}/sdapi/v1/samplers', timeout=3)
            return resp.status_code == 200
        except:
            return False
    
    def _img2img(self, init_image: str, prompt: str, 
                 negative_prompt: str = '', denoising: float = 0.6,
                 width: int = 512, height: int = 768) -> Optional[GenerationResult]:
        """调用 SD WebUI img2img API"""
        if not self._check_available():
            return None
        
        payload = {
            'init_images': [f'data:image/png;base64,{init_image}'],
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'denoising_strength': denoising,
            'width': width,
            'height': height,
            'steps': 25,
            'cfg_scale': 7,
            'sampler_name': 'DPM++ 2M Karras',
        }
        
        try:
            resp = requests.post(f'{self.api_url}/sdapi/v1/img2img',
                                json=payload, timeout=120)
            data = resp.json()
            
            if 'images' in data and data['images']:
                img_b64 = data['images'][0]
                img_bytes = base64.b64decode(img_b64)
                img_path = self._save_generated_image(img_bytes, 'sd')
                
                return GenerationResult(
                    image_url=f'/api/v1/images/generated/{os.path.basename(img_path)}',
                    image_path=img_path,
                    prompt=prompt,
                    provider=self.name,
                )
        except Exception as e:
            print(f'[SDLocal] img2img 失败: {e}')
        
        return None
    
    def generate_outfit(self, user_image: str, outfit_description: str,
                        gender: str = 'unisex') -> GenerationResult:
        """生成穿搭效果图"""
        init_image = self._clean_base64(user_image)
        
        prompt = (
            f"(masterpiece, best quality, photorealistic), "
            f"a person wearing {outfit_description}, "
            f"full body, standing pose, same face, same person, "
            f"high detail, studio lighting, 8k uhd"
        )
        negative = (
            "worst quality, low quality, deformed, mutated, "
            "extra limbs, bad anatomy, different person, different face"
        )
        
        result = self._img2img(init_image, prompt, negative, denoising=0.55)
        if result:
            return result
        
        # fallback
        return GenerationResult('', provider=self.name)
    
    def generate_hairstyle(self, user_image: str, hairstyle_description: str,
                           gender: str = 'unisex') -> GenerationResult:
        """生成发型效果图"""
        init_image = self._clean_base64(user_image)
        
        prompt = (
            f"(masterpiece, best quality, photorealistic), "
            f"same person with {hairstyle_description}, "
            f"portrait, same face, same facial features, "
            f"high detail, studio lighting, 8k uhd"
        )
        negative = (
            "worst quality, low quality, deformed, mutated, "
            "extra limbs, bad anatomy, different person, different face"
        )
        
        result = self._img2img(init_image, prompt, negative, denoising=0.5)
        if result:
            return result
        
        return GenerationResult('', provider=self.name)


class ReplicateBackend(ImageGenerationService):
    """
    Replicate 云API后端
    支持模型：flux-dev, sdxl, 等
    环境变量：REPLICATE_API_TOKEN
    文档：https://replicate.com/docs
    """
    
    name = 'replicate'
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.environ.get('REPLICATE_API_TOKEN')
        self.base_url = 'https://api.replicate.com/v1'
    
    def _call_model(self, model: str, input_data: dict) -> Optional[str]:
        """调用 Replicate 模型"""
        if not self.api_token:
            return None
        
        headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'version': model,
            'input': input_data,
        }
        
        try:
            # 创建预测
            resp = requests.post(f'{self.base_url}/predictions',
                                json=payload, headers=headers, timeout=30)
            data = resp.json()
            prediction_id = data.get('id')
            
            if not prediction_id:
                return None
            
            # 轮询结果
            import time
            for _ in range(60):  # 最多等2分钟
                time.sleep(2)
                resp = requests.get(f'{self.base_url}/predictions/{prediction_id}',
                                   headers=headers, timeout=10)
                status_data = resp.json()
                
                if status_data.get('status') == 'succeeded':
                    output = status_data.get('output')
                    if isinstance(output, list) and output:
                        return output[0]
                    elif isinstance(output, str):
                        return output
                    return None
                elif status_data.get('status') in ('failed', 'canceled'):
                    return None
        except Exception as e:
            print(f'[Replicate] API调用失败: {e}')
        
        return None
    
    def generate_outfit(self, user_image: str, outfit_description: str,
                        gender: str = 'unisex') -> GenerationResult:
        """生成穿搭效果图"""
        # Replicate 上可以用 img2img 模型，如 stability-ai/sdxl
        # 这里使用文本生成作为 fallback
        prompt = (
            f"photorealistic full body photo of a person wearing {outfit_description}, "
            f"high detail, studio lighting, 8k uhd"
        )
        
        # 如果有 img2img 模型版本，可以传入图片
        # 当前使用文本生成作为占位
        image_url = self._call_model(
            'stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b',
            {'prompt': prompt, 'width': 768, 'height': 1024}
        )
        
        if image_url:
            # 下载图片
            try:
                resp = requests.get(image_url, timeout=30)
                img_path = self._save_generated_image(resp.content, 'rep')
                return GenerationResult(
                    image_url=image_url,
                    image_path=img_path,
                    prompt=prompt,
                    provider=self.name,
                )
            except Exception as e:
                print(f'[Replicate] 下载图片失败: {e}')
        
        return GenerationResult('', provider=self.name)
    
    def generate_hairstyle(self, user_image: str, hairstyle_description: str,
                           gender: str = 'unisex') -> GenerationResult:
        """生成发型效果图"""
        prompt = (
            f"photorealistic portrait photo of a person with {hairstyle_description}, "
            f"high detail, studio lighting, 8k uhd"
        )
        
        image_url = self._call_model(
            'stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b',
            {'prompt': prompt, 'width': 768, 'height': 1024}
        )
        
        if image_url:
            try:
                resp = requests.get(image_url, timeout=30)
                img_path = self._save_generated_image(resp.content, 'rep')
                return GenerationResult(
                    image_url=image_url,
                    image_path=img_path,
                    prompt=prompt,
                    provider=self.name,
                )
            except Exception as e:
                print(f'[Replicate] 下载图片失败: {e}')
        
        return GenerationResult('', provider=self.name)


class MockImageGenerationService(ImageGenerationService):
    """
    Mock 图片生成服务（开发/测试用）
    不实际生成图片，返回原图或占位信息
    """
    
    name = 'mock'
    
    def generate_outfit(self, user_image: str, outfit_description: str,
                        gender: str = 'unisex') -> GenerationResult:
        """Mock：返回原图作为占位"""
        return GenerationResult(
            image_url=user_image if user_image else '',
            prompt=f'Mock outfit: {outfit_description}',
            provider=self.name,
            metadata={'mock': True, 'note': '请配置图片生成后端以获得真实效果'}
        )
    
    def generate_hairstyle(self, user_image: str, hairstyle_description: str,
                           gender: str = 'unisex') -> GenerationResult:
        """Mock：返回原图作为占位"""
        return GenerationResult(
            image_url=user_image if user_image else '',
            prompt=f'Mock hairstyle: {hairstyle_description}',
            provider=self.name,
            metadata={'mock': True, 'note': '请配置图片生成后端以获得真实效果'}
        )


class DefaultImageGenerationService(ImageGenerationService):
    """
    默认图片生成服务（组合策略）
    优先级：本地SD → Replicate → Mock
    """
    
    name = 'default'
    
    def __init__(self):
        self.backends = []
        
        # 1. 本地 SD
        sd = StableDiffusionLocalBackend()
        if sd._check_available():
            self.backends.append(sd)
        
        # 2. Replicate
        rep = ReplicateBackend()
        if rep.api_token:
            self.backends.append(rep)
        
        # 3. Mock（保底）
        self.backends.append(MockImageGenerationService())
    
    def generate_outfit(self, user_image: str, outfit_description: str,
                        gender: str = 'unisex') -> GenerationResult:
        for backend in self.backends:
            try:
                result = backend.generate_outfit(user_image, outfit_description, gender)
                if result and (result.image_url or result.image_path):
                    return result
            except Exception as e:
                print(f'[ImageGen] {backend.name} 失败: {e}')
                continue
        return GenerationResult('', provider=self.name)
    
    def generate_hairstyle(self, user_image: str, hairstyle_description: str,
                           gender: str = 'unisex') -> GenerationResult:
        for backend in self.backends:
            try:
                result = backend.generate_hairstyle(user_image, hairstyle_description, gender)
                if result and (result.image_url or result.image_path):
                    return result
            except Exception as e:
                print(f'[ImageGen] {backend.name} 失败: {e}')
                continue
        return GenerationResult('', provider=self.name)


# 全局单例
default_image_gen = DefaultImageGenerationService()


def generate_outfit_image(user_image: str, outfit_description: str,
                          gender: str = 'unisex') -> GenerationResult:
    return default_image_gen.generate_outfit(user_image, outfit_description, gender)


def generate_hairstyle_image(user_image: str, hairstyle_description: str,
                             gender: str = 'unisex') -> GenerationResult:
    return default_image_gen.generate_hairstyle(user_image, hairstyle_description, gender)
