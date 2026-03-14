"""
增强版特征工程模块
添加更多与吉凶预测相关的特征
"""

import numpy as np
from typing import Dict, List

# 八卦五行
TRIGRAM_ELEMENTS = {
    '乾': '金', '兑': '金',
    '离': '火',
    '震': '木', '巽': '木',
    '坎': '水',
    '艮': '土', '坤': '土',
}

# 五行生克关系
ELEMENT_CYCLE = {
    '金': {'生': '水', '克': '木', '被生': '土', '被克': '火'},
    '木': {'生': '火', '克': '土', '被生': '水', '被克': '金'},
    '水': {'生': '木', '克': '火', '被生': '金', '被克': '土'},
    '火': {'生': '土', '克': '金', '被生': '木', '被克': '水'},
    '土': {'生': '金', '克': '水', '被生': '火', '被克': '木'},
}

# 六十四卦吉凶等级（基于传统理论）
HEXAGRAM_FORTUNE = {
    # 大吉卦
    '乾为天': 2, '地天泰': 2, '天火同人': 2, '火天大有': 2,
    '泽山咸': 2, '雷风恒': 2, '风雷益': 2, '水火既济': 2,
    # 吉卦
    '水天需': 1, '天水讼': -1, '地泽临': 1, '风天小畜': 1,
    '天泽履': 1, '地天泰': 2, '天地否': -2, '天火同人': 2,
    # 平卦
    '坤为地': 0, '水雷屯': 0, '山水蒙': 0, '水地比': 0,
    # 凶卦
    '天地否': -2, '水泽节': -1, '泽水困': -2, '火水未济': -1,
    '山地剥': -2, '地雷复': 0, '天雷无妄': -1, '山天大畜': 1,
    # 大凶卦
    '坎为水': -2, '离为火': 0, '泽风大过': -2, '雷泽归妹': -1,
}

class FeatureEngineer:
    """特征工程类"""
    
    def __init__(self):
        self.trigrams = ['乾', '兑', '离', '震', '巽', '坎', '艮', '坤']
        self.elements = ['金', '木', '水', '火', '土']
        self.fortune_levels = ['大凶', '凶', '平', '吉', '大吉']
    
    def extract_enhanced_features(self, case: Dict, include_question_type: bool = False) -> np.ndarray:
        """提取增强版特征"""
        features = []
        
        # ===== 基础特征 =====
        # 1. 时间特征 (4维)
        features.append(case['month'] / 12.0)
        features.append(case['day'] / 31.0)
        features.append(case['hour'] / 24.0)
        features.append((case['year'] - 2020) / 10.0)
        
        # 2. 问事类型 (可选，5维)
        if include_question_type:
            question_types = ['财运', '事业', '婚姻', '健康', '诉讼']
            qtype_idx = question_types.index(case['question_type'])
            qtype_onehot = [1 if i == qtype_idx else 0 for i in range(5)]
            features.extend(qtype_onehot)
        
        # ===== 卦象特征 =====
        hexagram = case['hexagram']
        lines = hexagram['lines']
        moving_lines = hexagram['moving_lines']
        
        # 3. 六爻特征 (6维)
        features.extend(lines)
        
        # 4. 动爻 one-hot (6维)
        moving_onehot = [0] * 6
        for pos in moving_lines:
            if 1 <= pos <= 6:
                moving_onehot[pos - 1] = 1
        features.extend(moving_onehot)
        
        # 5. 上下卦 one-hot (16维)
        upper_idx = self.trigrams.index(hexagram['upper_trigram'])
        lower_idx = self.trigrams.index(hexagram['lower_trigram'])
        
        upper_onehot = [1 if i == upper_idx else 0 for i in range(8)]
        lower_onehot = [1 if i == lower_idx else 0 for i in range(8)]
        features.extend(upper_onehot)
        features.extend(lower_onehot)
        
        # ===== 六爻关系特征 =====
        analysis = case['analysis']
        
        # 6. 世应位置 (2维)
        features.append(analysis['shi_position'] / 6.0)
        features.append(analysis['ying_position'] / 6.0)
        
        # 7. 五行关系 one-hot (5维)
        element_relations = {'生': 0, '被生': 1, '克': 2, '被克': 3, '比和': 4}
        relation = analysis['element_relation']
        relation_idx = element_relations.get(relation, 4)
        relation_onehot = [1 if i == relation_idx else 0 for i in range(5)]
        features.extend(relation_onehot)
        
        # 8. 动爻统计 (2维)
        num_moving = len(moving_lines)
        features.append(num_moving / 6.0)
        features.append(1 if num_moving > 0 else 0)
        
        # ===== 新增：五行生克特征 =====
        # 9. 上下卦五行 (2维 one-hot，共10维)
        upper_element = TRIGRAM_ELEMENTS[hexagram['upper_trigram']]
        lower_element = TRIGRAM_ELEMENTS[hexagram['lower_trigram']]
        
        upper_elem_onehot = [1 if e == upper_element else 0 for e in self.elements]
        lower_elem_onehot = [1 if e == lower_element else 0 for e in self.elements]
        features.extend(upper_elem_onehot)
        features.extend(lower_elem_onehot)
        
        # 10. 上下卦五行关系 (4维 one-hot)
        # 上卦对下卦的关系
        upper_to_lower = ELEMENT_CYCLE[upper_element].get('克' if ELEMENT_CYCLE[upper_element]['克'] == lower_element else 
                                                         '被克' if ELEMENT_CYCLE[upper_element]['被克'] == lower_element else
                                                         '生' if ELEMENT_CYCLE[upper_element]['生'] == lower_element else
                                                         '被生' if ELEMENT_CYCLE[upper_element]['被生'] == lower_element else
                                                         '比和', '比和')
        elem_relation_onehot = [1 if r == upper_to_lower else 0 for r in ['生', '被生', '克', '被克', '比和']]
        features.extend(elem_relation_onehot)
        
        # ===== 新增：动爻位置特征 =====
        # 11. 动爻位置统计 (6维)
        # 初爻、二爻、三爻、四爻、五爻、上爻是否有动
        for i in range(6):
            features.append(1 if (i + 1) in moving_lines else 0)
        
        # 12. 动爻阴阳分布 (2维)
        yin_moving = sum(1 for pos in moving_lines if lines[pos - 1] == 0)
        yang_moving = sum(1 for pos in moving_lines if lines[pos - 1] == 1)
        features.append(yin_moving / 6.0)
        features.append(yang_moving / 6.0)
        
        # ===== 新增：特殊格局特征 =====
        # 13. 特殊卦象 (4维)
        hexagram_name = hexagram.get('name', '')
        from liuyao.engine import LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS, YOUHUN_HEXAGRAMS, GUIHUN_HEXAGRAMS
        features.append(1 if hexagram_name in LIUCHONG_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in LIUHE_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in YOUHUN_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in GUIHUN_HEXAGRAMS else 0)
        
        # 14. 特殊格局 one-hot (5维)
        if hexagram_name in LIUCHONG_HEXAGRAMS:
            special_pattern = '六冲'
        elif hexagram_name in LIUHE_HEXAGRAMS:
            special_pattern = '六合'
        elif hexagram_name in YOUHUN_HEXAGRAMS:
            special_pattern = '游魂'
        elif hexagram_name in GUIHUN_HEXAGRAMS:
            special_pattern = '归魂'
        else:
            special_pattern = '普通'
        
        pattern_types = ['普通', '六冲', '六合', '游魂', '归魂']
        pattern_idx = pattern_types.index(special_pattern)
        pattern_onehot = [1 if i == pattern_idx else 0 for i in range(5)]
        features.extend(pattern_onehot)
        
        # ===== 新增：卦象吉凶先验特征 =====
        # 15. 卦象传统吉凶等级 (5维 one-hot)
        fortune_score = HEXAGRAM_FORTUNE.get(hexagram_name, 0)
        # 将-2到2映射到0到4
        fortune_idx = fortune_score + 2
        fortune_onehot = [1 if i == fortune_idx else 0 for i in range(5)]
        features.extend(fortune_onehot)
        
        # 16. 动爻与用神关系 (1维)
        # 动爻是否包含世爻或应爻
        shi_pos = analysis['shi_position']
        ying_pos = analysis['ying_position']
        has_shi_moving = 1 if shi_pos in moving_lines else 0
        has_ying_moving = 1 if ying_pos in moving_lines else 0
        features.append(has_shi_moving)
        features.append(has_ying_moving)
        
        # 17. 变卦变化程度 (1维)
        # 动爻数量表示变化程度
        features.append(num_moving / 6.0)
        
        return np.array(features, dtype=np.float32)
    
    def get_feature_names(self, include_question_type: bool = False) -> List[str]:
        """获取特征名称列表"""
        names = []
        
        # 基础特征
        names.extend(['month', 'day', 'hour', 'year'])
        
        if include_question_type:
            names.extend([f'qtype_{t}' for t in ['财运', '事业', '婚姻', '健康', '诉讼']])
        
        # 卦象特征
        names.extend([f'line_{i}' for i in range(6)])
        names.extend([f'moving_{i}' for i in range(6)])
        names.extend([f'upper_{t}' for t in ['乾', '兑', '离', '震', '巽', '坎', '艮', '坤']])
        names.extend([f'lower_{t}' for t in ['乾', '兑', '离', '震', '巽', '坎', '艮', '坤']])
        
        # 六爻关系
        names.extend(['shi_pos', 'ying_pos'])
        names.extend([f'relation_{r}' for r in ['生', '被生', '克', '被克', '比和']])
        names.extend(['num_moving', 'has_moving'])
        
        # 五行特征
        names.extend([f'upper_elem_{e}' for e in ['金', '木', '水', '火', '土']])
        names.extend([f'lower_elem_{e}' for e in ['金', '木', '水', '火', '土']])
        names.extend([f'elem_relation_{r}' for r in ['生', '被生', '克', '被克', '比和']])
        
        # 动爻位置
        names.extend([f'moving_pos_{i}' for i in range(6)])
        names.extend(['yin_moving', 'yang_moving'])
        
        # 特殊格局
        names.extend(['liuchong', 'liuhe', 'youhun', 'guihun'])
        names.extend([f'pattern_{p}' for p in ['普通', '六冲', '六合', '游魂', '归魂']])
        
        # 吉凶先验
        names.extend([f'fortune_prior_{f}' for f in ['大凶', '凶', '平', '吉', '大吉']])
        
        # 其他
        names.extend(['shi_moving', 'ying_moving', 'change_degree'])
        
        return names


def test_feature_engineer():
    """测试特征工程"""
    import json
    
    # 加载测试数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    engineer = FeatureEngineer()
    
    # 测试特征提取
    case = cases[0]
    features = engineer.extract_enhanced_features(case)
    feature_names = engineer.get_feature_names()
    
    print(f"案例: {case['hexagram']['name']}")
    print(f"特征维度: {len(features)}")
    print(f"特征名称数: {len(feature_names)}")
    print("\n前20个特征:")
    for name, value in zip(feature_names[:20], features[:20]):
        print(f"  {name}: {value}")
    
    return features


if __name__ == '__main__':
    import os
    test_feature_engineer()
