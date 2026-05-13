"""
商品搜索服务
根据穿搭/发型推荐生成购买链接
支持：淘宝、京东、拼多多搜索链接生成
扩展：联盟API接入（需申请key）
"""

import os
import urllib.parse
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class ProductLink:
    """商品链接"""
    
    def __init__(self, title: str, search_url: str, platform: str,
                 keywords: str = '', image_url: str = ''):
        self.title = title
        self.search_url = search_url
        self.platform = platform
        self.keywords = keywords
        self.image_url = image_url
    
    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'search_url': self.search_url,
            'platform': self.platform,
            'keywords': self.keywords,
            'image_url': self.image_url,
        }


class ProductSearchService(ABC):
    """商品搜索服务抽象基类"""
    
    @abstractmethod
    def search(self, keywords: str, category: str = 'clothing') -> List[ProductLink]:
        """
        搜索商品
        :param keywords: 搜索关键词
        :param category: 类别（clothing/hair_product/accessory）
        :return: 商品链接列表
        """
        pass


class TaobaoSearchService(ProductSearchService):
    """淘宝搜索链接生成"""
    
    name = 'taobao'
    
    def search(self, keywords: str, category: str = 'clothing') -> List[ProductLink]:
        encoded = urllib.parse.quote(keywords)
        url = f'https://s.taobao.com/search?q={encoded}&imgfile=&js=1&stats_click=search_radio_all%3A1&initiative_id=staobaoz_20240101&ie=utf8&sort=sale-desc'
        
        return [ProductLink(
            title=f'淘宝搜索：{keywords}',
            search_url=url,
            platform='淘宝',
            keywords=keywords,
        )]


class JDSearchService(ProductSearchService):
    """京东搜索链接生成"""
    
    name = 'jd'
    
    def search(self, keywords: str, category: str = 'clothing') -> List[ProductLink]:
        encoded = urllib.parse.quote(keywords)
        url = f'https://search.jd.com/Search?keyword={encoded}&enc=utf-8&wq={encoded}'
        
        return [ProductLink(
            title=f'京东搜索：{keywords}',
            search_url=url,
            platform='京东',
            keywords=keywords,
        )]


class PDDSearchService(ProductSearchService):
    """拼多多搜索链接生成"""
    
    name = 'pdd'
    
    def search(self, keywords: str, category: str = 'clothing') -> List[ProductLink]:
        encoded = urllib.parse.quote(keywords)
        url = f'https://mobile.yangkeduo.com/search_result.html?search_key={encoded}'
        
        return [ProductLink(
            title=f'拼多多搜索：{keywords}',
            search_url=url,
            platform='拼多多',
            keywords=keywords,
        )]


class DefaultProductSearchService(ProductSearchService):
    """
    默认商品搜索服务
    同时返回多个平台的搜索链接
    """
    
    name = 'default'
    
    def __init__(self):
        self.services = [
            TaobaoSearchService(),
            JDSearchService(),
            PDDSearchService(),
        ]
    
    def search(self, keywords: str, category: str = 'clothing') -> List[ProductLink]:
        results = []
        for svc in self.services:
            try:
                links = svc.search(keywords, category)
                results.extend(links)
            except Exception as e:
                print(f'[ProductSearch] {svc.name} 失败: {e}')
        return results
    
    def search_outfit_items(self, outfit_items: Dict[str, str]) -> List[ProductLink]:
        """
        根据穿搭单品生成搜索链接
        :param outfit_items: {top, outer, bottom, shoes, accessories}
        :return: 商品链接列表
        """
        results = []
        category_map = {
            'top': '上装',
            'outer': '外套',
            'bottom': '下装',
            'shoes': '鞋履',
            'accessories': '配饰',
        }
        
        for key, value in outfit_items.items():
            if not value:
                continue
            label = category_map.get(key, key)
            keywords = value.replace('/', ' ').replace('+', ' ')
            
            for svc in self.services:
                try:
                    links = svc.search(f'{label} {keywords}')
                    for link in links:
                        link.title = f'[{label}] {value}'
                    results.extend(links)
                except Exception as e:
                    print(f'[ProductSearch] {svc.name} 失败: {e}')
        
        return results
    
    def search_hair_products(self, hairstyle_name: str, hair_type: str = '') -> List[ProductLink]:
        """
        根据发型推荐搜索相关美发产品
        :param hairstyle_name: 发型名称
        :param hair_type: 发质类型
        :return: 商品链接列表
        """
        results = []
        keywords_list = [
            f'{hairstyle_name} 造型',
            f'{hairstyle_name} 发蜡 发泥',
            f'{hairstyle_name} 打理教程',
        ]
        
        if hair_type:
            keywords_list.append(f'{hair_type} 护理')
        
        for keywords in keywords_list:
            for svc in self.services:
                try:
                    links = svc.search(keywords, category='hair_product')
                    results.extend(links)
                except Exception as e:
                    print(f'[ProductSearch] {svc.name} 失败: {e}')
        
        return results


# 全局单例
default_product_search = DefaultProductSearchService()


def search_products(keywords: str, category: str = 'clothing') -> List[ProductLink]:
    return default_product_search.search(keywords, category)


def search_outfit_items(outfit_items: Dict[str, str]) -> List[ProductLink]:
    return default_product_search.search_outfit_items(outfit_items)


def search_hair_products(hairstyle_name: str, hair_type: str = '') -> List[ProductLink]:
    return default_product_search.search_hair_products(hairstyle_name, hair_type)
