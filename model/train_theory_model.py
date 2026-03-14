#!/usr/bin/env python3
"""
使用基于理论的案例数据训练模型
"""

import json
import os
import sys
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.feature_engineer import FeatureEngineer

class TheoryBasedPredictor:
    """基于理论数据的预测器"""
    
    FORTUNE_LEVELS = ['大凶', '凶', '平', '吉', '大吉']
    QUESTION_TYPES = ['财运', '事业', '爱情', '健康', '诉讼']
    TIME_WINDOWS_3 = ['近期', '中期', '远期']
    
    def __init__(self, model_path=None):
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 'theory_model.pkl'
        )
        self.models = {}
        self.feature_engineer = FeatureEngineer()
    
    def load_theory_data(self):
        """加载基于理论的案例数据"""
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'theory_cases.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            cases = json.load(f)
        return cases
    
    def prepare_data(self, cases):
        """准备训练数据"""
        X = []
        y_fortune = []
        y_type = []
        y_time = []
        
        for case in cases:
            features = self.feature_engineer.extract_enhanced_features(case, include_question_type=False)
            X.append(features)
            
            # 吉凶标签
            y_fortune.append(self.FORTUNE_LEVELS.index(
                case['expert_interpretation']['fortune_level']
            ))
            
            # 问事类型标签
            y_type.append(self.QUESTION_TYPES.index(case['question_type']))
            
            # 时间窗口标签（转换为3分类）
            time_window = case['expert_interpretation'].get('time_window', '中期（一月内）')
            time_mapping = {
                '近期（3日内）': 0, '短期（一周内）': 0,
                '中期（一月内）': 1, '长期（三月内）': 1,
                '远期（半年内）': 2
            }
            y_time.append(time_mapping.get(time_window, 1))
        
        return np.array(X), np.array(y_fortune), np.array(y_type), np.array(y_time)
    
    def train(self, test_size=0.2, random_state=42):
        """训练模型"""
        cases = self.load_theory_data()
        print(f"加载案例数: {len(cases)}")
        
        X, y_fortune, y_type, y_time = self.prepare_data(cases)
        print(f"特征维度: {X.shape[1]}")
        
        # 划分数据集
        X_train, X_test, y_fortune_train, y_fortune_test = train_test_split(
            X, y_fortune, test_size=test_size, random_state=random_state, stratify=y_fortune
        )
        X_type_train, X_type_test, y_type_train, y_type_test = train_test_split(
            X, y_type, test_size=test_size, random_state=random_state, stratify=y_type
        )
        X_time_train, X_time_test, y_time_train, y_time_test = train_test_split(
            X, y_time, test_size=test_size, random_state=random_state, stratify=y_time
        )
        
        print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")
        
        results = {}
        
        # 1. 吉凶预测模型
        print("\n=== 吉凶预测模型 ===")
        self.models['fortune'] = GradientBoostingClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42
        )
        self.models['fortune'].fit(X_train, y_fortune_train)
        
        fortune_pred = self.models['fortune'].predict(X_test)
        fortune_acc = accuracy_score(y_fortune_test, fortune_pred)
        print(f"准确率: {fortune_acc:.2%}")
        print(classification_report(y_fortune_test, fortune_pred, target_names=self.FORTUNE_LEVELS))
        results['fortune_accuracy'] = fortune_acc
        
        # 2. 事件类型预测模型
        print("\n=== 事件类型预测模型 ===")
        self.models['type'] = GradientBoostingClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42
        )
        self.models['type'].fit(X_type_train, y_type_train)
        
        type_pred = self.models['type'].predict(X_type_test)
        type_acc = accuracy_score(y_type_test, type_pred)
        print(f"准确率: {type_acc:.2%}")
        print(classification_report(y_type_test, type_pred, target_names=self.QUESTION_TYPES))
        results['type_accuracy'] = type_acc
        
        # 3. 时间窗口预测模型
        print("\n=== 时间窗口预测模型 ===")
        self.models['time'] = GradientBoostingClassifier(
            n_estimators=150, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42
        )
        self.models['time'].fit(X_time_train, y_time_train)
        
        time_pred = self.models['time'].predict(X_time_test)
        time_acc = accuracy_score(y_time_test, time_pred)
        print(f"准确率: {time_acc:.2%}")
        # 动态确定类别名称
        unique_labels = sorted(np.unique(y_time_test))
        target_names = [self.TIME_WINDOWS_3[i] for i in unique_labels]
        print(classification_report(y_time_test, time_pred, target_names=target_names))
        results['time_accuracy'] = time_acc
        
        # 保存模型
        self.save_model()
        
        return results
    
    def cross_validate(self, cv=5):
        """交叉验证"""
        cases = self.load_theory_data()
        X, y_fortune, y_type, y_time = self.prepare_data(cases)
        
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        
        print(f"\n=== {cv}折交叉验证 ===")
        
        # 吉凶预测
        print("\n吉凶预测:")
        model = GradientBoostingClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42)
        scores = cross_val_score(model, X, y_fortune, cv=skf, scoring='accuracy')
        print(f"  准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
        
        # 事件类型预测
        print("\n事件类型预测:")
        model = GradientBoostingClassifier(n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42)
        scores = cross_val_score(model, X, y_type, cv=skf, scoring='accuracy')
        print(f"  准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
        
        # 时间窗口预测
        print("\n时间窗口预测:")
        model = GradientBoostingClassifier(n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42)
        scores = cross_val_score(model, X, y_time, cv=skf, scoring='accuracy')
        print(f"  准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
    
    def save_model(self):
        """保存模型"""
        with open(self.model_path, 'wb') as f:
            pickle.dump({'models': self.models}, f)
        print(f"\n模型已保存至: {self.model_path}")


def main():
    predictor = TheoryBasedPredictor()
    
    # 交叉验证
    predictor.cross_validate()
    
    # 训练模型
    print("\n" + "="*50)
    results = predictor.train()
    
    print("\n" + "="*50)
    print("训练完成!")
    print(f"吉凶预测准确率: {results['fortune_accuracy']:.2%}")
    print(f"事件类型预测准确率: {results['type_accuracy']:.2%}")
    print(f"时间窗口预测准确率: {results['time_accuracy']:.2%}")


if __name__ == '__main__':
    main()
