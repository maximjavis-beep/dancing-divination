"""
整合优化版预测器
结合所有优化：特征工程、理论案例、问事类型优化
"""

import json
import os
import sys
import numpy as np
from typing import Dict
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.feature_engineer import FeatureEngineer
from model.question_type_optimizer import QuestionTypeFeatureExtractor

class OptimizedPredictor:
    """优化版预测器 - 整合所有改进"""
    
    FORTUNE_LEVELS = ['大凶', '凶', '平', '吉', '大吉']
    QUESTION_TYPES = ['财运', '事业', '婚姻', '健康', '诉讼']
    TIME_WINDOWS_3 = ['近期', '中期', '远期']
    
    def __init__(self, model_path=None):
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 'optimized_model.pkl'
        )
        self.models = {}
        self.fortune_engineer = FeatureEngineer()
        self.question_extractor = QuestionTypeFeatureExtractor()
    
    def load_data(self):
        """加载理论案例数据"""
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'theory_cases.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            cases = json.load(f)
        return cases
    
    def prepare_fortune_data(self, cases):
        """准备吉凶预测数据"""
        X = []
        y = []
        for case in cases:
            features = self.fortune_engineer.extract_enhanced_features(case, include_question_type=False)
            X.append(features)
            y.append(self.FORTUNE_LEVELS.index(case['expert_interpretation']['fortune_level']))
        return np.array(X), np.array(y)
    
    def prepare_question_type_data(self, cases):
        """准备问事类型预测数据"""
        X = []
        y = []
        for case in cases:
            features = self.question_extractor.extract_features(case)
            X.append(features)
            y.append(self.QUESTION_TYPES.index(case['question_type']))
        return np.array(X), np.array(y)
    
    def prepare_time_data(self, cases):
        """准备时间窗口预测数据"""
        X = []
        y = []
        for case in cases:
            features = self.fortune_engineer.extract_enhanced_features(case, include_question_type=False)
            X.append(features)
            
            time_window = case['expert_interpretation'].get('time_window', '中期（一月内）')
            time_mapping = {
                '近期（3日内）': 0, '短期（一周内）': 0,
                '中期（一月内）': 1, '长期（三月内）': 1,
                '远期（半年内）': 2
            }
            y.append(time_mapping.get(time_window, 1))
        
        return np.array(X), np.array(y)
    
    def train(self, test_size=0.2, random_state=42):
        """训练所有模型"""
        cases = self.load_data()
        print(f"加载案例数: {len(cases)}")
        
        results = {}
        
        # 1. 吉凶预测模型
        print("\n" + "="*50)
        print("=== 吉凶预测模型 ===")
        X, y = self.prepare_fortune_data(cases)
        print(f"特征维度: {X.shape[1]}")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        self.models['fortune'] = GradientBoostingClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42
        )
        self.models['fortune'].fit(X_train, y_train)
        
        y_pred = self.models['fortune'].predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"准确率: {acc:.2%}")
        print(classification_report(y_test, y_pred, target_names=self.FORTUNE_LEVELS))
        results['fortune'] = acc
        
        # 2. 问事类型预测模型
        print("\n" + "="*50)
        print("=== 问事类型预测模型 ===")
        X, y = self.prepare_question_type_data(cases)
        print(f"特征维度: {X.shape[1]}")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        self.models['question_type'] = GradientBoostingClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42
        )
        self.models['question_type'].fit(X_train, y_train)
        
        y_pred = self.models['question_type'].predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"准确率: {acc:.2%}")
        print(classification_report(y_test, y_pred, target_names=self.QUESTION_TYPES))
        results['question_type'] = acc
        
        # 3. 时间窗口预测模型
        print("\n" + "="*50)
        print("=== 时间窗口预测模型 ===")
        X, y = self.prepare_time_data(cases)
        print(f"特征维度: {X.shape[1]}")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        self.models['time'] = GradientBoostingClassifier(
            n_estimators=150, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42
        )
        self.models['time'].fit(X_train, y_train)
        
        y_pred = self.models['time'].predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"准确率: {acc:.2%}")
        # 动态确定类别
        unique_labels = sorted(np.unique(y_test))
        target_names = [self.TIME_WINDOWS_3[i] for i in unique_labels]
        print(classification_report(y_test, y_pred, target_names=target_names))
        results['time'] = acc
        
        # 保存模型
        self.save_model()
        
        return results
    
    def cross_validate(self, cv=5):
        """交叉验证"""
        cases = self.load_data()
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        
        print(f"\n=== {cv}折交叉验证 ===")
        
        # 吉凶预测
        X, y = self.prepare_fortune_data(cases)
        model = GradientBoostingClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42)
        scores = cross_val_score(model, X, y, cv=skf, scoring='accuracy')
        print(f"\n吉凶预测: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
        
        # 问事类型预测
        X, y = self.prepare_question_type_data(cases)
        model = GradientBoostingClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42)
        scores = cross_val_score(model, X, y, cv=skf, scoring='accuracy')
        print(f"问事类型预测: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
        
        # 时间窗口预测
        X, y = self.prepare_time_data(cases)
        model = GradientBoostingClassifier(n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42)
        scores = cross_val_score(model, X, y, cv=skf, scoring='accuracy')
        print(f"时间窗口预测: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
    
    def predict(self, case: Dict) -> Dict:
        """预测"""
        if not self.models:
            self.load_model()
        
        # 吉凶预测
        fortune_features = self.fortune_engineer.extract_enhanced_features(case, include_question_type=False)
        fortune_probs = self.models['fortune'].predict_proba(fortune_features.reshape(1, -1))[0]
        fortune_pred = np.argmax(fortune_probs)
        
        # 问事类型预测
        question_features = self.question_extractor.extract_features(case)
        question_probs = self.models['question_type'].predict_proba(question_features.reshape(1, -1))[0]
        question_pred = np.argmax(question_probs)
        
        # 时间窗口预测
        time_features = self.fortune_engineer.extract_enhanced_features(case, include_question_type=False)
        time_probs = self.models['time'].predict_proba(time_features.reshape(1, -1))[0]
        time_pred = np.argmax(time_probs)
        
        return {
            'fortune_level': self.FORTUNE_LEVELS[fortune_pred],
            'fortune_probabilities': {
                level: float(fortune_probs[i])
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
            'question_type': self.QUESTION_TYPES[question_pred],
            'question_type_probabilities': {
                t: float(question_probs[i])
                for i, t in enumerate(self.QUESTION_TYPES)
            },
            'time_window': self.TIME_WINDOWS_3[time_pred],
            'time_probabilities': {
                t: float(time_probs[i])
                for i, t in enumerate(self.TIME_WINDOWS_3)
            },
        }
    
    def save_model(self):
        """保存模型"""
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'fortune_engineer': self.fortune_engineer,
                'question_extractor': self.question_extractor,
            }, f)
        print(f"\n模型已保存至: {self.model_path}")
    
    def load_model(self):
        """加载模型"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.models = data['models']
                self.fortune_engineer = data.get('fortune_engineer', FeatureEngineer())
                self.question_extractor = data.get('question_extractor', QuestionTypeFeatureExtractor())
            print(f"模型已加载: {self.model_path}")
        else:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")


def main():
    predictor = OptimizedPredictor()
    
    # 交叉验证
    predictor.cross_validate()
    
    # 训练
    print("\n" + "="*60)
    print("训练优化版预测器")
    print("="*60)
    results = predictor.train()
    
    print("\n" + "="*60)
    print("训练完成！")
    print(f"吉凶预测准确率: {results['fortune']:.2%}")
    print(f"问事类型预测准确率: {results['question_type']:.2%}")
    print(f"时间窗口预测准确率: {results['time']:.2%}")
    print("="*60)


if __name__ == '__main__':
    main()
