#!/usr/bin/env python3
"""
基于六爻理论的案例生成器
根据传统理论生成更合理的标签
"""

import json
import random
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import LiuYaoEngine, TRIGRAMS, LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS

class TheoryBasedCaseGenerator:
    """基于六爻理论的案例生成器"""
    
    QUESTION_TYPES = ['财运', '事业', '婚姻', '健康', '诉讼']
    FORTUNE_LEVELS = ['大吉', '吉', '平', '凶', '大凶']
    
    # 六十四卦传统吉凶（基于《周易》和六爻理论）
    HEXAGRAM_FORTUNE = {
        # 乾宫
        '乾为天': 2,      # 纯阳之卦，大吉
        '天风姤': -1,     # 一女遇五男，凶
        '天山遁': -1,     # 退避之象，凶
        '天地否': -2,     # 天地不交，大凶
        '风地观': 0,      # 观察之象，平
        '山地剥': -2,     # 剥落之象，大凶
        '火地晋': 1,      # 日出地上，吉
        '火天大有': 2,    # 盛大丰有，大吉
        
        # 兑宫
        '兑为泽': 1,      # 喜悦之象，吉
        '泽水困': -2,     # 困穷之象，大凶
        '泽地萃': 1,      # 聚集之象，吉
        '泽山咸': 2,      # 交感之象，大吉（婚姻吉）
        '水山蹇': -1,     # 蹇难之象，凶
        '地山谦': 2,      # 谦虚之象，大吉
        '雷山小过': -1,   # 小有过越，凶
        '雷泽归妹': -1,   # 嫁娶之象，凶（婚姻有变）
        
        # 离宫
        '离为火': 0,      # 光明之象，平
        '火山旅': -1,     # 旅行之象，凶
        '火风鼎': 1,      # 鼎新之象，吉
        '水火未济': -1,   # 未成之象，凶
        '山水蒙': 0,      # 蒙昧之象，平
        '风水涣': 0,      # 涣散之象，平
        '天水讼': -2,     # 诉讼之象，大凶
        '天火同人': 2,    # 和同之象，大吉
        
        # 震宫
        '震为雷': 0,      # 震动之象，平
        '雷地豫': 1,      # 喜悦之象，吉
        '雷水解': 1,      # 解脱之象，吉
        '雷风恒': 2,      # 恒久之象，大吉
        '地风升': 1,      # 上升之象，吉
        '水风井': 0,      # 井养之象，平
        '泽风大过': -2,   # 大有过越，大凶
        '泽雷随': 0,      # 随从之象，平
        
        # 巽宫
        '巽为风': 0,      # 随顺之象，平
        '风天小畜': 1,    # 小有蓄积，吉
        '风火家人': 2,    # 家庭和睦，大吉
        '风雷益': 2,      # 增益之象，大吉
        '天雷无妄': -1,   # 无妄之灾，凶
        '火雷噬嗑': 0,    # 咬合之象，平
        '山雷颐': 1,      # 颐养之象，吉
        '山风蛊': -2,     # 蛊惑之象，大凶
        
        # 坎宫
        '坎为水': -2,     # 险陷之象，大凶
        '水泽节': 0,      # 节制之象，平
        '水雷屯': -1,     # 屯难之象，凶
        '水火既济': 2,    # 既成之象，大吉
        '泽火革': 1,      # 变革之象，吉
        '雷火丰': 2,      # 丰盛之象，大吉
        '地火明夷': -2,   # 光明受伤，大凶
        '地水师': -1,     # 军队之象，凶
        
        # 艮宫
        '艮为山': 0,      # 止静之象，平
        '山火贲': 1,      # 文饰之象，吉
        '山天大畜': 1,    # 大有蓄积，吉
        '山泽损': -1,     # 减损之象，凶
        '火泽睽': -1,     # 乖睽之象，凶
        '天泽履': 1,      # 履行之象，吉
        '风泽中孚': 2,    # 诚信之象，大吉
        '风山渐': 1,      # 渐进之象，吉
        
        # 坤宫
        '坤为地': 0,      # 柔顺之象，平
        '地雷复': 1,      # 回复之象，吉
        '地泽临': 1,      # 临莅之象，吉
        '地天泰': 2,      # 通泰之象，大吉
        '雷天大壮': 1,    # 大壮之象，吉
        '泽天夬': 1,      # 决断之象，吉
        '水天需': 0,      # 等待之象，平
        '水地比': 1,      # 亲比之象，吉
    }
    
    # 问事类型与卦象的关联权重
    QUESTION_HEXAGRAM_WEIGHTS = {
        '财运': {
            '大有': 2, '小畜': 1, '丰': 2, '泰': 1, '比': 1,
            '损': -2, '困': -2, '剥': -2, '蹇': -1,
        },
        '事业': {
            '乾': 2, '升': 2, '晋': 2, '鼎': 1, '革': 1,
            '遁': -1, '否': -2, '明夷': -2, '困': -1,
        },
        '婚姻': {
            '咸': 2, '恒': 2, '家人': 2, '泰': 1, '益': 1,
            '姤': -2, '归妹': -1, '睽': -1, '革': -1,
        },
        '健康': {
            '颐': 2, '复': 2, '泰': 1, '既济': 1,
            '坎': -2, '明夷': -2, '蛊': -2, '讼': -1,
        },
        '诉讼': {
            '讼': -2, '师': -1, '夬': 1, '履': 1,
            '比': 1, '同人': 1, '大有': 1,
        },
    }
    
    def __init__(self, seed=42):
        self.engine = LiuYaoEngine()
        self.random = random.Random(seed)
    
    def generate_random_time(self, start_year=2020, end_year=2024):
        """生成随机时间"""
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        delta = end - start
        random_days = self.random.randint(0, delta.days)
        random_hours = self.random.randint(0, 23)
        return start + timedelta(days=random_days, hours=random_hours)
    
    def calculate_fortune_score(self, hexagram_name: str, question_type: str, 
                                 element_relation: str, has_moving: bool) -> int:
        """
        基于六爻理论计算吉凶分数
        
        Returns:
            -2: 大凶, -1: 凶, 0: 平, 1: 吉, 2: 大吉
        """
        # 1. 基础卦象吉凶
        base_score = self.HEXAGRAM_FORTUNE.get(hexagram_name, 0)
        
        # 2. 问事类型调整
        question_weights = self.QUESTION_HEXAGRAM_WEIGHTS.get(question_type, {})
        for key, weight in question_weights.items():
            if key in hexagram_name:
                base_score += weight
                break
        
        # 3. 五行关系调整
        relation_adjust = {
            '生': 1,
            '被生': 0,
            '克': -1,
            '被克': -2,
            '比和': 0,
        }
        base_score += relation_adjust.get(element_relation, 0)
        
        # 4. 动爻调整（有动爻表示变化，增加不确定性）
        if has_moving:
            # 随机微调，模拟动爻的影响
            base_score += self.random.choice([-1, 0, 1])
        
        # 5. 限制范围
        return max(-2, min(2, base_score))
    
    def generate_case(self, case_id: int) -> dict:
        """生成单个案例"""
        # 随机时间
        dt = self.generate_random_time()
        
        # 随机问事类型
        question_type = self.random.choice(self.QUESTION_TYPES)
        
        # 生成卦象
        hexagram = self.engine.generate_hexagram_from_time(
            dt.year, dt.month, dt.day, dt.hour
        )
        
        # 获取变卦
        changed = hexagram.get_changed_hexagram()
        
        # 分析卦象
        analysis = self.engine.analyze_hexagram(hexagram, question_type)
        
        # 计算吉凶（基于理论）
        fortune_score = self.calculate_fortune_score(
            hexagram.name,
            question_type,
            analysis['本卦']['五行关系'],
            len(hexagram.moving_lines) > 0
        )
        fortune_level = self.FORTUNE_LEVELS[fortune_score + 2]  # 映射到0-4索引
        
        # 生成时间窗口（基于动爻数量和位置）
        num_moving = len(hexagram.moving_lines)
        if num_moving == 0:
            time_idx = 2  # 无动爻，中期
        elif num_moving == 1:
            # 根据动爻位置判断
            pos = hexagram.moving_lines[0]
            if pos <= 2:
                time_idx = 0  # 近期
            elif pos <= 4:
                time_idx = 1  # 短期
            else:
                time_idx = 2  # 中期
        else:
            time_idx = self.random.randint(1, 3)
        
        time_windows = [
            '近期（3日内）', '短期（一周内）', '中期（一月内）',
            '长期（三月内）', '远期（半年内）'
        ]
        time_window = time_windows[time_idx]
        
        return {
            'case_id': case_id,
            'datetime': dt.isoformat(),
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'question_type': question_type,
            'hexagram': {
                'name': hexagram.name,
                'upper_trigram': hexagram.upper_trigram,
                'lower_trigram': hexagram.lower_trigram,
                'lines': hexagram.lines,
                'moving_lines': hexagram.moving_lines,
            },
            'changed_hexagram': {
                'name': changed.name,
                'upper_trigram': changed.upper_trigram,
                'lower_trigram': changed.lower_trigram,
                'lines': changed.lines,
            },
            'analysis': {
                'shi_position': analysis['世应']['世爻'],
                'ying_position': analysis['世应']['应爻'],
                'deity_type': analysis['用神']['用神类型'],
                'deity_element': analysis['用神']['用神五行'],
                'element_relation': analysis['本卦']['五行关系'],
            },
            'expert_interpretation': {
                'fortune_level': fortune_level,
                'fortune_comment': f'基于{hexagram.name}卦象分析',
                'time_window': time_window,
            },
        }
    
    def generate_cases(self, num_cases: int = 1000, output_path: str = None) -> list:
        """生成多个案例"""
        cases = []
        for i in range(1, num_cases + 1):
            case = self.generate_case(i)
            cases.append(case)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cases, f, ensure_ascii=False, indent=2)
            print(f"已生成 {num_cases} 个案例，保存至: {output_path}")
        
        return cases


def main():
    """主函数"""
    generator = TheoryBasedCaseGenerator(seed=42)
    
    # 生成训练数据
    output_path = os.path.join(os.path.dirname(__file__), 'theory_cases.json')
    cases = generator.generate_cases(2000, output_path)
    
    # 统计分布
    from collections import Counter
    
    print("\n=== 生成案例统计 ===")
    print(f"总案例数: {len(cases)}")
    
    print("\n吉凶分布:")
    fortune_dist = Counter(c['expert_interpretation']['fortune_level'] for c in cases)
    for level in ['大吉', '吉', '平', '凶', '大凶']:
        count = fortune_dist.get(level, 0)
        print(f"  {level}: {count} ({count/len(cases)*100:.1f}%)")
    
    print("\n问事类型分布:")
    type_dist = Counter(c['question_type'] for c in cases)
    for qtype in ['财运', '事业', '婚姻', '健康', '诉讼']:
        count = type_dist.get(qtype, 0)
        print(f"  {qtype}: {count} ({count/len(cases)*100:.1f}%)")
    
    print("\n时间窗口分布:")
    time_dist = Counter(c['expert_interpretation']['time_window'] for c in cases)
    for window in ['近期（3日内）', '短期（一周内）', '中期（一月内）', '长期（三月内）', '远期（半年内）']:
        count = time_dist.get(window, 0)
        print(f"  {window}: {count} ({count/len(cases)*100:.1f}%)")


if __name__ == '__main__':
    main()
