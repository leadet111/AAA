"""
业务服务层
原生APP和PWA共用同一套业务逻辑
新增：GenderRecognitionService 性别识别、ImageGeneration 图片生成、ProductSearch 商品搜索
"""

from .analyzer import StyleAnalyzer
from .storage import StorageService
from .monetization import MonetizationService
from .gender_recognition import (
    GenderRecognitionService,
    GenderRecognitionResult,
    BaiduGenderRecognition,
    AliyunGenderRecognition,
    MockGenderRecognition,
    DefaultGenderRecognition,
    recognize_gender,
)
from .image_generation import (
    ImageGenerationService,
    GenerationResult,
    StableDiffusionLocalBackend,
    ReplicateBackend,
    MockImageGenerationService,
    DefaultImageGenerationService,
    generate_outfit_image,
    generate_hairstyle_image,
)
from .product_search import (
    ProductSearchService,
    ProductLink,
    TaobaoSearchService,
    JDSearchService,
    PDDSearchService,
    DefaultProductSearchService,
    search_products,
    search_outfit_items,
    search_hair_products,
)

__all__ = [
    'StyleAnalyzer', 'StorageService', 'MonetizationService',
    'GenderRecognitionService', 'GenderRecognitionResult',
    'BaiduGenderRecognition', 'AliyunGenderRecognition',
    'MockGenderRecognition', 'DefaultGenderRecognition',
    'recognize_gender',
    'ImageGenerationService', 'GenerationResult',
    'StableDiffusionLocalBackend', 'ReplicateBackend',
    'MockImageGenerationService', 'DefaultImageGenerationService',
    'generate_outfit_image', 'generate_hairstyle_image',
    'ProductSearchService', 'ProductLink',
    'TaobaoSearchService', 'JDSearchService', 'PDDSearchService',
    'DefaultProductSearchService',
    'search_products', 'search_outfit_items', 'search_hair_products',
]
