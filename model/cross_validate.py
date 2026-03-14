#!/usr/bin/env python3
"""
交叉验证评估模型性能
"""
import json
import os
import sys
import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.gbm_predictor import GBMHexagramPredictor

def cross_validate_model():
    """执行交叉验证"""
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

    # 准备数据
    predictor = GBMHexagramPredictor()
    data = predictor.prepare_data(cases)
    X_fortune, y_fortune = data['fortune']
    X_type, y_type = data['type']
    X_type_clean, _ = data['type_clean']
    X_time, y_time = data['time']

    # 使用分层K折交叉验证
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    from sklearn.ensemble import GradientBoostingClassifier

    # 交叉验证 - 吉凶预测
    print("\n=== 吉凶预测交叉验证（特征维度: {}）===".format(X_fortune.shape[1]))
    fortune_model = GradientBoostingClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
    )
    scores = cross_val_score(fortune_model, X_fortune, y_fortune, cv=cv, scoring='accuracy')
    print(f"5折交叉验证准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
    print(f"各折准确率: {[f'{s:.2%}' for s in scores]}")

    # 交叉验证 - 事件类型预测（含问事类型特征 - 有泄露）
    print("\n=== 事件类型预测交叉验证（含问事类型特征 - 有泄露）===")
    type_model_leak = GradientBoostingClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
    )
    scores = cross_val_score(type_model_leak, X_type, y_type, cv=cv, scoring='accuracy')
    print(f"5折交叉验证准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
    print(f"各折准确率: {[f'{s:.2%}' for s in scores]}")
    
    # 交叉验证 - 事件类型预测（不含问事类型特征 - 正确）
    print("\n=== 事件类型预测交叉验证（不含问事类型特征 - 正确）===")
    type_model_clean = GradientBoostingClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
    )
    scores = cross_val_score(type_model_clean, X_type_clean, y_type, cv=cv, scoring='accuracy')
    print(f"5折交叉验证准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
    print(f"各折准确率: {[f'{s:.2%}' for s in scores]}")

    # 交叉验证 - 时间窗口预测（3分类）
    print("\n=== 时间窗口预测交叉验证（3分类：近期/中期/远期）===")
    # 转换为3分类
    y_time_3 = predictor._convert_to_3class(y_time)
    time_model = GradientBoostingClassifier(
        n_estimators=150, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42
    )
    scores = cross_val_score(time_model, X_time, y_time_3, cv=cv, scoring='accuracy')
    print(f"5折交叉验证准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
    print(f"各折准确率: {[f'{s:.2%}' for s in scores]}")

    print("\n=== 特征维度统计 ===")
    print(f"吉凶预测特征数: {X_fortune.shape[1]} (不含问事类型)")
    print(f"事件类型预测特征数: {X_type.shape[1]} (含问事类型)")
    print(f"事件类型预测特征数(正确): {X_type_clean.shape[1]} (不含问事类型)")
    print(f"时间窗口预测特征数: {X_time.shape[1]} (不含问事类型)")
    print("\n特征构成:")
    print("  - 时间特征: 4维")
    print("  - 问事类型 one-hot: 5维 (仅事件类型预测含泄露版本)")
    print("  - 六爻特征: 6维")
    print("  - 动爻 one-hot: 6维")
    print("  - 上下卦 one-hot: 16维")
    print("  - 世应位置: 2维")
    print("  - 五行关系 one-hot: 5维")
    print("  - 动爻数量: 1维")
    print("  - 是否有动爻: 1维")
    print("  - 六冲/六合/游魂/归魂: 4维")
    print("  - 特殊格局 one-hot: 5维")

if __name__ == '__main__':
    cross_validate_model()
