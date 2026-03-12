# 六爻核心引擎
"""
六爻预测核心算法
包含：时间起卦、卦象计算、五行生克、用神定位、世应定位
"""

import datetime
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

# 八卦定义
TRIGRAMS = {
    '乾': {'symbol': '☰', 'lines': [1, 1, 1], 'element': '金', 'number': 1},
    '兑': {'symbol': '☱', 'lines': [0, 1, 1], 'element': '金', 'number': 2},
    '离': {'symbol': '☲', 'lines': [1, 0, 1], 'element': '火', 'number': 3},
    '震': {'symbol': '☳', 'lines': [0, 0, 1], 'element': '木', 'number': 4},
    '巽': {'symbol': '☴', 'lines': [1, 1, 0], 'element': '木', 'number': 5},
    '坎': {'symbol': '☵', 'lines': [0, 1, 0], 'element': '水', 'number': 6},
    '艮': {'symbol': '☶', 'lines': [1, 0, 0], 'element': '土', 'number': 7},
    '坤': {'symbol': '☷', 'lines': [0, 0, 0], 'element': '土', 'number': 8},
}

# 六冲卦定义（上下卦相同的纯卦）
LIUCHONG_HEXAGRAMS = {
    '乾为天', '震为雷', '坎为水', '艮为山',
    '坤为地', '巽为风', '离为火', '兑为泽'
}

# 六合卦定义（上下卦相反而合）
LIUHE_HEXAGRAMS = {
    '天地否', '地天泰', '水泽节', '泽水困',
    '山火贲', '火山旅', '雷地豫', '地雷复',
    '风泽中孚', '泽风大过', '水火既济', '火水未济',
    '山雷颐', '雷山小过', '水山蹇', '山水蒙',
    '地水师', '水地比', '地泽临', '泽地萃',
    '地山谦', '山天大畜', '天泽履', '泽天夬',
    '天火同人', '火天大有', '天雷无妄', '雷天大壮',
    '天风姤', '风天小畜', '天水讼', '水天需',
    '风地观', '地风升', '风雷益', '雷风恒',
    '风火家人', '火风鼎', '水风井', '风水涣',
    '水雷屯', '雷水解', '山风蛊', '风山渐',
    '山泽损', '泽山咸', '火雷噬嗑', '雷火丰',
    '火泽睽', '泽火革', '地火明夷', '火地晋'
}

# 游魂卦（八宫第七卦）
YOUHUN_HEXAGRAMS = {
    '火地晋', '雷山小过', '天水讼', '泽风大过',
    '山雷颐', '地火明夷', '风泽中孚', '水天需'
}

# 归魂卦（八宫第八卦）
GUIHUN_HEXAGRAMS = {
    '火天大有', '雷泽归妹', '天火同人', '泽雷随',
    '山风蛊', '地水师', '风山渐', '水地比'
}

# 六十四卦（上卦+下卦组合）
def get_hexagram_name(upper: str, lower: str) -> str:
    """根据上下卦获取六十四卦名称"""
    hexagrams = {
        ('乾', '乾'): '乾为天', ('乾', '兑'): '天泽履', ('乾', '离'): '天火同人',
        ('乾', '震'): '天雷无妄', ('乾', '巽'): '天风姤', ('乾', '坎'): '天水讼',
        ('乾', '艮'): '天山遁', ('乾', '坤'): '天地否',
        ('兑', '乾'): '泽天夬', ('兑', '兑'): '兑为泽', ('兑', '离'): '泽火革',
        ('兑', '震'): '泽雷随', ('兑', '巽'): '泽风大过', ('兑', '坎'): '泽水困',
        ('兑', '艮'): '泽山咸', ('兑', '坤'): '泽地萃',
        ('离', '乾'): '火天大有', ('离', '兑'): '火泽睽', ('离', '离'): '离为火',
        ('离', '震'): '火雷噬嗑', ('离', '巽'): '火风鼎', ('离', '坎'): '火水未济',
        ('离', '艮'): '火山旅', ('离', '坤'): '火地晋',
        ('震', '乾'): '雷天大壮', ('震', '兑'): '雷泽归妹', ('震', '离'): '雷火丰',
        ('震', '震'): '震为雷', ('震', '巽'): '雷风恒', ('震', '坎'): '雷水解',
        ('震', '艮'): '雷山小过', ('震', '坤'): '雷地豫',
        ('巽', '乾'): '风天小畜', ('巽', '兑'): '风泽中孚', ('巽', '离'): '风火家人',
        ('巽', '震'): '风雷益', ('巽', '巽'): '巽为风', ('巽', '坎'): '风水涣',
        ('巽', '艮'): '风山渐', ('巽', '坤'): '风地观',
        ('坎', '乾'): '水天需', ('坎', '兑'): '水泽节', ('坎', '离'): '水火既济',
        ('坎', '震'): '水雷屯', ('坎', '巽'): '水风井', ('坎', '坎'): '坎为水',
        ('坎', '艮'): '水山蹇', ('坎', '坤'): '水地比',
        ('艮', '乾'): '山天大畜', ('艮', '兑'): '山泽损', ('艮', '离'): '山火贲',
        ('艮', '震'): '山雷颐', ('艮', '巽'): '山风蛊', ('艮', '坎'): '山水蒙',
        ('艮', '艮'): '艮为山', ('艮', '坤'): '山地剥',
        ('坤', '乾'): '地天泰', ('坤', '兑'): '地泽临', ('坤', '离'): '地火明夷',
        ('坤', '震'): '地雷复', ('坤', '巽'): '地风升', ('坤', '坎'): '地水师',
        ('坤', '艮'): '地山谦', ('坤', '坤'): '坤为地',
    }
    return hexagrams.get((upper, lower), f'{upper}上{lower}下')

# 五行生克关系
ELEMENT_CYCLE = {
    '生': {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'},
    '克': {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'},
}

# 问事类型与用神对应
QUESTION_TYPE_DEITY = {
    '财运': {'用神': '妻财', '五行': '金'},
    '事业': {'用神': '官鬼', '五行': '火'},
    '婚姻': {'用神': '妻财', '五行': '金'},
    '健康': {'用神': '父母', '五行': '土'},
    '诉讼': {'用神': '官鬼', '五行': '火'},
}

@dataclass
class Hexagram:
    """卦象数据结构"""
    upper_trigram: str  # 上卦
    lower_trigram: str  # 下卦
    lines: List[int]    # 六爻（从下到上）
    moving_lines: List[int]  # 动爻位置（1-6）

    @property
    def name(self) -> str:
        return get_hexagram_name(self.upper_trigram, self.lower_trigram)

    def is_liuchong(self) -> bool:
        """判断是否为六冲卦（上下卦相同的纯卦）"""
        return self.name in LIUCHONG_HEXAGRAMS

    def is_liuhe(self) -> bool:
        """判断是否为六合卦（上下卦相反而合）"""
        return self.name in LIUHE_HEXAGRAMS

    def is_youhun(self) -> bool:
        """判断是否为游魂卦"""
        return self.name in YOUHUN_HEXAGRAMS

    def is_guihun(self) -> bool:
        """判断是否为归魂卦"""
        return self.name in GUIHUN_HEXAGRAMS

    def get_special_pattern(self) -> str:
        """
        返回特殊格局
        六冲 > 六合 > 游魂 > 归魂 > 普通
        """
        if self.is_liuchong():
            return '六冲'
        elif self.is_liuhe():
            return '六合'
        elif self.is_youhun():
            return '游魂'
        elif self.is_guihun():
            return '归魂'
        else:
            return '普通'

    def get_changed_hexagram(self) -> 'Hexagram':
        """获取变卦"""
        changed_lines = self.lines.copy()
        for pos in self.moving_lines:
            changed_lines[pos - 1] = 1 - changed_lines[pos - 1]
        
        # 从六爻重新计算上下卦
        lower = self._get_trigram_from_lines(changed_lines[:3])
        upper = self._get_trigram_from_lines(changed_lines[3:])
        
        return Hexagram(upper, lower, changed_lines, [])
    
    @staticmethod
    def _get_trigram_from_lines(lines: List[int]) -> str:
        """根据三爻获取卦名"""
        for name, info in TRIGRAMS.items():
            if info['lines'] == lines:
                return name
        return '乾'

class LiuYaoEngine:
    """六爻预测引擎"""
    
    def __init__(self):
        self.trigrams = TRIGRAMS
        self.element_cycle = ELEMENT_CYCLE
        self.question_deity = QUESTION_TYPE_DEITY
    
    def generate_hexagram_from_time(self, year: int, month: int, day: int, hour: int) -> Hexagram:
        """
        根据时间起卦（梅花易数方法）
        上卦 = (年 + 月 + 日) % 8
        下卦 = (年 + 月 + 日 + 时) % 8
        动爻 = (年 + 月 + 日 + 时) % 6
        """
        # 农历年份简化计算
        lunar_year = year - 1984  # 以甲子年为基准
        if lunar_year < 0:
            lunar_year += 60
        
        # 计算上卦
        upper_num = (lunar_year + month + day) % 8
        if upper_num == 0:
            upper_num = 8
        upper_trigram = self._get_trigram_by_number(upper_num)
        
        # 计算下卦
        lower_num = (lunar_year + month + day + hour) % 8
        if lower_num == 0:
            lower_num = 8
        lower_trigram = self._get_trigram_by_number(lower_num)
        
        # 计算动爻
        moving_num = (lunar_year + month + day + hour) % 6
        if moving_num == 0:
            moving_num = 6
        
        # 构建六爻
        lower_lines = self.trigrams[lower_trigram]['lines']
        upper_lines = self.trigrams[upper_trigram]['lines']
        lines = lower_lines + upper_lines
        
        return Hexagram(upper_trigram, lower_trigram, lines, [moving_num])
    
    def _get_trigram_by_number(self, num: int) -> str:
        """根据数字获取卦名"""
        for name, info in self.trigrams.items():
            if info['number'] == num:
                return name
        return '乾'
    
    def get_shi_ying_position(self, hexagram: Hexagram) -> Tuple[int, int]:
        """
        确定世应位置
        根据八宫卦序确定世爻位置
        """
        # 简化规则：根据上下卦相同与否判断
        if hexagram.upper_trigram == hexagram.lower_trigram:
            # 纯卦，世在上爻（第6爻）
            return (6, 3)
        
        # 根据卦变规则确定世爻
        upper_num = self.trigrams[hexagram.upper_trigram]['number']
        lower_num = self.trigrams[hexagram.lower_trigram]['number']
        
        diff = abs(upper_num - lower_num)
        shi = (diff % 6) + 1
        ying = ((shi + 2) % 6) + 1
        
        return (shi, ying)
    
    def get_deity(self, question_type: str, hexagram: Hexagram) -> Dict:
        """
        根据问事类型定位用神
        """
        deity_info = self.question_deity.get(question_type, {'用神': '世爻', '五行': '土'})
        
        # 确定用神所在爻位
        shi_pos, _ = self.get_shi_ying_position(hexagram)
        
        # 简化：用神通常与世爻相关
        deity_position = shi_pos
        
        # 根据五行确定用神爻
        element = deity_info['五行']
        trigram_element = self.trigrams[hexagram.upper_trigram]['element']
        
        # 计算用神五行与卦五行的关系
        relation = self.get_element_relation(trigram_element, element)
        
        return {
            '用神类型': deity_info['用神'],
            '用神五行': element,
            '用神位置': deity_position,
            '五行关系': relation,
        }
    
    def get_element_relation(self, from_elem: str, to_elem: str) -> str:
        """
        计算五行关系
        """
        if self.element_cycle['生'][from_elem] == to_elem:
            return '生'
        elif self.element_cycle['克'][from_elem] == to_elem:
            return '克'
        elif self.element_cycle['生'][to_elem] == from_elem:
            return '被生'
        elif self.element_cycle['克'][to_elem] == from_elem:
            return '被克'
        else:
            return '比和'
    
    def analyze_hexagram(self, hexagram: Hexagram, question_type: str) -> Dict:
        """
        综合分析卦象
        """
        # 获取变卦
        changed = hexagram.get_changed_hexagram()
        
        # 世应定位
        shi, ying = self.get_shi_ying_position(hexagram)
        
        # 用神定位
        deity = self.get_deity(question_type, hexagram)
        
        # 分析动爻
        moving_analysis = []
        for pos in hexagram.moving_lines:
            line_num = pos - 1  # 转换为0-5索引（从下到上）
            if 0 <= line_num < len(hexagram.lines):
                is_yang = hexagram.lines[line_num] == 1
                moving_analysis.append({
                    '位置': pos,
                    '阴阳': '阳' if is_yang else '阴',
                    '变化': '变阴' if is_yang else '变阳',
                })
        
        # 五行生克分析
        upper_element = self.trigrams[hexagram.upper_trigram]['element']
        lower_element = self.trigrams[hexagram.lower_trigram]['element']
        element_relation = self.get_element_relation(upper_element, lower_element)
        
        return {
            '本卦': {
                '卦名': hexagram.name,
                '上卦': hexagram.upper_trigram,
                '下卦': hexagram.lower_trigram,
                '上卦五行': upper_element,
                '下卦五行': lower_element,
                '五行关系': element_relation,
            },
            '变卦': {
                '卦名': changed.name,
                '上卦': changed.upper_trigram,
                '下卦': changed.lower_trigram,
            },
            '世应': {
                '世爻': shi,
                '应爻': ying,
            },
            '用神': deity,
            '动爻': moving_analysis,
            '六爻': hexagram.lines,
        }
    
    def get_hexagram_text(self, hexagram_name: str) -> str:
        """
        获取卦辞（简化版）
        """
        texts = {
            '乾为天': '元亨利贞。',
            '坤为地': '元亨，利牝马之贞。',
            '水雷屯': '元亨利贞，勿用有攸往，利建侯。',
            '山水蒙': '亨。匪我求童蒙，童蒙求我。',
            '水天需': '有孚，光亨，贞吉。',
            '天水讼': '有孚，窒惕，中吉，终凶。',
            '地水师': '贞，丈人吉，无咎。',
            '水地比': '吉。原筮元永贞，无咎。',
        }
        return texts.get(hexagram_name, '卦辞：亨，无咎。')

# 便捷函数
def generate_hexagram(year: int, month: int, day: int, hour: int) -> Hexagram:
    """便捷函数：根据时间起卦"""
    engine = LiuYaoEngine()
    return engine.generate_hexagram_from_time(year, month, day, hour)

def analyze(year: int, month: int, day: int, hour: int, question_type: str) -> Dict:
    """便捷函数：综合分析"""
    engine = LiuYaoEngine()
    hexagram = engine.generate_hexagram_from_time(year, month, day, hour)
    return engine.analyze_hexagram(hexagram, question_type)
