"""
八字命理计算引擎
包含：四柱排盘、十神计算、旺衰判断、大运推算
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

# 天干
TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

# 地支
DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 天干五行
TIANGAN_WUXING = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水',
}

# 地支五行
DIZHI_WUXING = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木',
    '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水',
}

# 地支藏干
DIZHI_CANGGAN = {
    '子': ['癸'],
    '丑': ['己', '癸', '辛'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'],
    '未': ['己', '丁', '乙'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['戊', '辛', '丁'],
    '亥': ['壬', '甲'],
}

# 十神定义（以日干为"我"）
def get_shishen(day_gan: str, target_gan: str) -> str:
    """
    计算十神
    日干为"我"，看target_gan相对于日干是什么十神
    """
    if day_gan == target_gan:
        return '比肩'
    
    # 五行关系
    day_wx = TIANGAN_WUXING[day_gan]
    target_wx = TIANGAN_WUXING[target_gan]
    
    # 阴阳
    day_yin = TIANGAN.index(day_gan) % 2 == 1  # 乙丁己辛癸为阴
    target_yin = TIANGAN.index(target_gan) % 2 == 1
    same_yin_yang = day_yin == target_yin
    
    # 生克关系
    if day_wx == '木':
        if target_wx == '火': return '食神' if same_yin_yang else '伤官'
        if target_wx == '土': return '偏财' if same_yin_yang else '正财'
        if target_wx == '金': return '七杀' if same_yin_yang else '正官'
        if target_wx == '水': return '偏印' if same_yin_yang else '正印'
    elif day_wx == '火':
        if target_wx == '土': return '食神' if same_yin_yang else '伤官'
        if target_wx == '金': return '偏财' if same_yin_yang else '正财'
        if target_wx == '水': return '七杀' if same_yin_yang else '正官'
        if target_wx == '木': return '偏印' if same_yin_yang else '正印'
    elif day_wx == '土':
        if target_wx == '金': return '食神' if same_yin_yang else '伤官'
        if target_wx == '水': return '偏财' if same_yin_yang else '正财'
        if target_wx == '木': return '七杀' if same_yin_yang else '正官'
        if target_wx == '火': return '偏印' if same_yin_yang else '正印'
    elif day_wx == '金':
        if target_wx == '水': return '食神' if same_yin_yang else '伤官'
        if target_wx == '木': return '偏财' if same_yin_yang else '正财'
        if target_wx == '火': return '七杀' if same_yin_yang else '正官'
        if target_wx == '土': return '偏印' if same_yin_yang else '正印'
    elif day_wx == '水':
        if target_wx == '木': return '食神' if same_yin_yang else '伤官'
        if target_wx == '火': return '偏财' if same_yin_yang else '正财'
        if target_wx == '土': return '七杀' if same_yin_yang else '正官'
        if target_wx == '金': return '偏印' if same_yin_yang else '正印'
    
    return '比肩'

# 简化节气表（1900-2100年，仅包含每月的节）
# 格式：{(年, 月): 日}
JIEQI_TABLE = {}

def init_jieqi_table():
    """初始化节气表（简化版，使用近似值）"""
    # 节气大约日期（每月两个节气，这里只取"节"用于确定月柱）
    # 正月（寅月）：立春（约2月4日）
    # 二月（卯月）：惊蛰（约3月5日）
    # 三月（辰月）：清明（约4月5日）
    # 四月（巳月）：立夏（约5月5日）
    # 五月（午月）：芒种（约6月5日）
    # 六月（未月）：小暑（约7月7日）
    # 七月（申月）：立秋（约8月7日）
    # 八月（酉月）：白露（约9月7日）
    # 九月（戌月）：寒露（约10月8日）
    # 十月（亥月）：立冬（约11月7日）
    # 十一月（子月）：大雪（约12月7日）
    # 十二月（丑月）：小寒（约1月5日）
    
    # JIEQI_TABLE[(年, 农历月)] = 该月节气的datetime
    # 农历月1-12对应寅月到丑月
    for year in range(1900, 2100):
        # 正月：立春，约2月4日
        JIEQI_TABLE[(year, 1)] = datetime(year, 2, 4)
        # 二月：惊蛰，约3月5日
        JIEQI_TABLE[(year, 2)] = datetime(year, 3, 5)
        # 三月：清明，约4月5日
        JIEQI_TABLE[(year, 3)] = datetime(year, 4, 5)
        # 四月：立夏，约5月5日
        JIEQI_TABLE[(year, 4)] = datetime(year, 5, 5)
        # 五月：芒种，约6月5日
        JIEQI_TABLE[(year, 5)] = datetime(year, 6, 5)
        # 六月：小暑，约7月7日
        JIEQI_TABLE[(year, 6)] = datetime(year, 7, 7)
        # 七月：立秋，约8月7日
        JIEQI_TABLE[(year, 7)] = datetime(year, 8, 7)
        # 八月：白露，约9月7日
        JIEQI_TABLE[(year, 8)] = datetime(year, 9, 7)
        # 九月：寒露，约10月8日
        JIEQI_TABLE[(year, 9)] = datetime(year, 10, 8)
        # 十月：立冬，约11月7日
        JIEQI_TABLE[(year, 10)] = datetime(year, 11, 7)
        # 十一月：大雪，约12月7日
        JIEQI_TABLE[(year, 11)] = datetime(year, 12, 7)
        # 十二月：小寒，约1月5日（下一年）
        JIEQI_TABLE[(year, 12)] = datetime(year + 1, 1, 5)

init_jieqi_table()

@dataclass
class BaziPillar:
    """柱（年柱/月柱/日柱/时柱）"""
    gan: str  # 天干
    zhi: str  # 地支
    
    @property
    def wuxing(self) -> Dict[str, str]:
        return {
            '天干五行': TIANGAN_WUXING[self.gan],
            '地支五行': DIZHI_WUXING[self.zhi],
        }
    
    @property
    def canggan(self) -> List[str]:
        """地支藏干"""
        return DIZHI_CANGGAN[self.zhi]

@dataclass
class Bazi:
    """八字"""
    year: BaziPillar   # 年柱
    month: BaziPillar  # 月柱
    day: BaziPillar    # 日柱
    hour: BaziPillar   # 时柱
    
    @property
    def day_gan(self) -> str:
        """日干"""
        return self.day.gan
    
    def get_shishen_map(self) -> Dict[str, List[str]]:
        """
        获取所有十神映射
        返回：{十神名称: [天干列表]}
        """
        result = {
            '比肩': [], '劫财': [],
            '食神': [], '伤官': [],
            '偏财': [], '正财': [],
            '七杀': [], '正官': [],
            '偏印': [], '正印': [],
        }
        
        pillars = [self.year, self.month, self.day, self.hour]
        for pillar in pillars:
            # 天干十神
            tg_shishen = get_shishen(self.day_gan, pillar.gan)
            result[tg_shishen].append(pillar.gan)
            
            # 地支藏干十神
            for cg in pillar.canggan:
                cg_shishen = get_shishen(self.day_gan, cg)
                result[cg_shishen].append(f"{pillar.zhi}({cg})")
        
        return result
    
    def get_wuxing_count(self) -> Dict[str, int]:
        """统计五行数量（天干+地支本气）"""
        count = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
        
        pillars = [self.year, self.month, self.day, self.hour]
        for pillar in pillars:
            count[TIANGAN_WUXING[pillar.gan]] += 1
            count[DIZHI_WUXING[pillar.zhi]] += 1
        
        return count

class BaziEngine:
    """八字计算引擎"""
    
    def __init__(self):
        self.tiangan = TIANGAN
        self.dizhi = DIZHI
    
    def calculate_bazi(self, year: int, month: int, day: int, hour: int) -> Bazi:
        """
        根据出生时间计算八字
        """
        dt = datetime(year, month, day, hour)
        
        # 计算年柱
        year_pillar = self._get_year_pillar(year, month, day)
        
        # 计算月柱（需考虑节气）
        month_pillar = self._get_month_pillar(year, month, day, year_pillar.gan)
        
        # 计算日柱（使用简化算法）
        day_pillar = self._get_day_pillar(year, month, day)
        
        # 计算时柱
        hour_pillar = self._get_hour_pillar(day_pillar.gan, hour)
        
        return Bazi(year_pillar, month_pillar, day_pillar, hour_pillar)
    
    def _get_year_pillar(self, year: int, month: int, day: int) -> BaziPillar:
        """计算年柱"""
        # 年柱以立春为界
        lichun = JIEQI_TABLE.get((year, 1), datetime(year, 2, 4))
        
        if datetime(year, month, day) < lichun:
            effective_year = year - 1
        else:
            effective_year = year
        
        # 年干 = (年 - 3) % 10
        gan_index = (effective_year - 4) % 10
        # 年支 = (年 - 3) % 12
        zhi_index = (effective_year - 4) % 12
        
        return BaziPillar(TIANGAN[gan_index], DIZHI[zhi_index])
    
    def _get_month_pillar(self, year: int, month: int, day: int, year_gan: str) -> BaziPillar:
        """计算月柱"""
        dt = datetime(year, month, day)
        
        # 确定月支（根据节气）
        # 农历月1-12对应寅卯辰巳午未申酉戌亥子丑
        lunar_month = 12  # 默认腊月
        for lm in range(1, 13):
            jie = JIEQI_TABLE.get((year, lm))
            if jie and dt < jie:
                lunar_month = lm - 1 if lm > 1 else 12
                break
        else:
            # 如果已经过了当年所有节气，则是腊月
            lunar_month = 12
        
        if lunar_month == 0:
            lunar_month = 12
        
        # 月支（正月建寅，即寅月为正月）
        # lunar_month 1-12 对应 寅卯辰巳午未申酉戌亥子丑
        zhi_map = {1: '寅', 2: '卯', 3: '辰', 4: '巳', 5: '午', 6: '未',
                   7: '申', 8: '酉', 9: '戌', 10: '亥', 11: '子', 12: '丑'}
        zhi = zhi_map[lunar_month]
        
        # 月干（根据年干推算，五虎遁）
        # 甲己之年丙作首，乙庚之岁戊为头
        # 丙辛之岁寻庚上，丁壬壬位顺行流
        # 戊癸之年何方发，甲寅之上好追求
        year_gan_idx = TIANGAN.index(year_gan)
        
        if year_gan_idx in [0, 5]:   # 甲己
            start_gan = 2  # 丙
        elif year_gan_idx in [1, 6]: # 乙庚
            start_gan = 4  # 戊
        elif year_gan_idx in [2, 7]: # 丙辛
            start_gan = 6  # 庚
        elif year_gan_idx in [3, 8]: # 丁壬
            start_gan = 8  # 壬
        else:  # 戊癸
            start_gan = 0  # 甲
        
        gan = TIANGAN[(start_gan + lunar_month - 1) % 10]
        
        return BaziPillar(gan, zhi)
    
    def _get_day_pillar(self, year: int, month: int, day: int) -> BaziPillar:
        """计算日柱（基于蔡勒公式推导）"""
        # 使用已知的基准点：2024-01-01 是 甲子日
        # 计算目标日期与基准点的天数差
        
        base_date = datetime(2024, 1, 1)  # 已知甲子日
        target_date = datetime(year, month, day)
        
        days_diff = (target_date - base_date).days
        
        # 甲子是第1个，所以 days_diff=0 时应该是甲子
        # 天干：甲=0, 乙=1, ..., 癸=9
        # 地支：子=0, 丑=1, ..., 亥=11
        gan_index = days_diff % 10
        zhi_index = days_diff % 12
        
        # 确保是正数
        if gan_index < 0:
            gan_index += 10
        if zhi_index < 0:
            zhi_index += 12
        
        return BaziPillar(TIANGAN[gan_index], DIZHI[zhi_index])
    
    def _get_hour_pillar(self, day_gan: str, hour: int) -> BaziPillar:
        """计算时柱"""
        # 时辰对应（23-1为子时，以此类推）
        if hour == 23 or hour == 0:
            zhi_idx = 0  # 子
        else:
            zhi_idx = ((hour + 1) // 2) % 12
        
        zhi = DIZHI[zhi_idx]
        
        # 时干（根据日干推算，五鼠遁）
        # 甲己还加甲，乙庚丙作初
        # 丙辛从戊起，丁壬庚子居
        # 戊癸何方发，壬子是真途
        day_gan_idx = TIANGAN.index(day_gan)
        
        if day_gan_idx in [0, 5]:   # 甲己
            start_gan = 0  # 甲
        elif day_gan_idx in [1, 6]: # 乙庚
            start_gan = 2  # 丙
        elif day_gan_idx in [2, 7]: # 丙辛
            start_gan = 4  # 戊
        elif day_gan_idx in [3, 8]: # 丁壬
            start_gan = 6  # 庚
        else:  # 戊癸
            start_gan = 8  # 壬
        
        gan = TIANGAN[(start_gan + zhi_idx) % 10]
        
        return BaziPillar(gan, zhi)
    
    def calculate_dayun(self, bazi: Bazi, gender: str, birth_year: int) -> List[Dict]:
        """
        计算大运
        gender: '男' 或 '女'
        """
        # 确定顺逆（根据年干阴阳和性别）
        year_gan_yin = TIANGAN.index(bazi.year.gan) % 2 == 1  # 乙丁己辛癸为阴
        is_forward = (year_gan_yin and gender == '女') or (not year_gan_yin and gender == '男')
        
        # 起运年龄（简化计算，按3天=1岁）
        # 实际应该计算到下一个/上一个节气的天数
        start_age = 3  # 简化，默认3岁起运
        
        dayun = []
        month_zhi_idx = DIZHI.index(bazi.month.zhi)
        month_gan_idx = TIANGAN.index(bazi.month.gan)
        
        for i in range(8):  # 计算8步大运
            if is_forward:
                zhi_idx = (month_zhi_idx + i + 1) % 12
                gan_idx = (month_gan_idx + i + 1) % 10
            else:
                zhi_idx = (month_zhi_idx - i - 1) % 12
                gan_idx = (month_gan_idx - i - 1) % 10
            
            age = start_age + i * 10
            dayun.append({
                'ganzhi': TIANGAN[gan_idx] + DIZHI[zhi_idx],
                'start_age': age,
                'end_age': age + 9,
            })
        
        return dayun
    
    def analyze_wangshuai(self, bazi: Bazi) -> Dict:
        """
        简单分析日主旺衰
        """
        day_gan = bazi.day_gan
        day_wx = TIANGAN_WUXING[day_gan]
        
        # 统计生助日主的五行
        support_count = 0
        restrain_count = 0
        
        wuxing_cycle = {
            '生': {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'},
            '克': {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'},
        }
        
        pillars = [bazi.year, bazi.month, bazi.day, bazi.hour]
        for pillar in pillars:
            # 天干
            tg_wx = TIANGAN_WUXING[pillar.gan]
            if tg_wx == day_wx:
                support_count += 1
            elif wuxing_cycle['生'].get(tg_wx) == day_wx:
                support_count += 1
            elif wuxing_cycle['克'].get(tg_wx) == day_wx:
                restrain_count += 1
            
            # 地支本气
            dz_wx = DIZHI_WUXING[pillar.zhi]
            if dz_wx == day_wx:
                support_count += 0.5
            elif wuxing_cycle['生'].get(dz_wx) == day_wx:
                support_count += 0.5
        
        # 简单判断
        if support_count >= 3:
            wangshuai = '旺'
        elif support_count >= 2:
            wangshuai = '中和'
        else:
            wangshuai = '弱'
        
        return {
            '日主': day_gan,
            '日主五行': day_wx,
            '生助力量': support_count,
            '克泄力量': restrain_count,
            '旺衰判断': wangshuai,
        }

# 便捷函数
def calculate_bazi(year: int, month: int, day: int, hour: int) -> Bazi:
    """便捷函数：计算八字"""
    engine = BaziEngine()
    return engine.calculate_bazi(year, month, day, hour)

def get_bazi_info(year: int, month: int, day: int, hour: int, gender: str = '男') -> Dict:
    """获取完整的八字信息"""
    engine = BaziEngine()
    bazi = engine.calculate_bazi(year, month, day, hour)
    
    return {
        '四柱': {
            '年柱': {'天干': bazi.year.gan, '地支': bazi.year.zhi},
            '月柱': {'天干': bazi.month.gan, '地支': bazi.month.zhi},
            '日柱': {'天干': bazi.day.gan, '地支': bazi.day.zhi},
            '时柱': {'天干': bazi.hour.gan, '地支': bazi.hour.zhi},
        },
        '日干': bazi.day_gan,
        '十神': bazi.get_shishen_map(),
        '五行统计': bazi.get_wuxing_count(),
        '旺衰分析': engine.analyze_wangshuai(bazi),
        '大运': engine.calculate_dayun(bazi, gender, year),
    }
