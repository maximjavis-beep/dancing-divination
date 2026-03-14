"""
八字与六爻联合分析模块
结合八字命理和六爻卦象进行综合分析
"""

from typing import Dict, List
from .engine import LiuYaoEngine, TRIGRAMS
from .bazi import BaziEngine, TIANGAN_WUXING, DIZHI_WUXING

class BaziHexagramAnalyzer:
    """八字六爻联合分析器"""
    
    def __init__(self):
        self.bazi_engine = BaziEngine()
        self.liuyao_engine = LiuYaoEngine()
    
    def analyze(self, birth_year: int, birth_month: int, birth_day: int, birth_hour: int,
                gender: str,
                divination_year: int, divination_month: int, divination_day: int, divination_hour: int,
                question_type: str) -> Dict:
        """
        综合分析八字和六爻
        
        参数：
            birth_*: 出生时间（八字）
            gender: 性别
            divination_*: 起卦时间
            question_type: 问事类型
        """
        # 计算八字
        bazi = self.bazi_engine.calculate_bazi(birth_year, birth_month, birth_day, birth_hour)
        bazi_info = self.bazi_engine.analyze_wangshuai(bazi)
        
        # 计算六爻
        hexagram = self.liuyao_engine.generate_hexagram_from_time(
            divination_year, divination_month, divination_day, divination_hour
        )
        hexagram_analysis = self.liuyao_engine.analyze_hexagram(hexagram, question_type)
        
        # 联合分析
        combined_analysis = self._combine_analysis(bazi, bazi_info, hexagram_analysis, question_type)
        
        return {
            '八字': {
                '四柱': {
                    '年柱': f"{bazi.year.gan}{bazi.year.zhi}",
                    '月柱': f"{bazi.month.gan}{bazi.month.zhi}",
                    '日柱': f"{bazi.day.gan}{bazi.day.zhi}",
                    '时柱': f"{bazi.hour.gan}{bazi.hour.zhi}",
                },
                '日干': bazi.day_gan,
                '日主五行': bazi_info['日主五行'],
                '旺衰': bazi_info['旺衰判断'],
                '十神': bazi.get_shishen_map(),
                '五行统计': bazi.get_wuxing_count(),
                '大运': self.bazi_engine.calculate_dayun(bazi, gender, birth_year)[:3],  # 只返回前3步
            },
            '六爻': {
                '本卦': hexagram_analysis['本卦'],
                '变卦': hexagram_analysis['变卦'],
                '世应': hexagram_analysis['世应'],
                '用神': hexagram_analysis['用神'],
                '动爻': hexagram_analysis['动爻'],
            },
            '联合分析': combined_analysis,
        }
    
    def _combine_analysis(self, bazi, bazi_info: Dict, hexagram_analysis: Dict, question_type: str) -> Dict:
        """联合分析八字和六爻"""
        
        day_master_wx = bazi_info['日主五行']  # 日主五行
        day_master_wangshuai = bazi_info['旺衰判断']  # 日主旺衰
        
        # 获取用神五行
        deity_info = hexagram_analysis['用神']
        deity_wx = deity_info['用神五行']
        
        # 分析八字对用神的支持
        bazi_support = self._analyze_bazi_support(bazi, deity_wx)
        
        # 分析卦象吉凶
        hexagram_fortune = self._analyze_hexagram_fortune(hexagram_analysis)
        
        # 综合评分
        combined_score = self._calculate_combined_score(
            bazi_support, hexagram_fortune, day_master_wangshuai
        )
        
        # 生成解读
        interpretation = self._generate_interpretation(
            bazi_support, hexagram_fortune, day_master_wangshuai, 
            deity_wx, question_type
        )
        
        return {
            '用神五行': deity_wx,
            '日主五行': day_master_wx,
            '日主旺衰': day_master_wangshuai,
            '八字对用神支持度': bazi_support,
            '卦象吉凶度': hexagram_fortune,
            '综合评分': combined_score,
            '综合判断': interpretation['judgment'],
            '详细解读': interpretation['detail'],
            '建议': interpretation['advice'],
        }
    
    def _analyze_bazi_support(self, bazi, deity_wx: str) -> Dict:
        """分析八字对用神的支持程度"""
        
        # 五行生克关系
        wuxing_cycle = {
            '生': {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'},
            '克': {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'},
        }
        
        support_score = 0
        details = []
        
        pillars = [
            ('年柱', bazi.year), ('月柱', bazi.month), 
            ('日柱', bazi.day), ('时柱', bazi.hour)
        ]
        
        for name, pillar in pillars:
            # 天干
            tg_wx = TIANGAN_WUXING[pillar.gan]
            if tg_wx == deity_wx:
                support_score += 2
                details.append(f"{name}天干{pillar.gan}({tg_wx})比和用神")
            elif wuxing_cycle['生'].get(tg_wx) == deity_wx:
                support_score += 1.5
                details.append(f"{name}天干{pillar.gan}({tg_wx})生助用神")
            elif wuxing_cycle['克'].get(tg_wx) == deity_wx:
                support_score -= 1
                details.append(f"{name}天干{pillar.gan}({tg_wx})克制用神")
            
            # 地支
            dz_wx = DIZHI_WUXING[pillar.zhi]
            if dz_wx == deity_wx:
                support_score += 1
                details.append(f"{name}地支{pillar.zhi}({dz_wx})比和用神")
            elif wuxing_cycle['生'].get(dz_wx) == deity_wx:
                support_score += 0.5
                details.append(f"{name}地支{pillar.zhi}({dz_wx})生助用神")
            elif wuxing_cycle['克'].get(dz_wx) == deity_wx:
                support_score -= 0.5
                details.append(f"{name}地支{pillar.zhi}({dz_wx})克制用神")
        
        # 判断支持度等级
        if support_score >= 4:
            level = '强'
        elif support_score >= 1:
            level = '中'
        else:
            level = '弱'
        
        return {
            '分数': support_score,
            '等级': level,
            '详情': details,
        }
    
    def _analyze_hexagram_fortune(self, hexagram_analysis: Dict) -> Dict:
        """分析卦象吉凶"""
        
        score = 50  # 基础分50
        details = []
        
        # 1. 用神分析
        deity = hexagram_analysis['用神']
        if deity['五行关系'] == '被生':
            score += 15
            details.append("用神受生，吉")
        elif deity['五行关系'] == '生':
            score += 10
            details.append("用神得助，平吉")
        elif deity['五行关系'] == '比和':
            score += 5
            details.append("用神比和，平稳")
        elif deity['五行关系'] == '克':
            score -= 10
            details.append("用神克制他物，耗力")
        elif deity['五行关系'] == '被克':
            score -= 15
            details.append("用神受克，凶")
        
        # 2. 动爻分析
        moving_lines = hexagram_analysis['动爻']
        if moving_lines:
            for line in moving_lines:
                if line['阴阳'] == '阳':
                    score += 3
                    details.append(f"第{line['位置']}爻阳动，有变")
                else:
                    score += 2
                    details.append(f"第{line['位置']}爻阴动，渐变")
        
        # 3. 世应分析
        shi = hexagram_analysis['世应']['世爻']
        ying = hexagram_analysis['世应']['应爻']
        if abs(shi - ying) == 3:
            score += 5
            details.append("世应相应，人和")
        
        # 判断等级
        if score >= 70:
            level = '吉'
        elif score >= 50:
            level = '平'
        else:
            level = '凶'
        
        return {
            '分数': score,
            '等级': level,
            '详情': details,
        }
    
    def _calculate_combined_score(self, bazi_support: Dict, hexagram_fortune: Dict, 
                                   day_master_wangshuai: str) -> Dict:
        """计算综合评分"""
        
        # 基础分来自卦象
        base_score = hexagram_fortune['分数']
        
        # 八字支持调整
        bazi_adjustment = {
            '强': 10, '中': 0, '弱': -5
        }.get(bazi_support['等级'], 0)
        
        # 日主旺衰调整（身强能担财官，身弱喜印比）
        wangshuai_adjustment = {
            '旺': 5, '中和': 0, '弱': -3
        }.get(day_master_wangshuai, 0)
        
        final_score = base_score + bazi_adjustment + wangshuai_adjustment
        
        # 限制在0-100
        final_score = max(0, min(100, final_score))
        
        # 综合等级
        if final_score >= 75:
            level = '大吉'
        elif final_score >= 60:
            level = '吉'
        elif final_score >= 45:
            level = '平'
        elif final_score >= 30:
            level = '凶'
        else:
            level = '大凶'
        
        return {
            '总分': final_score,
            '等级': level,
            '卦象基础分': base_score,
            '八字支持调整': bazi_adjustment,
            '日主旺衰调整': wangshuai_adjustment,
        }
    
    def _generate_interpretation(self, bazi_support: Dict, hexagram_fortune: Dict,
                                  day_master_wangshuai: str, deity_wx: str,
                                  question_type: str) -> Dict:
        """生成综合解读"""
        
        combined_score = self._calculate_combined_score(
            bazi_support, hexagram_fortune, day_master_wangshuai
        )
        
        level = combined_score['等级']
        
        # 根据等级生成判断
        judgments = {
            '大吉': '天时地利人和，此事可成',
            '吉': '时机有利，努力可得',
            '平': '吉凶参半，谨慎行事',
            '凶': '时机不利，宜守不宜攻',
            '大凶': '诸多阻碍，暂避锋芒',
        }
        
        # 详细解读
        detail_parts = []
        
        # 八字部分
        if bazi_support['等级'] == '强':
            detail_parts.append(f"八字对{deity_wx}用神支持力度强，个人运势有助此事")
        elif bazi_support['等级'] == '中':
            detail_parts.append(f"八字对{deity_wx}用神支持力度一般")
        else:
            detail_parts.append(f"八字对{deity_wx}用神支持力度较弱，个人运势对此事的助力有限")
        
        # 日主部分
        if day_master_wangshuai == '旺':
            detail_parts.append("日主旺相，有能力承担此事的压力")
        elif day_master_wangshuai == '中和':
            detail_parts.append("日主中和，顺势而为即可")
        else:
            detail_parts.append("日主偏弱，需要借助外力或等待时机")
        
        # 卦象部分
        detail_parts.append(f"卦象显示{hexagram_fortune['等级']}，{'；'.join(hexagram_fortune['详情'][:2])}")
        
        # 建议
        advice_map = {
            '大吉': ['把握时机，积极推进', '可大胆行动，成功率高'],
            '吉': ['顺势而为，稳步前行', '保持积极心态，努力可得'],
            '平': ['谨慎评估，多方考虑', '不宜冒进，稳扎稳打'],
            '凶': ['暂缓行动，等待时机', '注意风险，保守为上'],
            '大凶': ['暂时放弃，另寻他路', '避免投入，保存实力'],
        }
        
        return {
            'judgment': judgments.get(level, '吉凶难料，需进一步观察'),
            'detail': '；'.join(detail_parts),
            'advice': advice_map.get(level, ['保持观望', '谨慎决策']),
        }

# 便捷函数
def analyze_bazi_hexagram(birth_time: Dict, gender: str, 
                          divination_time: Dict, question_type: str) -> Dict:
    """
    便捷函数：综合分析八字和六爻
    
    参数：
        birth_time: {'year': 1990, 'month': 5, 'day': 15, 'hour': 10}
        gender: '男' 或 '女'
        divination_time: {'year': 2024, 'month': 3, 'day': 12, 'hour': 14}
        question_type: '财运'/'事业'/'爱情'/'健康'/'诉讼'
    """
    analyzer = BaziHexagramAnalyzer()
    return analyzer.analyze(
        birth_time['year'], birth_time['month'], birth_time['day'], birth_time['hour'],
        gender,
        divination_time['year'], divination_time['month'], divination_time['day'], divination_time['hour'],
        question_type
    )
