"""
穿搭发型分析引擎
核心推荐算法，原生APP和PWA共用
新增：
  1. 按性别过滤穿搭和发型
  2. 为所有用户生成三种方案（用户性别 + 中性 + 另一性别）
"""

import json
import os
import hashlib


class StyleAnalyzer:
    """形象分析引擎"""
    
    # 性别方案展示顺序
    GENDER_SCHEMES = ['user', 'unisex', 'other']
    
    def __init__(self, knowledge_path=None):
        if knowledge_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            knowledge_path = os.path.join(base_dir, 'data', 'style_knowledge.json')
        
        with open(knowledge_path, 'r', encoding='utf-8') as f:
            self.kb = json.load(f)
    
    def analyze(self, survey, analysis_type='full', user_gender='unknown'):
        """
        执行形象分析
        :param survey: 问卷字典
        :param analysis_type: outfit / hair / full
        :param user_gender: AI识别的用户性别 (male/female/unisex/unknown)
        :return: 分析结果字典（包含三种性别方案）
        """
        face_shape = survey.get('faceShape', '')
        body_type = survey.get('bodyType', '')
        skin_tone = survey.get('skinTone', '')
        occasion = survey.get('occasion', 'daily')
        season = survey.get('season', 'spring')
        
        face_info = self.kb['face_shapes'].get(face_shape, {})
        body_info = self.kb['body_types'].get(body_type, {})
        skin_info = self.kb['skin_tones'].get(skin_tone, {})
        
        result = {
            'traits': {
                'faceShape': face_info.get('name', face_shape or '未知'),
                'bodyType': body_info.get('name', body_type or '未知'),
                'skinTone': skin_info.get('name', skin_tone or '未知'),
            },
            'analysis': {
                'face': face_info.get('description', ''),
                'body': body_info.get('description', ''),
                'skin': skin_info.get('description', ''),
            }
        }
        
        # 生成三种性别方案
        result['genderSchemes'] = self._generate_gender_schemes(
            user_gender, face_info, body_info, skin_info, 
            occasion, season, analysis_type
        )
        
        # 兼容旧版：同时保留顶层 outfit/hair（取用户性别方案）
        user_scheme = result['genderSchemes'].get('user', {})
        if 'outfit' in user_scheme:
            result['outfit'] = user_scheme['outfit']
        if 'hair' in user_scheme:
            result['hair'] = user_scheme['hair']
        
        return result
    
    def _generate_gender_schemes(self, user_gender, face_info, body_info, 
                                  skin_info, occasion, season, analysis_type):
        """
        生成三种性别方案
        - user: 用户被识别出的性别（最匹配）
        - unisex: 中性方案（适合所有性别）
        - other: 另一性别方案（探索不同风格）
        """
        # 标准化性别
        if user_gender not in ('male', 'female', 'unisex'):
            user_gender = 'unisex'
        
        # 确定另一性别
        other_gender = 'female' if user_gender == 'male' else 'male'
        
        schemes = {}
        
        # 1. 用户性别方案（主方案）
        schemes['user'] = {
            'gender': user_gender,
            'label': self._gender_label(user_gender),
            'is_primary': True,
            'hint': f'AI识别你的性别为「{self._gender_label(user_gender)}」，这是为你量身定制的方案',
        }
        
        # 2. 中性方案
        schemes['unisex'] = {
            'gender': 'unisex',
            'label': '中性',
            'is_primary': False,
            'hint': '中性风格，简约百搭，适合追求无性别穿搭的你',
        }
        
        # 3. 另一性别方案
        schemes['other'] = {
            'gender': other_gender,
            'label': self._gender_label(other_gender),
            'is_primary': False,
            'hint': f'尝试「{self._gender_label(other_gender)}」风格，发现不一样的自己。每个人都有探索不同风格的权利 ✨',
        }
        
        # 为每种方案生成穿搭和发型
        for scheme_key, scheme in schemes.items():
            target_gender = scheme['gender']
            
            if analysis_type in ('outfit', 'full'):
                scheme['outfit'] = self._generate_outfit(
                    body_info, skin_info, occasion, season, target_gender
                )
            
            if analysis_type in ('hair', 'full'):
                scheme['hair'] = self._generate_hair(
                    face_info, skin_info, target_gender
                )
        
        return schemes
    
    @staticmethod
    def _gender_label(gender):
        labels = {
            'male': '男性',
            'female': '女性', 
            'unisex': '中性',
            'unknown': '未知',
        }
        return labels.get(gender, '未知')
    
    def _generate_outfit(self, body_info, skin_info, occasion, season, gender='unisex'):
        """
        生成穿搭推荐
        :param gender: 目标性别 (male/female/unisex)
        """
        outfits = self.kb.get('outfits', [])
        matched = []
        
        for outfit in outfits:
            # 性别过滤：outfit 必须匹配目标性别或标记为 universal
            outfit_genders = outfit.get('gender', ['unisex'])
            if isinstance(outfit_genders, str):
                outfit_genders = [outfit_genders]
            
            if gender not in outfit_genders and 'unisex' not in outfit_genders:
                continue
            
            score = 0
            if occasion in outfit.get('occasions', []):
                score += 3
            if season in outfit.get('seasons', []):
                score += 2
            if body_info.get('id') in outfit.get('body_types', []):
                score += 3
            if skin_info.get('id') in outfit.get('skin_tones', []):
                score += 2
            
            if score >= 5 or 'universal' in outfit.get('tags', []):
                matched.append({**outfit, 'score': score})
        
        matched.sort(key=lambda x: x['score'], reverse=True)
        
        if not matched:
            # 降级：如果该性别没有匹配，返回 universal 或 unisex
            matched = [o for o in outfits 
                      if 'universal' in o.get('tags', []) 
                      or 'unisex' in (o.get('gender', ['unisex']) if isinstance(o.get('gender'), list) else [o.get('gender', 'unisex')])][:3]
        
        # 为每个穿搭添加搜索关键词
        enriched_items = []
        for item in matched[:3]:
            enriched = dict(item)
            enriched['search_keywords'] = item.get('name', '')
            enriched_items.append(enriched)
        
        # 添加其他穿搭选择（同性别下未入选的候选）
        other_choices = []
        for o in outfits:
            if o in matched[:3]:
                continue
            o_genders = o.get('gender', ['unisex'])
            if isinstance(o_genders, str):
                o_genders = [o_genders]
            if gender in o_genders or 'unisex' in o_genders:
                other_choices.append({
                    'id': o.get('id'),
                    'name': o.get('name'),
                    'description': o.get('description'),
                    'search_keywords': o.get('name', ''),
                })
        
        return {
            'items': enriched_items,
            'other_choices': other_choices[:6],
            'colorAdvice': {
                'recommended': skin_info.get('recommended_colors', [])[:6],
                'avoid': skin_info.get('avoid_colors', [])[:4],
            },
            'bodyTips': body_info.get('style_tips', []),
        }
    
    def _generate_hair(self, face_info, skin_info, gender='unisex'):
        """
        生成发型推荐
        :param gender: 目标性别 (male/female/unisex)
        """
        hairstyles = self.kb.get('hairstyles', [])
        matched = []
        
        for hs in hairstyles:
            # 性别过滤
            hs_genders = hs.get('gender', ['unisex'])
            if isinstance(hs_genders, str):
                hs_genders = [hs_genders]
            
            if gender not in hs_genders and 'unisex' not in hs_genders:
                continue
            
            score = 0
            if face_info.get('id') in hs.get('face_shapes', []):
                score += 5
            if skin_info.get('id') in hs.get('skin_tones', []):
                score += 2
            
            if score >= 5 or 'universal' in hs.get('tags', []):
                matched.append({**hs, 'score': score})
        
        matched.sort(key=lambda x: x['score'], reverse=True)
        
        if not matched:
            matched = [h for h in hairstyles 
                      if 'universal' in h.get('tags', [])
                      or 'unisex' in (h.get('gender', ['unisex']) if isinstance(h.get('gender'), list) else [h.get('gender', 'unisex')])][:3]
        
        # 为每个匹配的发型添加发质打理方案
        enriched_items = []
        for item in matched[:3]:
            enriched = dict(item)
            enriched['hair_type_care'] = item.get('hair_type_care', {})
            enriched['search_keywords'] = item.get('name', '')
            enriched_items.append(enriched)
        
        # 添加其他发型选择（同性别下未入选的候选）
        other_choices = []
        for hs in hairstyles:
            if hs in matched[:3]:
                continue
            hs_genders = hs.get('gender', ['unisex'])
            if isinstance(hs_genders, str):
                hs_genders = [hs_genders]
            if gender in hs_genders or 'unisex' in hs_genders:
                other_choices.append({
                    'id': hs.get('id'),
                    'name': hs.get('name'),
                    'description': hs.get('description'),
                    'length': hs.get('length'),
                    'search_keywords': hs.get('name', ''),
                })
        
        return {
            'items': enriched_items,
            'other_choices': other_choices[:6],
            'faceTips': face_info.get('hair_tips', []),
            'colorAdvice': {
                'recommended': skin_info.get('hair_colors', []),
                'avoid': skin_info.get('avoid_hair_colors', []),
            }
        }
