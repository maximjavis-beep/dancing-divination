# 模拟数据生成器
"""
生成六爻预测模拟案例数据，用于训练ML模型
"""

import json
import random
import datetime
from typing import List, Dict
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import LiuYaoEngine, TRIGRAMS

class CaseGenerator:
    """案例生成器"""
    
    QUESTION_TYPES = ['财运', '事业', '爱情', '健康', '诉讼']
    
    # 吉凶评语库
    FORTUNE_COMMENTS = {
        '大吉': ['天时地利人和，诸事顺遂', '吉星高照，心想事成', '运势亨通，百无禁忌'],
        '吉': ['运势平稳，小有收获', '努力有成，渐入佳境', '贵人相助，逢凶化吉'],
        '平': ['吉凶参半，谨慎行事', '平稳发展，静待时机', '波澜不惊，守成为上'],
        '凶': ['运势低迷，诸事不顺', '阻碍重重，宜守不宜攻', '小人当道，谨防受骗'],
        '大凶': ['运势极差，百事不利', '灾祸临头，宜静不宜动', '时运不济，明哲保身'],
    }
    
    # 时间窗口评语
    TIME_COMMENTS = [
        '近期（3日内）',
        '短期（一周内）',
        '中期（一月内）',
        '长期（三月内）',
        '远期（半年内）',
    ]
    
    def __init__(self):
        self.engine = LiuYaoEngine()
        self.random = random.Random()
    
    def generate_random_time(self, start_year: int = 2020, end_year: int = 2024) -> datetime.datetime:
        """生成随机时间"""
        start = datetime.datetime(start_year, 1, 1)
        end = datetime.datetime(end_year, 12, 31)
        delta = end - start
        random_days = self.random.randint(0, delta.days)
        random_hours = self.random.randint(0, 23)
        return start + datetime.timedelta(days=random_days, hours=random_hours)
    
    def generate_case(self, case_id: int) -> Dict:
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
        
        # 生成模拟的"专家解读"
        fortune_level = self._calculate_fortune_level(analysis, question_type)
        fortune_comment = self.random.choice(self.FORTUNE_COMMENTS[fortune_level])
        time_window = self.random.choice(self.TIME_COMMENTS)
        
        # 应验结果（模拟历史数据）
        verification = self._generate_verification(fortune_level)
        
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
                'fortune_comment': fortune_comment,
                'time_window': time_window,
                'advice': self._generate_advice(fortune_level, question_type),
            },
            'verification': verification,
        }
    
    def _calculate_fortune_level(self, analysis: Dict, question_type: str) -> str:
        """
        根据卦象分析计算吉凶等级
        简化算法：根据五行关系判断
        """
        element_relation = analysis['本卦']['五行关系']
        
        # 基础概率
        weights = {
            '大吉': 10,
            '吉': 25,
            '平': 30,
            '凶': 25,
            '大凶': 10,
        }
        
        # 根据五行关系调整
        if element_relation == '生':
            weights['大吉'] += 15
            weights['吉'] += 10
            weights['凶'] -= 10
            weights['大凶'] -= 15
        elif element_relation == '被生':
            weights['大吉'] += 10
            weights['吉'] += 5
        elif element_relation == '克':
            weights['凶'] += 10
            weights['大凶'] += 5
            weights['大吉'] -= 10
        elif element_relation == '被克':
            weights['凶'] += 15
            weights['大凶'] += 10
            weights['大吉'] -= 15
            weights['吉'] -= 10
        
        # 根据动爻数量调整
        moving_count = len(analysis.get('动爻', []))
        if moving_count > 1:
            weights['平'] += 5
        
        # 归一化并随机选择
        total = sum(weights.values())
        r = self.random.uniform(0, total)
        cumulative = 0
        for level, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return level
        
        return '平'
    
    def _generate_advice(self, fortune_level: str, question_type: str) -> str:
        """生成建议"""
        advice_map = {
            '财运': {
                '大吉': '大胆投资，把握良机',
                '吉': '稳健理财，小有进账',
                '平': '守财为上，不宜冒险',
                '凶': '紧缩开支，避免损失',
                '大凶': '谨防破财，保守经营',
            },
            '事业': {
                '大吉': '积极进取，大展宏图',
                '吉': '稳步发展，争取晋升',
                '平': '坚守岗位，等待时机',
                '凶': '低调行事，避免冲突',
                '大凶': '明哲保身，不宜变动',
            },
            '爱情': {
                '大吉': '良缘天定，可喜可贺',
                '吉': '感情和睦，渐入佳境',
                '平': '相互包容，平淡是真',
                '凶': '沟通不畅，需要耐心',
                '大凶': '感情危机，慎重处理',
            },
            '健康': {
                '大吉': '身体康健，精力充沛',
                '吉': '注意保养，预防为主',
                '平': '劳逸结合，适度锻炼',
                '凶': '身体不适，及时就医',
                '大凶': '重病缠身，精心调养',
            },
            '诉讼': {
                '大吉': '官司必胜，正义得伸',
                '吉': '有理有据，胜算较大',
                '平': '和解为上，避免纠缠',
                '凶': '证据不足，可能败诉',
                '大凶': '官司不利，尽早和解',
            },
        }
        return advice_map.get(question_type, {}).get(fortune_level, '谨慎行事')
    
    def _generate_verification(self, fortune_level: str) -> Dict:
        """生成应验结果（模拟历史验证数据）"""
        # 应验概率根据吉凶等级调整
        verification_prob = {
            '大吉': 0.9,
            '吉': 0.75,
            '平': 0.5,
            '凶': 0.25,
            '大凶': 0.1,
        }
        
        prob = verification_prob.get(fortune_level, 0.5)
        verified = self.random.random() < prob
        
        return {
            'verified': verified,
            'accuracy': prob,
            'actual_outcome': '符合预测' if verified else '与预测有偏差',
        }
    
    def generate_cases(self, count: int = 200) -> List[Dict]:
        """生成指定数量的案例"""
        cases = []
        for i in range(count):
            case = self.generate_case(i + 1)
            cases.append(case)
        return cases

def main():
    """主函数"""
    print("开始生成模拟案例数据...")
    
    generator = CaseGenerator()
    cases = generator.generate_cases(500)
    
    # 保存为JSON
    output_path = os.path.join(os.path.dirname(__file__), 'cases.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    
    print(f"已生成 {len(cases)} 个案例")
    print(f"保存至: {output_path}")
    
    # 统计信息
    fortune_counts = {}
    type_counts = {}
    for case in cases:
        fortune = case['expert_interpretation']['fortune_level']
        qtype = case['question_type']
        fortune_counts[fortune] = fortune_counts.get(fortune, 0) + 1
        type_counts[qtype] = type_counts.get(qtype, 0) + 1
    
    print("\n吉凶分布:")
    for level in ['大吉', '吉', '平', '凶', '大凶']:
        count = fortune_counts.get(level, 0)
        print(f"  {level}: {count} ({count/len(cases)*100:.1f}%)")
    
    print("\n问事类型分布:")
    for qtype in generator.QUESTION_TYPES:
        count = type_counts.get(qtype, 0)
        print(f"  {qtype}: {count} ({count/len(cases)*100:.1f}%)")

if __name__ == '__main__':
    main()
