#!/usr/bin/env python3
"""
增强版GBM预测器
使用更多特征和优化参数
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.enhanced_features import EnhancedFeatureExtractor

class EnhancedGBMPredictor:
    """增强版GBM预测器"""
    
    FORTUNE_LEVELS = ['大凶', '凶', '平', '吉', '大吉']
    QUESTION_TYPES = ['财运', '事业', '爱情', '健康', '诉讼']
    TIME_WINDOWS = ['近期', '中期', '远期']
    
    def __init__(self):
        self.models = {}
        self.extractor = EnhancedFeatureExtractor()
        self.model_dir = os.path.join(os.path.dirname(__file__), '..', 'model')
        self.model_path = os.path.join(self.model_dir, 'enhanced_gbm_model.pkl')
    
    def prepare_data(self, cases: List[Dict]):
        """准备数据"""
        X_fortune = []
        X_type = []
        X_time = []
        y_fortune = []
        y_type = []
        y_time = []
        
        for case in cases:
            # 提取特征（不含问事类型，避免泄露）
            features = self.extractor.extract_features(case, include_question_type=False)
            
            # 吉凶标签
            fortune = case['expert_interpretation']['fortune_level']
            if fortune in self.FORTUNE_LEVELS:
                y_fortune.append(self.FORTUNE_LEVELS.index(fortune))
                X_fortune.append(features)
            
            # 问事类型标签
            qtype = case['question_type']
            if qtype in self.QUESTION_TYPES:
                y_type.append(self.QUESTION_TYPES.index(qtype))
                X_type.append(features)
            
            # 时间窗口标签（转换为3分类）
            time_window = case['expert_interpretation'].get('time_window', '中期')
            time_label = self._convert_time_window(time_window)
            y_time.append(time_label)
            X_time.append(features)
        
        return {
            'fortune': (np.array(X_fortune), np.array(y_fortune)),
            'type': (np.array(X_type), np.array(y_type)),
            'time': (np.array(X_time), np.array(y_time)),
        }
    
    def _convert_time_window(self, time_window: str) -> int:
        """将时间窗口转换为3分类"""
        if '近期' in time_window or '短期' in time_window or '3日' in time_window or '一周' in time_window:
            return 0  # 近期
        elif '中期' in time_window or '一月' in time_window:
            return 1  # 中期
        else:
            return 2  # 远期
    
    def train(self, cases: List[Dict], test_size=0.2, random_state=42):
        """训练模型"""
        print(f"准备数据: {len(cases)} 个案例")
        print(f"特征维度: {self.extractor.get_feature_count()}")
        
        data = self.prepare_data(cases)
        X_fortune, y_fortune = data['fortune']
        X_type, y_type = data['type']
        X_time, y_time = data['time']
        
        # 划分训练集和测试集
        X_fortune_train, X_fortune_test, y_fortune_train, y_fortune_test = train_test_split(
            X_fortune, y_fortune, test_size=test_size, random_state=random_state, stratify=y_fortune
        )
        X_type_train, X_type_test, y_type_train, y_type_test = train_test_split(
            X_type, y_type, test_size=test_size, random_state=random_state, stratify=y_type
        )
        X_time_train, X_time_test, y_time_train, y_time_test = train_test_split(
            X_time, y_time, test_size=test_size, random_state=random_state, stratify=y_time
        )
        
        print(f"训练集: {len(X_fortune_train)}, 测试集: {len(X_fortune_test)}")
        
        results = {}
        
        # 1. 吉凶预测模型（优化参数）
        print("\n=== 吉凶预测模型 ===")
        self.models['fortune'] = GradientBoostingClassifier(
            n_estimators=200,  # 增加树的数量
            max_depth=6,       # 增加深度
            learning_rate=0.05, # 降低学习率
            subsample=0.8,     # 子采样
            random_state=42,
            verbose=0
        )
        self.models['fortune'].fit(X_fortune_train, y_fortune_train)
        
        fortune_pred = self.models['fortune'].predict(X_fortune_test)
        fortune_acc = accuracy_score(y_fortune_test, fortune_pred)
        results['fortune'] = fortune_acc
        print(f"准确率: {fortune_acc:.2%}")
        print(f"分类报告:\n{classification_report(y_fortune_test, fortune_pred, target_names=self.FORTUNE_LEVELS)}")
        
        # 2. 事件类型预测模型（使用RandomForest）
        print("\n=== 事件类型预测模型 ===")
        self.models['type'] = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        self.models['type'].fit(X_type_train, y_type_train)
        
        type_pred = self.models['type'].predict(X_type_test)
        type_acc = accuracy_score(y_type_test, type_pred)
        results['type'] = type_acc
        print(f"准确率: {type_acc:.2%}")
        print(f"分类报告:\n{classification_report(y_type_test, type_pred, target_names=self.QUESTION_TYPES)}")
        
        # 3. 时间窗口预测模型
        print("\n=== 时间窗口预测模型 ===")
        self.models['time'] = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.models['time'].fit(X_time_train, y_time_train)
        
        time_pred = self.models['time'].predict(X_time_test)
        time_acc = accuracy_score(y_time_test, time_pred)
        results['time'] = time_acc
        print(f"准确率: {time_acc:.2%}")
        print(f"分类报告:\n{classification_report(y_time_test, time_pred, target_names=self.TIME_WINDOWS)}")
        
        # 特征重要性
        print("\n=== 特征重要性 (吉凶预测) ===")
        importances = self.models['fortune'].feature_importances_
        feature_names = self.extractor.feature_names
        indices = np.argsort(importances)[::-1][:10]
        for i in indices:
            print(f"  {feature_names[i]}: {importances[i]:.4f}")
        
        return results
    
    def predict(self, case: Dict, return_components: bool = False) -> Dict:
        """预测"""
        if not self.models:
            try:
                self.load_model()
            except FileNotFoundError:
                return self._random_prediction()
        
        # 提取特征
        features = self.extractor.extract_features(case, include_question_type=False).reshape(1, -1)
        
        # 吉凶预测
        fortune_probs = self.models['fortune'].predict_proba(features)[0]
        fortune_pred = np.argmax(fortune_probs)
        
        # 事件类型预测
        type_probs = self.models['type'].predict_proba(features)[0]
        type_pred = np.argmax(type_probs)
        
        # 时间窗口预测
        time_probs = self.models['time'].predict_proba(features)[0]
        time_pred = np.argmax(time_probs)
        
        result = {
            'fortune_level': self.FORTUNE_LEVELS[fortune_pred],
            'fortune_probabilities': {
                level: float(fortune_probs[i])
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
            'time_window': self.TIME_WINDOWS[time_pred],
            'time_probabilities': {
                t: float(time_probs[i])
                for i, t in enumerate(self.TIME_WINDOWS)
            },
            'probabilities': {
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
        """随机预测（模型未加载时）"""
        return {
            'fortune_level': '平',
            'fortune_probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS},
            'time_window': '中期',
            'time_probabilities': {t: 0.33 for t in self.TIME_WINDOWS},
            'probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS},
        }
    
    def save_model(self):
        """保存模型"""
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'extractor': self.extractor
            }, f)
        print(f"\n模型已保存至: {self.model_path}")
    
    def load_model(self):
        """加载模型"""
        with open(self.model_path, 'rb') as f:
            data = pickle.load(f)
            self.models = data['models']
            self.extractor = data['extractor']
        print(f"模型已加载: {self.model_path}")

def train_enhanced_model():
    """训练增强版模型"""
    # 加载案例数据
    base_path = os.path.join(os.path.dirname(__file__), '..')
    
    with open(os.path.join(base_path, 'data', 'cases.json'), 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    with open(os.path.join(base_path, 'data', 'gudian_cases.json'), 'r', encoding='utf-8') as f:
        gudian_cases = json.load(f)
    
    cases.extend(gudian_cases)
    print(f"合并古籍案例，共 {len(cases)} 个案例")
    
    # 训练模型
    model = EnhancedGBMPredictor()
    results = model.train(cases)
    model.save_model()
    
    print("\n" + "="*50)
    print("训练完成!")
    print(f"吉凶预测准确率: {results['fortune']:.2%}")
    print(f"事件类型预测准确率: {results['type']:.2%}")
    print(f"时间窗口预测准确率: {results['time']:.2%}")
    print("="*50)
    
    return model

if __name__ == '__main__':
    train_enhanced_model()
