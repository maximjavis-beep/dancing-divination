"""
改进的时间窗口预测模块
将5分类改为3分类，增加时间相关特征
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import TRIGRAMS, LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS, YOUHUN_HEXAGRAMS, GUIHUN_HEXAGRAMS

# 农历节气数据（简化版）
SOLAR_TERMS = [
    (2, 4), (2, 19),   # 立春、雨水
    (3, 6), (3, 21),   # 惊蛰、春分
    (4, 5), (4, 20),   # 清明、谷雨
    (5, 6), (5, 21),   # 立夏、小满
    (6, 6), (6, 21),   # 芒种、夏至
    (7, 7), (7, 23),   # 小暑、大暑
    (8, 8), (8, 23),   # 立秋、处暑
    (9, 8), (9, 23),   # 白露、秋分
    (10, 8), (10, 24), # 寒露、霜降
    (11, 7), (11, 22), # 立冬、小雪
    (12, 7), (12, 22), # 大雪、冬至
    (1, 6), (1, 20),   # 小寒、大寒
]

class TimeWindowPredictor:
    """改进的时间窗口预测器
    
    将原来的5分类改为3分类：
    - 近期（1周内）
    - 中期（1-3个月）
    - 远期（3个月以上）
    
    增加时间相关特征：节气、月相、时辰五行等
    """
    
    # 简化后的3分类时间窗口
    TIME_WINDOWS_3 = ['近期', '中期', '远期']
    
    # 时辰对应的地支和五行
    HOUR_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    HOUR_ELEMENTS = ['水', '土', '木', '木', '土', '火', '火', '土', '金', '金', '土', '水']
    
    def __init__(self, model_path=None):
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 'time_window_model.pkl'
        )
        self.model = None
        self.feature_names = []
    
    def _get_solar_term(self, month: int, day: int) -> int:
        """获取节气索引（简化版）"""
        for i, (m, d) in enumerate(SOLAR_TERMS):
            if month == m and day >= d:
                return i
            if month > m:
                return i
        return 0
    
    def _extract_features(self, case: Dict) -> np.ndarray:
        """提取时间窗口预测特征"""
        features = []
        
        year = case['year']
        month = case['month']
        day = case['day']
        hour = case['hour']
        
        # 1. 基础时间特征 (4维)
        features.append(month / 12.0)
        features.append(day / 31.0)
        features.append(hour / 24.0)
        features.append((year - 2020) / 10.0)
        
        # 2. 节气特征 (1维) - 新增
        solar_term = self._get_solar_term(month, day)
        features.append(solar_term / 24.0)
        
        # 3. 季节 one-hot (4维) - 新增
        season = self._get_season(month, day)
        season_onehot = [1 if i == season else 0 for i in range(4)]
        features.extend(season_onehot)
        
        # 4. 时辰五行 one-hot (5维) - 新增
        hour_zhi_idx = hour % 12
        hour_element = self.HOUR_ELEMENTS[hour_zhi_idx]
        element_onehot = self._element_to_onehot(hour_element)
        features.extend(element_onehot)
        
        # 5. 六爻特征 (6维)
        features.extend(case['hexagram']['lines'])
        
        # 6. 动爻 one-hot (6维)
        moving_onehot = [0] * 6
        for pos in case['hexagram']['moving_lines']:
            if 1 <= pos <= 6:
                moving_onehot[pos - 1] = 1
        features.extend(moving_onehot)
        
        # 7. 上下卦 one-hot (16维)
        upper_idx = list(TRIGRAMS.keys()).index(case['hexagram']['upper_trigram'])
        lower_idx = list(TRIGRAMS.keys()).index(case['hexagram']['lower_trigram'])
        
        upper_onehot = [1 if i == upper_idx else 0 for i in range(8)]
        lower_onehot = [1 if i == lower_idx else 0 for i in range(8)]
        features.extend(upper_onehot)
        features.extend(lower_onehot)
        
        # 8. 世应位置 (2维)
        features.append(case['analysis']['shi_position'] / 6.0)
        features.append(case['analysis']['ying_position'] / 6.0)
        
        # 9. 五行关系 one-hot (5维)
        element_relations = {'生': 0, '被生': 1, '克': 2, '被克': 3, '比和': 4}
        relation = case['analysis']['element_relation']
        relation_idx = element_relations.get(relation, 4)
        relation_onehot = [1 if i == relation_idx else 0 for i in range(5)]
        features.extend(relation_onehot)
        
        # 10. 动爻数量 (1维)
        features.append(len(case['hexagram']['moving_lines']) / 6.0)
        
        # 11. 是否有动爻 (1维)
        features.append(1 if case['hexagram']['moving_lines'] else 0)
        
        # 12. 特殊卦象 (4维)
        hexagram_name = case['hexagram'].get('name', '')
        features.append(1 if hexagram_name in LIUCHONG_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in LIUHE_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in YOUHUN_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in GUIHUN_HEXAGRAMS else 0)
        
        # 13. 动爻位置与时间的交互特征 (6维) - 新增
        for i in range(6):
            if i < len(case['hexagram']['moving_lines']):
                # 动爻位置与时辰的交互
                features.append((case['hexagram']['moving_lines'][i] / 6.0) * (hour / 24.0))
            else:
                features.append(0.0)
        
        return np.array(features, dtype=np.float32)
    
    def _get_season(self, month: int, day: int) -> int:
        """获取季节 (0:春, 1:夏, 2:秋, 3:冬)"""
        if (month == 2 and day >= 4) or month in [3, 4] or (month == 5 and day < 6):
            return 0  # 春
        elif (month == 5 and day >= 6) or month in [6, 7] or (month == 8 and day < 8):
            return 1  # 夏
        elif (month == 8 and day >= 8) or month in [9, 10] or (month == 11 and day < 7):
            return 2  # 秋
        else:
            return 3  # 冬
    
    def _element_to_onehot(self, element: str) -> List[int]:
        """将五行转换为one-hot编码"""
        elements = ['金', '木', '水', '火', '土']
        idx = elements.index(element) if element in elements else 4
        return [1 if i == idx else 0 for i in range(5)]
    
    def _convert_time_window(self, original_window: str) -> int:
        """将原始5分类时间窗口转换为3分类"""
        # 原始分类映射到3分类
        mapping = {
            '近期（3日内）': 0,  # 近期
            '短期（一周内）': 0,  # 近期
            '中期（一月内）': 1,  # 中期
            '长期（三月内）': 1,  # 中期
            '远期（半年内）': 2,  # 远期
        }
        return mapping.get(original_window, 1)  # 默认中期
    
    def prepare_data(self, cases: List[Dict]):
        """准备训练数据"""
        X = []
        y = []
        
        for case in cases:
            features = self._extract_features(case)
            X.append(features)
            
            # 转换时间窗口为3分类
            original_window = case['expert_interpretation'].get('time_window', '中期（一月内）')
            y.append(self._convert_time_window(original_window))
        
        return np.array(X), np.array(y)
    
    def train(self, cases, test_size=0.2, random_state=42):
        """训练时间窗口预测模型"""
        print(f"准备数据: {len(cases)} 个案例")
        
        X, y = self.prepare_data(cases)
        
        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")
        print(f"特征维度: {X.shape[1]}")
        
        # 统计各类别分布
        unique, counts = np.unique(y, return_counts=True)
        print("\n时间窗口分布:")
        for i, (u, c) in enumerate(zip(unique, counts)):
            print(f"  {self.TIME_WINDOWS_3[u]}: {c} ({c/len(y)*100:.1f}%)")
        
        # 训练模型
        print("\n训练时间窗口预测模型...")
        self.model = GradientBoostingClassifier(
            n_estimators=150,  # 增加树的数量
            max_depth=6,       # 增加深度
            learning_rate=0.05, # 降低学习率
            subsample=0.8,     # 使用子采样防止过拟合
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # 评估
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\n准确率: {accuracy:.2%}")
        print("\n分类报告:")
        print(classification_report(y_test, y_pred, target_names=self.TIME_WINDOWS_3))
        
        # 特征重要性
        importance = self.model.feature_importances_
        print("\nTop 10 重要特征:")
        indices = np.argsort(importance)[::-1][:10]
        for i in indices:
            print(f"  特征{i}: {importance[i]:.4f}")
        
        # 保存模型
        self.save_model()
        
        return {'accuracy': accuracy}
    
    def predict(self, case: Dict) -> Dict:
        """预测时间窗口"""
        if self.model is None:
            try:
                self.load_model()
            except FileNotFoundError:
                return {
                    'time_window': '中期',
                    'time_probabilities': {t: 1/3 for t in self.TIME_WINDOWS_3},
                    'note': '模型未加载'
                }
        
        features = self._extract_features(case).reshape(1, -1)
        probs = self.model.predict_proba(features)[0]
        pred = np.argmax(probs)
        
        return {
            'time_window': self.TIME_WINDOWS_3[pred],
            'time_probabilities': {
                t: float(probs[i]) for i, t in enumerate(self.TIME_WINDOWS_3)
            }
        }
    
    def save_model(self):
        """保存模型"""
        with open(self.model_path, 'wb') as f:
            pickle.dump({'model': self.model}, f)
        print(f"\n模型已保存至: {self.model_path}")
    
    def load_model(self):
        """加载模型"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
            print(f"模型已加载: {self.model_path}")
        else:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")


def train_time_window_model():
    """训练时间窗口预测模型主函数"""
    # 加载数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    # 加载古籍案例
    gudian_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gudian_cases.json')
    if os.path.exists(gudian_path):
        with open(gudian_path, 'r', encoding='utf-8') as f:
            gudian_cases = json.load(f)
        cases.extend(gudian_cases)
        print(f"合并古籍案例，共 {len(cases)} 个案例")
    
    # 训练模型
    predictor = TimeWindowPredictor()
    results = predictor.train(cases)
    
    print("\n训练完成!")
    print(f"时间窗口预测准确率: {results['accuracy']:.2%}")
    
    return predictor


if __name__ == '__main__':
    train_time_window_model()
