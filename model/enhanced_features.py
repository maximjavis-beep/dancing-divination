#!/usr/bin/env python3
"""
增强版特征工程
添加更多六爻专业特征以提高模型准确率
"""

import numpy as np
from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import TRIGRAMS, LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS, YOUHUN_HEXAGRAMS, GUIHUN_HEXAGRAMS

class EnhancedFeatureExtractor:
    """增强版特征提取器"""
    
    # 五行生克关系
    ELEMENTS = ['金', '木', '水', '火', '土']
    ELEMENT_CYCLE = {'金': '水', '水': '木', '木': '火', '火': '土', '土': '金'}  # 生
    ELEMENT_RESTRICT = {'金': '木', '木': '土', '土': '水', '水': '火', '火': '金'}  # 克
    
    # 地支
    BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    BRANCH_ELEMENTS = {
        '子': '水', '丑': '土', '寅': '木', '卯': '木',
        '辰': '土', '巳': '火', '午': '火', '未': '土',
        '申': '金', '酉': '金', '戌': '土', '亥': '水'
    }
    
    def __init__(self):
        self.feature_names = []
    
    def extract_features(self, case: Dict, include_question_type: bool = False) -> np.ndarray:
        """提取增强版特征"""
        features = []
        self.feature_names = []
        
        # ===== 1. 时间特征 (增强) =====
        # 月份节气特征
        month = case['month']
        features.append(month / 12.0)  # 归一化月份
        features.append(np.sin(2 * np.pi * month / 12))  # 月份周期性
        features.append(np.cos(2 * np.pi * month / 12))
        self.feature_names.extend(['month_norm', 'month_sin', 'month_cos'])
        
        # 日期特征
        day = case['day']
        features.append(day / 31.0)
        features.append(np.sin(2 * np.pi * day / 31))
        self.feature_names.extend(['day_norm', 'day_sin'])
        
        # 时辰特征
        hour = case['hour']
        features.append(hour / 24.0)
        # 十二时辰对应
        shichen = (hour + 1) // 2 % 12
        shichen_onehot = [1 if i == shichen else 0 for i in range(12)]
        features.extend(shichen_onehot)
        self.feature_names.extend(['hour_norm'] + [f'shichen_{i}' for i in range(12)])
        
        # ===== 2. 卦象特征 (增强) =====
        hexagram = case['hexagram']
        lines = hexagram['lines']
        moving_lines = hexagram.get('moving_lines', [])
        
        # 六爻阴阳分布
        yang_count = sum(lines)
        yin_count = 6 - yang_count
        features.append(yang_count / 6.0)
        features.append(yin_count / 6.0)
        features.append(abs(yang_count - yin_count) / 6.0)  # 阴阳平衡度
        self.feature_names.extend(['yang_ratio', 'yin_ratio', 'balance'])
        
        # 动爻特征 (增强)
        moving_count = len(moving_lines)
        features.append(moving_count / 6.0)
        features.append(1 if moving_count == 0 else 0)  # 静卦
        features.append(1 if moving_count == 1 else 0)  # 单动
        features.append(1 if moving_count >= 2 else 0)  # 多动
        self.feature_names.extend(['moving_count', 'static_hex', 'single_moving', 'multi_moving'])
        
        # 动爻位置 one-hot
        moving_position = [0] * 6
        for pos in moving_lines:
            if 1 <= pos <= 6:
                moving_position[pos - 1] = 1
        features.extend(moving_position)
        self.feature_names.extend([f'moving_pos_{i}' for i in range(6)])
        
        # 动爻阴阳
        moving_yang = sum(1 for pos in moving_lines if lines[pos-1] == 1)
        moving_yin = moving_count - moving_yang
        features.append(moving_yang / 6.0 if moving_count > 0 else 0)
        features.append(moving_yin / 6.0 if moving_count > 0 else 0)
        self.feature_names.extend(['moving_yang', 'moving_yin'])
        
        # ===== 3. 上下卦特征 (增强) =====
        upper = hexagram['upper_trigram']
        lower = hexagram['lower_trigram']
        
        # 上下卦五行
        upper_element = TRIGRAMS[upper]['element']
        lower_element = TRIGRAMS[lower]['element']
        
        # 五行生克关系
        element_relations = self._get_element_relation(upper_element, lower_element)
        features.extend(element_relations)
        self.feature_names.extend(['upper_gen_lower', 'upper_ke_lower', 'upper_bi_lower'])
        
        # 上下卦 one-hot
        trigram_names = list(TRIGRAMS.keys())
        upper_idx = trigram_names.index(upper)
        lower_idx = trigram_names.index(lower)
        
        upper_onehot = [1 if i == upper_idx else 0 for i in range(8)]
        lower_onehot = [1 if i == lower_idx else 0 for i in range(8)]
        features.extend(upper_onehot)
        features.extend(lower_onehot)
        self.feature_names.extend([f'upper_{t}' for t in trigram_names])
        self.feature_names.extend([f'lower_{t}' for t in trigram_names])
        
        # ===== 4. 世应特征 (增强) =====
        shi = case['analysis']['shi_position']
        ying = case['analysis']['ying_position']
        
        features.append(shi / 6.0)
        features.append(ying / 6.0)
        # 世应距离
        distance = abs(shi - ying)
        features.append(distance / 6.0)
        # 世应在位（初爻=1，上爻=6）
        features.append(1 if shi <= 2 else 0)  # 世爻在下卦
        features.append(1 if shi >= 5 else 0)  # 世爻在上卦
        self.feature_names.extend(['shi_pos', 'ying_pos', 'shi_ying_dist', 'shi_lower', 'shi_upper'])
        
        # 世应 one-hot
        shi_onehot = [1 if i == shi - 1 else 0 for i in range(6)]
        ying_onehot = [1 if i == ying - 1 else 0 for i in range(6)]
        features.extend(shi_onehot)
        features.extend(ying_onehot)
        self.feature_names.extend([f'shi_at_{i}' for i in range(6)])
        self.feature_names.extend([f'ying_at_{i}' for i in range(6)])
        
        # ===== 5. 用神特征 (增强) =====
        deity_type = case['analysis'].get('deity_type', '妻财')
        deity_element = case['analysis'].get('deity_element', '金')
        element_relation = case['analysis'].get('element_relation', '比和')
        
        # 用神类型 one-hot
        deity_types = ['父母', '官鬼', '妻财', '子孙', '兄弟']
        deity_idx = deity_types.index(deity_type) if deity_type in deity_types else 2
        deity_onehot = [1 if i == deity_idx else 0 for i in range(5)]
        features.extend(deity_onehot)
        self.feature_names.extend([f'deity_{t}' for t in deity_types])
        
        # 用神五行
        element_idx = self.ELEMENTS.index(deity_element) if deity_element in self.ELEMENTS else 0
        element_onehot = [1 if i == element_idx else 0 for i in range(5)]
        features.extend(element_onehot)
        self.feature_names.extend([f'deity_elem_{e}' for e in self.ELEMENTS])
        
        # 五行关系 one-hot
        relation_map = {'生': 0, '被生': 1, '克': 2, '被克': 3, '比和': 4}
        relation_idx = relation_map.get(element_relation, 4)
        relation_onehot = [1 if i == relation_idx else 0 for i in range(5)]
        features.extend(relation_onehot)
        self.feature_names.extend(['rel_sheng', 'rel_beisheng', 'rel_ke', 'rel_beike', 'rel_bihe'])
        
        # ===== 6. 特殊格局 (增强) =====
        hexagram_name = hexagram.get('name', '')
        
        # 六冲/六合/游魂/归魂
        is_liuchong = 1 if hexagram_name in LIUCHONG_HEXAGRAMS else 0
        is_liuhe = 1 if hexagram_name in LIUHE_HEXAGRAMS else 0
        is_youhun = 1 if hexagram_name in YOUHUN_HEXAGRAMS else 0
        is_guihun = 1 if hexagram_name in GUIHUN_HEXAGRAMS else 0
        
        features.extend([is_liuchong, is_liuhe, is_youhun, is_guihun])
        self.feature_names.extend(['liuchong', 'liuhe', 'youhun', 'guihun'])
        
        # 特殊格局组合
        features.append(is_liuchong * is_liuhe)  # 不可能同时为1，但保留
        features.append(is_youhun + is_guihun)  # 游魂或归魂
        self.feature_names.extend(['special_combo', 'hun_type'])
        
        # ===== 7. 变卦特征 (新增) =====
        changed = case.get('changed_hexagram', {})
        if changed and 'name' in changed:
            changed_name = changed['name']
            # 变卦是否也是特殊格局
            features.append(1 if changed_name in LIUCHONG_HEXAGRAMS else 0)
            features.append(1 if changed_name in LIUHE_HEXAGRAMS else 0)
            # 本卦变卦是否同为六冲/六合
            features.append(is_liuchong and (changed_name in LIUCHONG_HEXAGRAMS))
            features.append(is_liuhe and (changed_name in LIUHE_HEXAGRAMS))
        else:
            features.extend([0, 0, 0, 0])
        self.feature_names.extend(['changed_liuchong', 'changed_liuhe', 'both_liuchong', 'both_liuhe'])
        
        # ===== 8. 交互特征 (新增) =====
        # 用神与动爻关系
        deity_pos = shi  # 简化：假设用神在世爻位置
        moving_near_deity = sum(1 for pos in moving_lines if abs(pos - deity_pos) <= 1)
        features.append(moving_near_deity / 6.0)
        self.feature_names.append('moving_near_deity')
        
        # 动爻与世应关系
        moving_near_shi = sum(1 for pos in moving_lines if abs(pos - shi) <= 1)
        moving_near_ying = sum(1 for pos in moving_lines if abs(pos - ying) <= 1)
        features.append(moving_near_shi / 6.0)
        features.append(moving_near_ying / 6.0)
        self.feature_names.extend(['moving_near_shi', 'moving_near_ying'])
        
        # ===== 9. 问事类型 (可选) =====
        if include_question_type:
            question_type = case.get('question_type', '财运')
            question_types = ['财运', '事业', '爱情', '健康', '诉讼']
            qtype_idx = question_types.index(question_type) if question_type in question_types else 0
            qtype_onehot = [1 if i == qtype_idx else 0 for i in range(5)]
            features.extend(qtype_onehot)
            self.feature_names.extend([f'qtype_{t}' for t in question_types])
        
        return np.array(features)
    
    def _get_element_relation(self, elem1: str, elem2: str) -> List[float]:
        """获取两个五行的关系 [生, 克, 比和]"""
        if elem1 == elem2:
            return [0, 0, 1]  # 比和
        elif self.ELEMENT_CYCLE.get(elem1) == elem2:
            return [1, 0, 0]  # elem1 生 elem2
        elif self.ELEMENT_RESTRICT.get(elem1) == elem2:
            return [0, 1, 0]  # elem1 克 elem2
        elif self.ELEMENT_CYCLE.get(elem2) == elem1:
            return [0, 0, 0]  # 被生（用0表示，因为不对称）
        elif self.ELEMENT_RESTRICT.get(elem2) == elem1:
            return [0, 0, 0]  # 被克
        else:
            return [0, 0, 0]
    
    def get_feature_count(self, include_question_type: bool = False) -> int:
        """获取特征数量"""
        dummy_case = {
            'year': 2024, 'month': 3, 'day': 14, 'hour': 10,
            'question_type': '财运',
            'hexagram': {
                'name': '地天泰', 'upper_trigram': '坤', 'lower_trigram': '乾',
                'lines': [1, 1, 1, 0, 0, 0], 'moving_lines': [1]
            },
            'changed_hexagram': {'name': '地泽临'},
            'analysis': {
                'shi_position': 2, 'ying_position': 5,
                'deity_type': '妻财', 'deity_element': '金', 'element_relation': '生'
            }
        }
        features = self.extract_features(dummy_case, include_question_type)
        return len(features)


if __name__ == '__main__':
    extractor = EnhancedFeatureExtractor()
    
    # 测试特征提取
    test_case = {
        'year': 2024, 'month': 3, 'day': 14, 'hour': 10,
        'question_type': '财运',
        'hexagram': {
            'name': '地天泰', 'upper_trigram': '坤', 'lower_trigram': '乾',
            'lines': [1, 1, 1, 0, 0, 0], 'moving_lines': [1],
            'special_pattern': '六合'
        },
        'changed_hexagram': {'name': '地泽临'},
        'analysis': {
            'shi_position': 2, 'ying_position': 5,
            'deity_type': '妻财', 'deity_element': '金', 'element_relation': '生'
        }
    }
    
    features = extractor.extract_features(test_case)
    print(f"特征数量: {len(features)}")
    print(f"特征名数量: {len(extractor.feature_names)}")
    print(f"\n前20个特征名: {extractor.feature_names[:20]}")
    print(f"\n特征示例 (前10个): {features[:10]}")
    
    # 对比旧版特征数量
    print(f"\n对比:")
    print(f"  旧版特征数: 50")
    print(f"  新版特征数: {len(features)}")
    print(f"  增加: {len(features) - 50} 个特征")
