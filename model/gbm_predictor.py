"""
Gradient Boosting预测模型
使用scikit-learn，无需额外依赖
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import TRIGRAMS, LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS, YOUHUN_HEXAGRAMS, GUIHUN_HEXAGRAMS

class GBMHexagramPredictor:
    """Gradient Boosting六爻预测器"""
    
    FORTUNE_LEVELS = ['大吉', '吉', '平', '凶', '大凶']
    QUESTION_TYPES = ['财运', '事业', '婚姻', '健康', '诉讼']
    TIME_WINDOWS = [
        '近期（3日内）',
        '短期（一周内）',
        '中期（一月内）',
        '长期（三月内）',
        '远期（半年内）',
    ]
    
    def __init__(self, model_path=None):
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 'gbm_model.pkl'
        )
        self.models = {}
        self.feature_names = []
    
    def _convert_to_3class(self, y_5class: np.ndarray) -> np.ndarray:
        """将5分类时间窗口转换为3分类
        
        0: 近期（3日内） -> 0: 近期
        1: 短期（一周内） -> 0: 近期
        2: 中期（一月内） -> 1: 中期
        3: 长期（三月内） -> 1: 中期
        4: 远期（半年内） -> 2: 远期
        """
        mapping = {0: 0, 1: 0, 2: 1, 3: 1, 4: 2}
        return np.array([mapping.get(i, 1) for i in y_5class])
    
    def _extract_features(self, case: Dict, include_question_type: bool = False) -> np.ndarray:
        """从案例中提取特征
        
        Args:
            case: 案例数据
            include_question_type: 是否包含问事类型特征（默认False，避免特征泄露）
        """
        features = []
        
        # 1. 时间特征 (4维)
        features.append(case['month'] / 12.0)
        features.append(case['day'] / 31.0)
        features.append(case['hour'] / 24.0)
        features.append((case['year'] - 2020) / 10.0)
        
        # 2. 问事类型 one-hot (5维) - 默认不包含，避免特征泄露
        # 事件类型预测时，不应该知道问事类型
        if include_question_type:
            qtype_idx = self.QUESTION_TYPES.index(case['question_type'])
            qtype_onehot = [1 if i == qtype_idx else 0 for i in range(5)]
            features.extend(qtype_onehot)
        
        # 3. 六爻特征 (6维)
        features.extend(case['hexagram']['lines'])
        
        # 4. 动爻 one-hot (6维)
        moving_onehot = [0] * 6
        for pos in case['hexagram']['moving_lines']:
            if 1 <= pos <= 6:
                moving_onehot[pos - 1] = 1
        features.extend(moving_onehot)
        
        # 5. 上下卦 one-hot (8+8=16维)
        upper_idx = list(TRIGRAMS.keys()).index(case['hexagram']['upper_trigram'])
        lower_idx = list(TRIGRAMS.keys()).index(case['hexagram']['lower_trigram'])
        
        upper_onehot = [1 if i == upper_idx else 0 for i in range(8)]
        lower_onehot = [1 if i == lower_idx else 0 for i in range(8)]
        features.extend(upper_onehot)
        features.extend(lower_onehot)
        
        # 6. 世应位置 (2维)
        features.append(case['analysis']['shi_position'] / 6.0)
        features.append(case['analysis']['ying_position'] / 6.0)
        
        # 7. 五行关系 one-hot (5维)
        element_relations = {'生': 0, '被生': 1, '克': 2, '被克': 3, '比和': 4}
        relation = case['analysis']['element_relation']
        relation_idx = element_relations.get(relation, 4)
        relation_onehot = [1 if i == relation_idx else 0 for i in range(5)]
        features.extend(relation_onehot)
        
        # 8. 动爻数量 (1维)
        features.append(len(case['hexagram']['moving_lines']) / 6.0)
        
        # 9. 是否有动爻 (1维)
        features.append(1 if case['hexagram']['moving_lines'] else 0)

        # 10. 六冲/六合/游魂/归魂特征 (4维)
        hexagram_name = case['hexagram'].get('name', '')
        features.append(1 if hexagram_name in LIUCHONG_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in LIUHE_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in YOUHUN_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in GUIHUN_HEXAGRAMS else 0)

        # 11. 特殊格局 one-hot (5维: 普通/六冲/六合/游魂/归魂)
        # 根据卦名判断特殊格局
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
        pattern_idx = pattern_types.index(special_pattern) if special_pattern in pattern_types else 0
        pattern_onehot = [1 if i == pattern_idx else 0 for i in range(5)]
        features.extend(pattern_onehot)

        return np.array(features, dtype=np.float32)
    
    def prepare_data(self, cases: List[Dict]):
        """准备训练数据
        
        为不同预测任务准备不同的特征集：
        - 吉凶/时间预测：不包含问事类型（避免泄露）
        - 事件类型预测：包含问事类型（用于验证特征泄露问题）
        """
        X_fortune = []  # 吉凶预测特征（不含问事类型）
        X_type = []     # 事件类型预测特征（含问事类型，用于调试）
        X_type_clean = []  # 事件类型预测特征（不含问事类型）
        X_time = []     # 时间窗口预测特征（不含问事类型）
        
        y_fortune = []
        y_type = []
        y_time = []
        
        for case in cases:
            # 吉凶/时间预测：不包含问事类型
            features_clean = self._extract_features(case, include_question_type=False)
            X_fortune.append(features_clean)
            X_time.append(features_clean)
            
            # 事件类型预测：测试两种版本
            features_with_type = self._extract_features(case, include_question_type=True)
            X_type.append(features_with_type)
            X_type_clean.append(features_clean)
            
            # 标签编码
            y_fortune.append(self.FORTUNE_LEVELS.index(
                case['expert_interpretation']['fortune_level']
            ))
            y_type.append(self.QUESTION_TYPES.index(case['question_type']))
            
            # 时间窗口
            time_window = case['expert_interpretation'].get('time_window', '中期（一月内）')
            if time_window in self.TIME_WINDOWS:
                y_time.append(self.TIME_WINDOWS.index(time_window))
            else:
                y_time.append(2)  # 默认中期
        
        return {
            'fortune': (np.array(X_fortune), np.array(y_fortune)),
            'type': (np.array(X_type), np.array(y_type)),
            'type_clean': (np.array(X_type_clean), np.array(y_type)),
            'time': (np.array(X_time), np.array(y_time)),
        }
    
    def train(self, cases, test_size=0.2, random_state=42):
        """训练模型"""
        print(f"准备数据: {len(cases)} 个案例")
        
        data = self.prepare_data(cases)
        X_fortune, y_fortune = data['fortune']
        X_type, y_type = data['type']
        X_type_clean, _ = data['type_clean']
        X_time, y_time = data['time']
        
        # 划分训练集和测试集
        X_fortune_train, X_fortune_test, y_fortune_train, y_fortune_test = train_test_split(
            X_fortune, y_fortune, test_size=test_size, random_state=random_state
        )
        X_type_train, X_type_test, y_type_train, y_type_test = train_test_split(
            X_type, y_type, test_size=test_size, random_state=random_state
        )
        X_type_clean_train, X_type_clean_test, _, _ = train_test_split(
            X_type_clean, y_type, test_size=test_size, random_state=random_state
        )
        X_time_train, X_time_test, y_time_train, y_time_test = train_test_split(
            X_time, y_time, test_size=test_size, random_state=random_state
        )
        
        print(f"训练集: {len(X_fortune_train)}, 测试集: {len(X_fortune_test)}")
        
        # 训练吉凶预测模型（带类别权重）
        print("\n=== 吉凶预测模型 ===")
        print(f"特征维度: {X_fortune.shape[1]}")
        # 类别权重：大吉/大凶权重更高
        class_weight = {0: 2.0, 1: 1.5, 2: 1.0, 3: 1.5, 4: 2.0}
        sample_weight = np.array([class_weight.get(y, 1.0) for y in y_fortune_train])

        self.models['fortune'] = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.models['fortune'].fit(X_fortune_train, y_fortune_train, sample_weight=sample_weight)
        
        fortune_pred = self.models['fortune'].predict(X_fortune_test)
        fortune_acc = accuracy_score(y_fortune_test, fortune_pred)
        print(f"准确率: {fortune_acc:.2%}")
        
        # 训练事件类型预测模型（含问事类型特征 - 用于对比）
        print("\n=== 事件类型预测模型（含问事类型特征 - 有泄露）===")
        print(f"特征维度: {X_type.shape[1]}")
        model_type_with_leak = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        model_type_with_leak.fit(X_type_train, y_type_train)
        type_pred_leak = model_type_with_leak.predict(X_type_test)
        type_acc_leak = accuracy_score(y_type_test, type_pred_leak)
        print(f"准确率: {type_acc_leak:.2%}")
        
        # 训练事件类型预测模型（不含问事类型特征 - 正确版本）
        print("\n=== 事件类型预测模型（不含问事类型特征 - 正确）===")
        print(f"特征维度: {X_type_clean.shape[1]}")
        self.models['type'] = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.models['type'].fit(X_type_clean_train, y_type_train)
        type_pred = self.models['type'].predict(X_type_clean_test)
        type_acc = accuracy_score(y_type_test, type_pred)
        print(f"准确率: {type_acc:.2%}")
        
        # 训练时间窗口预测模型（使用新的3分类）
        print("\n=== 时间窗口预测模型（5分类 -> 3分类）===")
        # 将5分类转换为3分类
        y_time_3_train = self._convert_to_3class(y_time_train)
        y_time_3_test = self._convert_to_3class(y_time_test)
        
        print(f"特征维度: {X_time.shape[1]}")
        self.models['time'] = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        self.models['time'].fit(X_time_train, y_time_3_train)
        
        time_pred = self.models['time'].predict(X_time_test)
        time_acc = accuracy_score(y_time_3_test, time_pred)
        print(f"准确率: {time_acc:.2%}")
        
        # 保存3分类映射
        self.TIME_WINDOWS_3 = ['近期', '中期', '远期']
        
        # 保存特征名
        self.feature_names = [f'f{i}' for i in range(X.shape[1])]
        
        # 保存模型
        self.save_model()
        
        return {
            'fortune_accuracy': fortune_acc,
            'type_accuracy': type_acc,
            'time_accuracy': time_acc,
        }
    
    def predict(self, case: Dict, return_components: bool = False) -> Dict:
        """预测单个案例
        
        Args:
            case: 案例数据
            return_components: 是否返回各模型组件的预测结果
        """
        if not self.models:
            try:
                self.load_model()
            except FileNotFoundError:
                # 模型未训练，返回随机预测
                return self._random_prediction()
        
        # 吉凶预测：使用不含问事类型的特征
        features_fortune = self._extract_features(case, include_question_type=False).reshape(1, -1)
        fortune_probs = self.models['fortune'].predict_proba(features_fortune)[0]
        fortune_pred = np.argmax(fortune_probs)
        
        # 事件类型预测：使用不含问事类型的特征（正确版本）
        features_type = self._extract_features(case, include_question_type=False).reshape(1, -1)
        type_probs = self.models['type'].predict_proba(features_type)[0]
        type_pred = np.argmax(type_probs)
        
        # 时间窗口预测：使用不含问事类型的特征（3分类）
        features_time = self._extract_features(case, include_question_type=False).reshape(1, -1)
        time_probs = self.models['time'].predict_proba(features_time)[0]
        time_pred = np.argmax(time_probs)
        
        # 获取3分类时间窗口名称
        time_windows_3 = getattr(self, 'TIME_WINDOWS_3', ['近期', '中期', '远期'])
        
        result = {
            'fortune_level': self.FORTUNE_LEVELS[fortune_pred],
            'fortune_probabilities': {
                level: float(fortune_probs[i])
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
            'time_window': time_windows_3[time_pred],
            'time_probabilities': {
                t: float(time_probs[i])
                for i, t in enumerate(time_windows_3)
            },
            'probabilities': {  # 兼容前端格式
                level: float(fortune_probs[i])
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
        }
        
        if return_components:
            result['question_type_pred'] = self.QUESTION_TYPES[type_pred]
            result['type_probabilities'] = {
                t: float(type_probs[i])
                for i, t in enumerate(self.QUESTION_TYPES)
            }
        
        return result
    
    def _random_prediction(self) -> Dict:
        """生成随机预测（模型未加载时的回退）"""
        import random
        return {
            'fortune_level': random.choice(self.FORTUNE_LEVELS),
            'fortune_probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS},
            'time_window': random.choice(self.TIME_WINDOWS),
            'time_probabilities': {t: 0.2 for t in self.TIME_WINDOWS},
            'probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS},
            'note': '演示模式：模型未训练或加载失败'
        }
    
    def get_feature_importance(self) -> Dict[str, List[Dict]]:
        """获取特征重要性"""
        if not self.models:
            self.load_model()
        
        importance = {}
        for task, model in self.models.items():
            scores = model.feature_importances_
            importance[task] = [
                {'feature': f'feature_{i}', 'importance': float(score)}
                for i, score in enumerate(scores)
            ]
            importance[task].sort(key=lambda x: x['importance'], reverse=True)
        
        return importance
    
    def save_model(self):
        """保存模型"""
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'feature_names': self.feature_names,
            }, f)
        
        print(f"\n模型已保存至: {self.model_path}")
    
    def load_model(self):
        """加载模型"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.models = data['models']
                self.feature_names = data.get('feature_names', [])
            print(f"模型已加载: {self.model_path}")
        else:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

def train_gbm_model():
    """训练Gradient Boosting模型主函数"""
    # 加载模拟数据
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
    model = GBMHexagramPredictor()
    results = model.train(cases)
    
    print("\n训练完成!")
    print(f"吉凶预测准确率: {results['fortune_accuracy']:.2%}")
    print(f"事件类型预测准确率: {results['type_accuracy']:.2%}")
    print(f"时间窗口预测准确率: {results['time_accuracy']:.2%}")
    
    # 特征重要性
    importance = model.get_feature_importance()
    print("\n吉凶预测 Top 5 重要特征:")
    for feat in importance['fortune'][:5]:
        print(f"  {feat['feature']}: {feat['importance']:.4f}")
    
    return model

if __name__ == '__main__':
    train_gbm_model()
