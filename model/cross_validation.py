"""
交叉验证评估脚本
用古籍案例作为专家验证集
"""

import json
import os
import sys
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.gbm_predictor import GBMHexagramPredictor

def load_data():
    """加载数据"""
    # 模拟案例
    cases_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    with open(cases_path, 'r', encoding='utf-8') as f:
        mock_cases = json.load(f)
    
    # 古籍案例
    gudian_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gudian_cases.json')
    with open(gudian_path, 'r', encoding='utf-8') as f:
        gudian_cases = json.load(f)
    
    return mock_cases, gudian_cases

def cross_validation_evaluation():
    """交叉验证评估"""
    mock_cases, gudian_cases = load_data()
    
    print("=" * 60)
    print("六爻预测模型交叉验证评估")
    print("=" * 60)
    
    # 划分模拟案例：训练集400，验证集50，测试集50
    train_cases, temp_cases = train_test_split(mock_cases, test_size=100, random_state=42)
    val_cases, mock_test_cases = train_test_split(temp_cases, test_size=50, random_state=42)
    
    print(f"\n数据集划分:")
    print(f"  训练集（模拟案例）: {len(train_cases)} 个")
    print(f"  验证集（模拟案例）: {len(val_cases)} 个")
    print(f"  测试集A（模拟案例）: {len(mock_test_cases)} 个")
    print(f"  测试集B（古籍案例）: {len(gudian_cases)} 个")
    
    # 合并训练集和验证集
    train_val_cases = train_cases + val_cases
    
    # 训练模型
    print(f"\n训练模型...")
    model = GBMHexagramPredictor()
    model.train(train_val_cases)
    
    # 在测试集A上评估
    print("\n" + "=" * 60)
    print("测试集A评估（模拟案例）")
    print("=" * 60)
    mock_results = evaluate_on_dataset(model, mock_test_cases, "模拟案例")
    
    # 在测试集B上评估
    print("\n" + "=" * 60)
    print("测试集B评估（古籍案例 - 专家验证）")
    print("=" * 60)
    gudian_results = evaluate_on_dataset(model, gudian_cases, "古籍案例")
    
    # 对比分析
    print("\n" + "=" * 60)
    print("对比分析")
    print("=" * 60)
    
    print(f"\n吉凶预测准确率:")
    print(f"  模拟案例: {mock_results['fortune_accuracy']:.2%}")
    print(f"  古籍案例: {gudian_results['fortune_accuracy']:.2%}")
    print(f"  差距: {abs(mock_results['fortune_accuracy'] - gudian_results['fortune_accuracy']):.2%}")
    
    print(f"\n事件类型预测准确率:")
    print(f"  模拟案例: {mock_results['type_accuracy']:.2%}")
    print(f"  古籍案例: {gudian_results['type_accuracy']:.2%}")
    
    print(f"\n时间窗口预测准确率:")
    print(f"  模拟案例: {mock_results['time_accuracy']:.2%}")
    print(f"  古籍案例: {gudian_results['time_accuracy']:.2%}")
    
    # 差距分析
    fortune_gap = mock_results['fortune_accuracy'] - gudian_results['fortune_accuracy']
    if fortune_gap > 0.1:
        print(f"\n⚠️ 警告: 模型在古籍案例上表现明显较差（差距{fortune_gap:.2%}）")
        print("   可能原因：")
        print("   1. 模拟数据与真实数据分布不一致")
        print("   2. 模型过拟合到模拟数据的噪声")
        print("   3. 古籍案例的标注更严格/准确")
    else:
        print(f"\n✓ 模型泛化能力良好，古籍案例差距在可接受范围内")
    
    # 特征重要性对比
    print("\n" + "=" * 60)
    print("特征重要性分析（基于训练集）")
    print("=" * 60)
    importance = model.get_feature_importance()
    print("\n吉凶预测 Top 10 重要特征:")
    for i, feat in enumerate(importance['fortune'][:10], 1):
        print(f"  {i:2d}. {feat['feature']}: {feat['importance']:.4f}")
    
    return {
        'mock_results': mock_results,
        'gudian_results': gudian_results,
        'fortune_gap': fortune_gap,
    }

def evaluate_on_dataset(model, cases, dataset_name):
    """在指定数据集上评估"""
    # 准备数据
    X, y_fortune, y_type, y_time = model.prepare_data(cases)
    
    # 预测
    fortune_pred = model.models['fortune'].predict(X)
    type_pred = model.models['type'].predict(X)
    time_pred = model.models['time'].predict(X)
    
    # 计算准确率
    fortune_acc = accuracy_score(y_fortune, fortune_pred)
    type_acc = accuracy_score(y_type, type_pred)
    time_acc = accuracy_score(y_time, time_pred)
    
    print(f"\n{dataset_name} 评估结果:")
    print(f"  吉凶预测准确率: {fortune_acc:.2%}")
    print(f"  事件类型预测准确率: {type_acc:.2%}")
    print(f"  时间窗口预测准确率: {time_acc:.2%}")
    
    # 详细分类报告
    print(f"\n{dataset_name} 吉凶预测分类报告:")
    print(classification_report(
        y_fortune, fortune_pred,
        target_names=model.FORTUNE_LEVELS,
        zero_division=0
    ))
    
    # 混淆矩阵
    print(f"\n{dataset_name} 吉凶预测混淆矩阵:")
    cm = confusion_matrix(y_fortune, fortune_pred)
    print("    ", " ".join(f"{l:>6}" for l in model.FORTUNE_LEVELS))
    for i, row in enumerate(cm):
        print(f"{model.FORTUNE_LEVELS[i]:>6}", " ".join(f"{c:>6}" for c in row))
    
    return {
        'fortune_accuracy': fortune_acc,
        'type_accuracy': type_acc,
        'time_accuracy': time_acc,
    }

def analyze_case_errors(model, cases, dataset_name):
    """分析错误案例"""
    print(f"\n{dataset_name} 错误案例分析:")
    
    X, y_fortune, _, _ = model.prepare_data(cases)
    fortune_pred = model.models['fortune'].predict(X)
    fortune_proba = model.models['fortune'].predict_proba(X)
    
    errors = []
    for i, (case, true_label, pred_label, proba) in enumerate(zip(cases, y_fortune, fortune_pred, fortune_proba)):
        if true_label != pred_label:
            confidence = proba[pred_label]
            errors.append({
                'case_id': case.get('case_id', i),
                'hexagram': case['hexagram']['name'],
                'question_type': case['question_type'],
                'true': model.FORTUNE_LEVELS[true_label],
                'predicted': model.FORTUNE_LEVELS[pred_label],
                'confidence': confidence,
            })
    
    # 按置信度排序
    errors.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"  总错误数: {len(errors)} / {len(cases)} ({len(errors)/len(cases):.1%})")
    print("\n  高置信度错误案例（模型很确定但错了）:")
    for err in errors[:5]:
        print(f"    {err['case_id']}: {err['hexagram']} ({err['question_type']})")
        print(f"      真实: {err['true']}, 预测: {err['predicted']}, 置信度: {err['confidence']:.2%}")
    
    return errors

if __name__ == '__main__':
    results = cross_validation_evaluation()
    
    # 分析错误案例
    mock_cases, gudian_cases = load_data()
    _, temp_cases = train_test_split(mock_cases, test_size=100, random_state=42)
    _, mock_test_cases = train_test_split(temp_cases, test_size=50, random_state=42)
    
    model = GBMHexagramPredictor()
    model.load_model()
    
    print("\n" + "=" * 60)
    analyze_case_errors(model, mock_test_cases, "模拟案例")
    
    print("\n" + "=" * 60)
    analyze_case_errors(model, gudian_cases, "古籍案例")
