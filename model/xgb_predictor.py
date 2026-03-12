"""
XGBoost预测模型
替代神经网络，提供更好的可解释性
"""

import json
import os
import sys
import numpy as np
import xgboost as xgb
from typing import Dict, List
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import TRIGRAMS

class XGBHexagramPredictor:
    """XGBoost六爻预测器"""
    
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
            os.path.dirname(__file__), 'xgb_model.json'
        )
        self.label_encoders = {}
        self.models = {}
        self.feature_names = []
    
    def _extract_features(self, case: Dict) -> np.ndarray:
        """从案例中提取特征"""
        features = []
        
        # 1. 时间特征 (4维)
        features.append(case['month'] / 12.0)
        features.append(case['day'] / 31.0)
        features.append(case['hour'] / 24.0)
        features.append((case['year'] - 2020) / 10.0)
        
        # 2. 问事类型 one-hot (5维)
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
        
        return np.array(features, dtype=np.float32)
    
    def prepare_data(self, cases: List[Dict]):
        """准备训练数据"""
        X = []
        y_fortune = []
        y_type = []
        y_time = []
        
        for case in cases:
            features = self._extract_features(case)
            X.append(features)
            
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
        
        return np.array(X), np.array(y_fortune), np.array(y_type), np.array(y_time)
    
    def train(self, cases, test_size=0.2, random_state=42):
        """训练模型"""
        print(f"准备数据: {len(cases)} 个案例")
        
        X, y_fortune, y_type, y_time = self.prepare_data(cases)
        
        # 划分训练集和测试集
        X_train, X_test, y_fortune_train, y_fortune_test = train_test_split(
            X, y_fortune, test_size=test_size, random_state=random_state
        )
        _, _, y_type_train, y_type_test = train_test_split(
            X, y_type, test_size=test_size, random_state=random_state
        )
        _, _, y_time_train, y_time_test = train_test_split(
            X, y_time, test_size=test_size, random_state=random_state
        )
        
        print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")
        
        # 训练吉凶预测模型
        print("\n训练吉凶预测模型...")
        self.models['fortune'] = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective='multi:softprob',
            num_class=len(self.FORTUNE_LEVELS),
            eval_metric='mlogloss',
            use_label_encoder=False
        )
        self.models['fortune'].fit(
            X_train, y_fortune_train,
            eval_set=[(X_test, y_fortune_test)],
            verbose=False
        )
        
        fortune_acc = self.models['fortune'].score(X_test, y_fortune_test)
        print(f"吉凶预测准确率: {fortune_acc:.2%}")
        
        # 训练事件类型预测模型
        print("\n训练事件类型预测模型...")
        self.models['type'] = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective='multi:softprob',
            num_class=len(self.QUESTION_TYPES),
            eval_metric='mlogloss',
            use_label_encoder=False
        )
        self.models['type'].fit(
            X_train, y_type_train,
            eval_set=[(X_test, y_type_test)],
            verbose=False
        )
        
        type_acc = self.models['type'].score(X_test, y_type_test)
        print(f"事件类型预测准确率: {type_acc:.2%}")
        
        # 训练时间窗口预测模型
        print("\n训练时间窗口预测模型...")
        self.models['time'] = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective='multi:softprob',
            num_class=len(self.TIME_WINDOWS),
            eval_metric='mlogloss',
            use_label_encoder=False
        )
        self.models['time'].fit(
            X_train, y_time_train,
            eval_set=[(X_test, y_time_test)],
            verbose=False
        )
        
        time_acc = self.models['time'].score(X_test, y_time_test)
        print(f"时间窗口预测准确率: {time_acc:.2%}")
        
        # 保存特征名
        self.feature_names = [f'f{i}' for i in range(X.shape[1])]
        
        # 保存模型
        self.save_model()
        
        return {
            'fortune_accuracy': fortune_acc,
            'type_accuracy': type_acc,
            'time_accuracy': time_acc,
        }
    
    def predict(self, case: Dict) -> Dict:
        """预测单个案例"""
        if not self.models:
            self.load_model()
        
        features = self._extract_features(case).reshape(1, -1)
        
        # 吉凶预测
        fortune_probs = self.models['fortune'].predict_proba(features)[0]
        fortune_pred = np.argmax(fortune_probs)
        
        # 事件类型预测
        type_probs = self.models['type'].predict_proba(features)[0]
        type_pred = np.argmax(type_probs)
        
        # 时间窗口预测
        time_probs = self.models['time'].predict_proba(features)[0]
        time_pred = np.argmax(time_probs)
        
        return {
            'fortune_level': self.FORTUNE_LEVELS[fortune_pred],
            'fortune_probabilities': {
                level: fortune_probs[i] 
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
            'question_type': self.QUESTION_TYPES[type_pred],
            'type_probabilities': {
                t: type_probs[i]
                for i, t in enumerate(self.QUESTION_TYPES)
            },
            'time_window': self.TIME_WINDOWS[time_pred],
            'time_probabilities': {
                t: time_probs[i]
                for i, t in enumerate(self.TIME_WINDOWS)
            },
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
        for task, model in self.models.items():
            path = self.model_path.replace('.json', f'_{task}.json')
            model.save_model(path)
        
        # 保存配置
        config = {
            'feature_names': self.feature_names,
            'fortune_levels': self.FORTUNE_LEVELS,
            'question_types': self.QUESTION_TYPES,
            'time_windows': self.TIME_WINDOWS,
        }
        config_path = self.model_path.replace('.json', '_config.pkl')
        with open(config_path, 'wb') as f:
            pickle.dump(config, f)
        
        print(f"\n模型已保存至: {self.model_path}")
    
    def load_model(self):
        """加载模型"""
        self.models = {}
        
        for task in ['fortune', 'type', 'time']:
            path = self.model_path.replace('.json', f'_{task}.json')
            if os.path.exists(path):
                self.models[task] = xgb.XGBClassifier()
                self.models[task].load_model(path)
            else:
                raise FileNotFoundError(f"模型文件不存在: {path}")
        
        # 加载配置
        config_path = self.model_path.replace('.json', '_config.pkl')
        if os.path.exists(config_path):
            with open(config_path, 'rb') as f:
                config = pickle.load(f)
                self.feature_names = config.get('feature_names', [])
        
        print(f"模型已加载: {self.model_path}")

def train_xgb_model():
    """训练XGBoost模型主函数"""
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
    model = XGBHexagramPredictor()
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
    train_xgb_model()
