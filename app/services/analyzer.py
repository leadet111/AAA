"""
穿搭发型分析引擎
核心推荐算法，原生APP和PWA共用
"""

import json
import os
import hashlib


class StyleAnalyzer:
    """形象分析引擎"""
    
    def __init__(self, knowledge_path=None):
        if knowledge_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            knowledge_path = os.path.join(base_dir, 'data', 'style_knowledge.json')
        
        with open(knowledge_path, 'r', encoding='utf-8') as f:
            self.kb = json.load(f)
    
    def analyze(self, survey, analysis_type='full'):
        """
        执行形象分析
        :param survey: 问卷字典
        :param analysis_type: outfit / hair / full
        :return: 分析结果字典
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
        
        if analysis_type in ('outfit', 'full'):
            result['outfit'] = self._generate_outfit(
                body_info, skin_info, occasion, season
            )
        
        if analysis_type in ('hair', 'full'):
            result['hair'] = self._generate_hair(
                face_info, skin_info
            )
        
        return result
    
    def _generate_outfit(self, body_info, skin_info, occasion, season):
        """生成穿搭推荐"""
        outfits = self.kb.get('outfits', [])
        matched = []
        
        for outfit in outfits:
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
            matched = [o for o in outfits if 'universal' in o.get('tags', [])][:3]
        
        return {
            'items': matched[:3],
            'colorAdvice': {
                'recommended': skin_info.get('recommended_colors', [])[:6],
                'avoid': skin_info.get('avoid_colors', [])[:4],
            },
            'bodyTips': body_info.get('style_tips', []),
        }
    
    def _generate_hair(self, face_info, skin_info):
        """生成发型推荐"""
        hairstyles = self.kb.get('hairstyles', [])
        matched = []
        
        for hs in hairstyles:
            score = 0
            if face_info.get('id') in hs.get('face_shapes', []):
                score += 5
            if skin_info.get('id') in hs.get('skin_tones', []):
                score += 2
            
            if score >= 5 or 'universal' in hs.get('tags', []):
                matched.append({**hs, 'score': score})
        
        matched.sort(key=lambda x: x['score'], reverse=True)
        
        if not matched:
            matched = [h for h in hairstyles if 'universal' in h.get('tags', [])][:3]
        
        return {
            'items': matched[:3],
            'faceTips': face_info.get('hair_tips', []),
            'colorAdvice': {
                'recommended': skin_info.get('hair_colors', []),
                'avoid': skin_info.get('avoid_hair_colors', []),
            }
        }
