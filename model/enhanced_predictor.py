"""
增强版GBM预测器
使用更丰富的特征工程
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.feature_engineer import FeatureEngineer

class EnhancedPredictor:
    """增强版预测器"""
    
    FORTUNE_LEVELS = ['大凶', '凶', '平', '吉', '大吉']
    QUESTION_TYPES = ['财运', '事业', '婚姻', '健康', '诉讼']
    TIME_WINDOWS_3 = ['近期', '中期', '远期']
    
    def __init__(self, model_path=None):
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 'enhanced_model.pkl'
        )
        self.models = {}
        self.feature_engineer = FeatureEngineer()
    
    def prepare_data(self, cases: List[Dict]):
        """准备训练数据"""
        X_fortune = []
        X_type = []
        X_time = []
        
        y_fortune = []
        y_type = []
        y_time = []
        
        for case in cases:
            # 提取特征
            features = self.feature_engineer.extract_enhanced_features(case, include_question_type=False)
            X_fortune.append(features)
            X_type.append(features)
            X_time.append(features)
            
            # 标签编码
            y_fortune.append(self.FORTUNE_LEVELS.index(
                case['expert_interpretation']['fortune_level']
            ))
            y_type.append(self.QUESTION_TYPES.index(case['question_type']))
            
            # 时间窗口转换为3分类
            time_window = case['expert_interpretation'].get('time_window', '中期（一月内）')
            time_mapping = {
                '近期（3日内）': 0, '短期（一周内）': 0,
                '中期（一月内）': 1, '长期（三月内）': 1,
                '远期（半年内）': 2
            }
            y_time.append(time_mapping.get(time_window, 1))
        
        return {
            'fortune': (np.array(X_fortune), np.array(y_fortune)),
            'type': (np.array(X_type), np.array(y_type)),
            'time': (np.array(X_time), np.array(y_time)),
        }
    
    def train(self, cases, test_size=0.2, random_state=42):
        """训练模型"""
        print(f"准备数据: {len(cases)} 个案例")
        
        data = self.prepare_data(cases)
        X_fortune, y_fortune = data['fortune']
        X_type, y_type = data['type']
        X_time, y_time = data['time']
        
        print(f"特征维度: {X_fortune.shape[1]}")
        
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
        
        # 1. 训练吉凶预测模型
        print("\n=== 吉凶预测模型 ===")
        # 使用类别权重处理不平衡
        from sklearn.utils.class_weight import compute_class_weight
        classes = np.unique(y_fortune_train)
        class_weights = compute_class_weight('balanced', classes=classes, y=y_fortune_train)
        class_weight_dict = {c: w for c, w in zip(classes, class_weights)}
        
        self.models['fortune'] = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        
        # 使用样本权重
        sample_weights = np.array([class_weight_dict[y] for y in y_fortune_train])
        self.models['fortune'].fit(X_fortune_train, y_fortune_train, sample_weight=sample_weights)
        
        fortune_pred = self.models['fortune'].predict(X_fortune_test)
        fortune_acc = accuracy_score(y_fortune_test, fortune_pred)
        print(f"准确率: {fortune_acc:.2%}")
        print("\n分类报告:")
        print(classification_report(y_fortune_test, fortune_pred, target_names=self.FORTUNE_LEVELS))
        results['fortune_accuracy'] = fortune_acc
        
        # 2. 训练事件类型预测模型
        print("\n=== 事件类型预测模型 ===")
        self.models['type'] = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.models['type'].fit(X_type_train, y_type_train)
        
        type_pred = self.models['type'].predict(X_type_test)
        type_acc = accuracy_score(y_type_test, type_pred)
        print(f"准确率: {type_acc:.2%}")
        print("\n分类报告:")
        print(classification_report(y_type_test, type_pred, target_names=self.QUESTION_TYPES))
        results['type_accuracy'] = type_acc
        
        # 3. 训练时间窗口预测模型
        print("\n=== 时间窗口预测模型 ===")
        self.models['time'] = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        self.models['time'].fit(X_time_train, y_time_train)
        
        time_pred = self.models['time'].predict(X_time_test)
        time_acc = accuracy_score(y_time_test, time_pred)
        print(f"准确率: {time_acc:.2%}")
        print("\n分类报告:")
        print(classification_report(y_time_test, time_pred, target_names=self.TIME_WINDOWS_3))
        results['time_accuracy'] = time_acc
        
        # 保存模型
        self.save_model()
        
        return results
    
    def cross_validate(self, cases, cv=5):
        """交叉验证"""
        print(f"\n=== {cv}折交叉验证 ===")
        
        data = self.prepare_data(cases)
        X_fortune, y_fortune = data['fortune']
        X_type, y_type = data['type']
        X_time, y_time = data['time']
        
        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        
        # 吉凶预测交叉验证
        print("\n吉凶预测:")
        model = GradientBoostingClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42)
        scores = cross_val_score(model, X_fortune, y_fortune, cv=skf, scoring='accuracy')
        print(f"  准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
        print(f"  各折: {[f'{s:.2%}' for s in scores]}")
        
        # 事件类型预测交叉验证
        print("\n事件类型预测:")
        model = GradientBoostingClassifier(n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42)
        scores = cross_val_score(model, X_type, y_type, cv=skf, scoring='accuracy')
        print(f"  准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
        print(f"  各折: {[f'{s:.2%}' for s in scores]}")
        
        # 时间窗口预测交叉验证
        print("\n时间窗口预测:")
        model = GradientBoostingClassifier(n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42)
        scores = cross_val_score(model, X_time, y_time, cv=skf, scoring='accuracy')
        print(f"  准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
        print(f"  各折: {[f'{s:.2%}' for s in scores]}")
    
    def predict(self, case: Dict) -> Dict:
        """预测"""
        if not self.models:
            self.load_model()
        
        features = self.feature_engineer.extract_enhanced_features(case, include_question_type=False)
        features = features.reshape(1, -1)
        
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
                level: float(fortune_probs[i])
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
            'question_type': self.QUESTION_TYPES[type_pred],
            'type_probabilities': {
                t: float(type_probs[i])
                for i, t in enumerate(self.QUESTION_TYPES)
            },
            'time_window': self.TIME_WINDOWS_3[time_pred],
            'time_probabilities': {
                t: float(time_probs[i])
                for i, t in enumerate(self.TIME_WINDOWS_3)
            },
        }
    
    def get_feature_importance(self) -> Dict:
        """获取特征重要性"""
        if not self.models:
            self.load_model()
        
        feature_names = self.feature_engineer.get_feature_names()
        importance = {}
        
        for task, model in self.models.items():
            scores = model.feature_importances_
            importance[task] = sorted(
                [(name, float(score)) for name, score in zip(feature_names, scores)],
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10
        
        return importance
    
    def save_model(self):
        """保存模型"""
        with open(self.model_path, 'wb') as f:
            pickle.dump({'models': self.models}, f)
        print(f"\n模型已保存至: {self.model_path}")
    
    def load_model(self):
        """加载模型"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.models = data['models']
            print(f"模型已加载: {self.model_path}")
        else:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")


def main():
    """主函数"""
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
        print(f"总案例数: {len(cases)}")
    
    # 创建预测器
    predictor = EnhancedPredictor()
    
    # 交叉验证
    predictor.cross_validate(cases)
    
    # 训练模型
    print("\n" + "="*50)
    results = predictor.train(cases)
    
    print("\n" + "="*50)
    print("训练完成!")
    print(f"吉凶预测准确率: {results['fortune_accuracy']:.2%}")
    print(f"事件类型预测准确率: {results['type_accuracy']:.2%}")
    print(f"时间窗口预测准确率: {results['time_accuracy']:.2%}")
    
    # 特征重要性
    importance = predictor.get_feature_importance()
    print("\n吉凶预测 Top 5 重要特征:")
    for name, score in importance['fortune'][:5]:
        print(f"  {name}: {score:.4f}")


if __name__ == '__main__':
    main()
