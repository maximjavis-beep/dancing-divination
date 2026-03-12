"""
六爻规则引擎
基于传统六爻规则计算吉凶分数
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS

class RuleEngine:
    """六爻规则引擎"""
    
    # 吉凶等级映射
    FORTUNE_LEVELS = ['大凶', '凶', '平', '吉', '大吉']
    
    # 五行生克关系
    ELEMENTS = ['金', '木', '水', '火', '土']
    
    # 五行相生：金->水->木->火->土->金
    SHENG_RELATION = {
        '金': '水',
        '水': '木',
        '木': '火',
        '火': '土',
        '土': '金'
    }
    
    # 五行相克：金->木->土->水->火->金
    KE_RELATION = {
        '金': '木',
        '木': '土',
        '土': '水',
        '水': '火',
        '火': '金'
    }
    
    # 规则权重
    RULE_WEIGHTS = {
        'deity_sheng': 20,      # 用神被生
        'deity_bihe': 10,       # 用神比和
        'deity_ke': -20,        # 用神被克
        'liuchong': -15,        # 六冲卦
        'liuhe': 15,            # 六合卦
        'moving_sheng': 10,     # 动爻生用神
        'moving_ke': -10,       # 动爻克用神
        'shi_wang': 10,         # 世爻旺相
        'deity_kongwang': -15,  # 用神空亡
    }
    
    def __init__(self):
        pass
    
    def _get_element_relation(self, element1, element2):
        """获取两个五行的关系"""
        if element1 == element2:
            return '比和'
        if self.SHENG_RELATION.get(element1) == element2:
            return '生'
        if self.KE_RELATION.get(element1) == element2:
            return '克'
        if self.SHENG_RELATION.get(element2) == element1:
            return '被生'
        if self.KE_RELATION.get(element2) == element1:
            return '被克'
        return '比和'
    
    def _is_liuchong(self, hexagram_name):
        """判断是否为六冲卦"""
        return hexagram_name in LIUCHONG_HEXAGRAMS
    
    def _is_liuhe(self, hexagram_name):
        """判断是否为六合卦"""
        return hexagram_name in LIUHE_HEXAGRAMS
    
    def _is_kongwang(self, position, day_gan, day_zhi):
        """
        判断某爻是否空亡
        简化版：根据日柱地支判断
        """
        # 空亡地支对（简化）
        kongwang_pairs = {
            '甲': ['申', '酉'],
            '乙': ['午', '未'],
            '丙': ['辰', '巳'],
            '丁': ['寅', '卯'],
            '戊': ['子', '丑'],
            '己': ['申', '酉'],
            '庚': ['午', '未'],
            '辛': ['辰', '巳'],
            '壬': ['寅', '卯'],
            '癸': ['子', '丑'],
        }
        
        # 简化处理：假设空亡概率为10%
        import random
        return random.random() < 0.1
    
    def calculate_score(self, case):
        """
        计算案例的吉凶分数
        
        Args:
            case: 案例字典
            
        Returns:
            dict: 包含分数和详细规则分析
        """
        score = 0
        details = []
        
        hexagram = case.get('hexagram', {})
        analysis = case.get('analysis', {})
        
        # 1. 用神旺衰分析
        element_relation = analysis.get('element_relation', '比和')
        deity_element = analysis.get('deity_element', '金')
        
        if element_relation == '被生':
            score += self.RULE_WEIGHTS['deity_sheng']
            details.append({
                'rule': '用神被生',
                'score': self.RULE_WEIGHTS['deity_sheng'],
                'description': f'用神{deity_element}得生扶，旺相有力'
            })
        elif element_relation == '比和':
            score += self.RULE_WEIGHTS['deity_bihe']
            details.append({
                'rule': '用神比和',
                'score': self.RULE_WEIGHTS['deity_bihe'],
                'description': f'用神{deity_element}得比和，力量平稳'
            })
        elif element_relation == '被克':
            score += self.RULE_WEIGHTS['deity_ke']
            details.append({
                'rule': '用神被克',
                'score': self.RULE_WEIGHTS['deity_ke'],
                'description': f'用神{deity_element}受克制，力量衰弱'
            })
        
        # 2. 六冲/六合卦分析
        hexagram_name = hexagram.get('name', '')
        if self._is_liuchong(hexagram_name):
            score += self.RULE_WEIGHTS['liuchong']
            details.append({
                'rule': '六冲卦',
                'score': self.RULE_WEIGHTS['liuchong'],
                'description': f'{hexagram_name}为六冲卦，事多变动'
            })
        elif self._is_liuhe(hexagram_name):
            score += self.RULE_WEIGHTS['liuhe']
            details.append({
                'rule': '六合卦',
                'score': self.RULE_WEIGHTS['liuhe'],
                'description': f'{hexagram_name}为六合卦，事多和合'
            })
        
        # 3. 动爻分析
        moving_lines = hexagram.get('moving_lines', [])
        if moving_lines:
            # 简化：假设动爻生用神概率50%
            import random
            if random.random() > 0.5:
                score += self.RULE_WEIGHTS['moving_sheng']
                details.append({
                    'rule': '动爻生用神',
                    'score': self.RULE_WEIGHTS['moving_sheng'],
                    'description': '动爻生扶用神，吉象'
                })
            else:
                score += self.RULE_WEIGHTS['moving_ke']
                details.append({
                    'rule': '动爻克用神',
                    'score': self.RULE_WEIGHTS['moving_ke'],
                    'description': '动爻克制用神，凶象'
                })
        
        # 4. 世爻旺相分析
        shi_position = analysis.get('shi_position', 1)
        # 世爻在2-5位为旺相（简化判断）
        if 2 <= shi_position <= 5:
            score += self.RULE_WEIGHTS['shi_wang']
            details.append({
                'rule': '世爻旺相',
                'score': self.RULE_WEIGHTS['shi_wang'],
                'description': f'世爻在{shi_position}位，得位旺相'
            })
        
        # 5. 用神空亡分析（简化）
        import random
        if random.random() < 0.1:  # 10%概率空亡
            score += self.RULE_WEIGHTS['deity_kongwang']
            details.append({
                'rule': '用神空亡',
                'score': self.RULE_WEIGHTS['deity_kongwang'],
                'description': '用神逢空亡，力量不显'
            })
        
        # 计算吉凶等级
        fortune_level = self.score_to_fortune(score)
        
        return {
            'score': score,
            'fortune_level': fortune_level,
            'details': details,
            'rule_count': len(details)
        }
    
    def score_to_fortune(self, score):
        """
        将分数转换为吉凶等级
        
        分数区间：
        -40以下：大凶
        -39 ~ -10：凶
        -9 ~ 9：平
        10 ~ 39：吉
        40以上：大吉
        """
        if score <= -40:
            return '大凶'
        elif score <= -10:
            return '凶'
        elif score <= 9:
            return '平'
        elif score <= 39:
            return '吉'
        else:
            return '大吉'
    
    def predict(self, case):
        """
        预测接口
        
        Args:
            case: 案例字典
            
        Returns:
            dict: 预测结果
        """
        result = self.calculate_score(case)
        
        return {
            'fortune_level': result['fortune_level'],
            'score': result['score'],
            'probabilities': self._get_probabilities(result['score']),
            'rule_details': result['details'],
            'method': 'rule_engine'
        }
    
    def _get_probabilities(self, score):
        """
        根据分数获取各吉凶等级的概率分布
        """
        # 基于分数计算softmax概率
        import math
        
        # 基准概率
        base_probs = [0.1, 0.2, 0.4, 0.2, 0.1]  # 大凶, 凶, 平, 吉, 大吉
        
        # 根据分数调整
        if score <= -40:
            probs = [0.6, 0.3, 0.08, 0.015, 0.005]
        elif score <= -10:
            probs = [0.15, 0.5, 0.25, 0.08, 0.02]
        elif score <= 9:
            probs = [0.05, 0.2, 0.5, 0.2, 0.05]
        elif score <= 39:
            probs = [0.02, 0.08, 0.25, 0.5, 0.15]
        else:
            probs = [0.005, 0.015, 0.08, 0.3, 0.6]
        
        return {
            '大吉': probs[4],
            '吉': probs[3],
            '平': probs[2],
            '凶': probs[1],
            '大凶': probs[0]
        }


if __name__ == '__main__':
    # 测试规则引擎
    engine = RuleEngine()
    
    # 测试案例
    test_case = {
        'hexagram': {
            'name': '天风姤',
            'upper_trigram': '乾',
            'lower_trigram': '巽',
            'lines': [1, 1, 1, 1, 1, 0],
            'moving_lines': [6]
        },
        'analysis': {
            'shi_position': 1,
            'ying_position': 4,
            'deity_type': '妻财',
            'deity_element': '金',
            'element_relation': '比和'
        }
    }
    
    result = engine.predict(test_case)
    print(f"预测结果: {result['fortune_level']}")
    print(f"分数: {result['score']}")
    print(f"概率分布: {result['probabilities']}")
    print("\n规则明细:")
    for detail in result['rule_details']:
        print(f"  - {detail['rule']}: {detail['score']:+d} ({detail['description']})")
