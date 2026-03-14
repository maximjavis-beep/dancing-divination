"""
卦象趋势分析模块
分析未来12小时内卦象的变化趋势
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import Counter

class HexagramTrendAnalyzer:
    """卦象趋势分析器"""
    
    FORTUNE_ORDER = {'大凶': 0, '凶': 1, '平': 2, '吉': 3, '大吉': 4}
    
    def __init__(self, engine, model):
        self.engine = engine
        self.model = model
    
    def analyze_trend(self, base_time: datetime, question_type: str, 
                      birth_info: Dict = None, gender: str = '男') -> Dict:
        """
        分析未来12小时的卦象趋势
        
        参数：
            base_time: 起卦基准时间
            question_type: 问事类型
            birth_info: 八字信息（可选）
            gender: 性别
        
        返回：
            趋势分析结果
        """
        # 生成12个时间点的卦象（每小时一个）
        hourly_readings = []
        
        for hour_offset in range(13):  # 0-12小时
            current_time = base_time + timedelta(hours=hour_offset)
            
            # 生成卦象
            hexagram = self.engine.generate_hexagram_from_time(
                current_time.year, current_time.month, 
                current_time.day, current_time.hour
            )
            
            # 构建案例
            case = {
                'year': current_time.year,
                'month': current_time.month,
                'day': current_time.day,
                'hour': current_time.hour,
                'question_type': question_type,
                'hexagram': {
                    'name': hexagram.name,
                    'upper_trigram': hexagram.upper_trigram,
                    'lower_trigram': hexagram.lower_trigram,
                    'lines': hexagram.lines,
                    'moving_lines': hexagram.moving_lines,
                },
                'analysis': {
                    'shi_position': 3,  # 简化
                    'ying_position': 6,
                    'element_relation': '比和',
                }
            }
            
            # AI预测
            try:
                prediction = self.model.predict(case)
                fortune_level = prediction['fortune_level']
                fortune_score = self.FORTUNE_ORDER.get(fortune_level, 2)
            except:
                fortune_level = '平'
                fortune_score = 2
            
            hourly_readings.append({
                'hour_offset': hour_offset,
                'time': current_time.strftime('%H:%M'),
                'hexagram_name': hexagram.name,
                'fortune_level': fortune_level,
                'fortune_score': fortune_score,
                'time_window': prediction.get('time_window', '中期（一月内）'),
            })
        
        # 分析趋势
        trend_analysis = self._analyze_trend_pattern(hourly_readings)
        
        # 找出最佳时机
        best_windows = self._find_best_windows(hourly_readings)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            hourly_readings, trend_analysis, best_windows, question_type
        )
        
        return {
            'base_time': base_time.strftime('%Y-%m-%d %H:%M'),
            'hourly_readings': hourly_readings,
            'trend_analysis': trend_analysis,
            'best_windows': best_windows,
            'recommendations': recommendations,
        }
    
    def _analyze_trend_pattern(self, readings: List[Dict]) -> Dict:
        """分析趋势模式"""
        scores = [r['fortune_score'] for r in readings]
        levels = [r['fortune_level'] for r in readings]
        
        # 统计
        level_counts = Counter(levels)
        
        # 趋势方向
        first_half = sum(scores[:6]) / 6
        second_half = sum(scores[7:]) / 6
        
        if second_half > first_half + 0.5:
            trend_direction = '上升'
        elif second_half < first_half - 0.5:
            trend_direction = '下降'
        else:
            trend_direction = '平稳'
        
        # 稳定性
        score_variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
        if score_variance < 0.5:
            stability = '稳定'
        elif score_variance < 1.0:
            stability = '波动'
        else:
            stability = '剧烈波动'
        
        # 整体吉凶
        avg_score = sum(scores) / len(scores)
        if avg_score >= 3.5:
            overall = '大吉'
        elif avg_score >= 2.5:
            overall = '吉'
        elif avg_score >= 1.5:
            overall = '平'
        elif avg_score >= 0.5:
            overall = '凶'
        else:
            overall = '大凶'
        
        return {
            'trend_direction': trend_direction,
            'stability': stability,
            'overall_fortune': overall,
            'average_score': round(avg_score, 2),
            'level_distribution': dict(level_counts),
            'best_hour': readings[scores.index(max(scores))]['time'],
            'worst_hour': readings[scores.index(min(scores))]['time'],
        }
    
    def _find_best_windows(self, readings: List[Dict]) -> List[Dict]:
        """找出最佳时机窗口"""
        windows = []
        
        # 找出连续吉时
        current_window = None
        
        for reading in readings:
            score = reading['fortune_score']
            
            if score >= 3:  # 吉或大吉
                if current_window is None:
                    current_window = {
                        'start': reading['time'],
                        'start_offset': reading['hour_offset'],
                        'scores': [score],
                    }
                else:
                    current_window['scores'].append(score)
            else:
                if current_window is not None:
                    current_window['end'] = readings[
                        readings.index(reading) - 1
                    ]['time']
                    current_window['end_offset'] = readings[
                        readings.index(reading) - 1
                    ]['hour_offset']
                    current_window['duration'] = len(current_window['scores'])
                    current_window['average_score'] = sum(current_window['scores']) / len(current_window['scores'])
                    
                    if current_window['duration'] >= 2:  # 至少2小时
                        windows.append(current_window)
                    
                    current_window = None
        
        # 处理最后一个窗口
        if current_window is not None:
            current_window['end'] = readings[-1]['time']
            current_window['end_offset'] = readings[-1]['hour_offset']
            current_window['duration'] = len(current_window['scores'])
            current_window['average_score'] = sum(current_window['scores']) / len(current_window['scores'])
            
            if current_window['duration'] >= 1:
                windows.append(current_window)
        
        # 按平均分数排序
        windows.sort(key=lambda x: x['average_score'], reverse=True)
        
        return windows[:3]  # 返回前3个最佳窗口
    
    def _generate_recommendations(self, readings: List[Dict], 
                                   trend: Dict, windows: List[Dict],
                                   question_type: str) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于整体趋势
        if trend['overall_fortune'] in ['大吉', '吉']:
            recommendations.append(f"✓ 未来12小时整体运势{trend['overall_fortune']}，适合推进{question_type}相关事宜")
        elif trend['overall_fortune'] in ['凶', '大凶']:
            recommendations.append(f"⚠️ 未来12小时整体运势偏弱，{question_type}方面需谨慎行事")
        else:
            recommendations.append(f"→ 未来12小时运势平稳，{question_type}方面宜守不宜攻")
        
        # 基于趋势方向
        if trend['trend_direction'] == '上升':
            recommendations.append("📈 运势呈上升趋势，越往后时机越好，可适当推迟重要行动")
        elif trend['trend_direction'] == '下降':
            recommendations.append("📉 运势呈下降趋势，建议尽早行动，把握当前时机")
        else:
            recommendations.append("➡️ 运势相对平稳，选择合适的时间窗口即可")
        
        # 基于最佳窗口
        if windows:
            best = windows[0]
            recommendations.append(
                f"🎯 最佳时机：{best['start']} - {best['end']}（持续{best['duration']}小时），"
                f"此时行动成功率最高"
            )
        
        # 基于稳定性
        if trend['stability'] == '剧烈波动':
            recommendations.append("⚡ 运势波动较大，建议多次确认后再做重要决定")
        elif trend['stability'] == '稳定':
            recommendations.append("✓ 运势相对稳定，可按计划推进")
        
        # 具体行动建议
        if question_type == '财运':
            if trend['overall_fortune'] in ['大吉', '吉']:
                recommendations.append("💰 财运较佳，可考虑投资或签约")
            else:
                recommendations.append("💰 财运一般，避免大额支出或高风险投资")
        
        elif question_type == '事业':
            if trend['overall_fortune'] in ['大吉', '吉']:
                recommendations.append("💼 事业运旺，适合面试、谈判或推进项目")
            else:
                recommendations.append("💼 事业运平，宜巩固现有成果，不宜冒进")
        
        elif question_type == '爱情':
            if trend['overall_fortune'] in ['大吉', '吉']:
                recommendations.append("💕 感情运佳，适合表白、约会或谈婚论嫁")
            else:
                recommendations.append("💕 感情运平，需多沟通理解，避免争执")
        
        elif question_type == '健康':
            if trend['overall_fortune'] in ['大吉', '吉']:
                recommendations.append("🏥 健康运佳，身体恢复能力强")
            else:
                recommendations.append("🏥 健康运弱，注意休息，及时就医")
        
        elif question_type == '诉讼':
            if trend['overall_fortune'] in ['大吉', '吉']:
                recommendations.append("⚖️ 诉讼运佳，胜算较大，可积极推进")
            else:
                recommendations.append("⚖️ 诉讼运弱，宜和解，避免长期纠缠")
        
        return recommendations

# 便捷函数
def analyze_trend(engine, model, base_time: datetime, question_type: str,
                  birth_info: Dict = None, gender: str = '男') -> Dict:
    """便捷函数：分析趋势"""
    analyzer = HexagramTrendAnalyzer(engine, model)
    return analyzer.analyze_trend(base_time, question_type, birth_info, gender)
