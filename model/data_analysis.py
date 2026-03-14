#!/usr/bin/env python3
"""
数据分析诊断脚本
分析案例数据的特征和标签分布
"""

import json
import os
import sys
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.feature_engineer import FeatureEngineer

def analyze_data():
    """分析数据分布"""
    # 加载数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    gudian_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gudian_cases.json')
    if os.path.exists(gudian_path):
        with open(gudian_path, 'r', encoding='utf-8') as f:
            gudian_cases = json.load(f)
        cases.extend(gudian_cases)
    
    print(f"总案例数: {len(cases)}")
    
    # 1. 分析吉凶分布
    print("\n=== 吉凶分布 ===")
    fortune_dist = Counter(c['expert_interpretation']['fortune_level'] for c in cases)
    for level in ['大吉', '吉', '平', '凶', '大凶']:
        count = fortune_dist.get(level, 0)
        print(f"  {level}: {count} ({count/len(cases)*100:.1f}%)")
    
    # 2. 分析问事类型分布
    print("\n=== 问事类型分布 ===")
    type_dist = Counter(c['question_type'] for c in cases)
    for qtype in ['财运', '事业', '爱情', '健康', '诉讼']:
        count = type_dist.get(qtype, 0)
        print(f"  {qtype}: {count} ({count/len(cases)*100:.1f}%)")
    
    # 3. 分析时间窗口分布
    print("\n=== 时间窗口分布 ===")
    time_dist = Counter(c['expert_interpretation'].get('time_window', '中期（一月内）') for c in cases)
    for window in ['近期（3日内）', '短期（一周内）', '中期（一月内）', '长期（三月内）', '远期（半年内）']:
        count = time_dist.get(window, 0)
        print(f"  {window}: {count} ({count/len(cases)*100:.1f}%)")
    
    # 4. 分析卦象分布
    print("\n=== 卦象分布（Top 10）===")
    hexagram_dist = Counter(c['hexagram']['name'] for c in cases)
    for name, count in hexagram_dist.most_common(10):
        print(f"  {name}: {count}")
    
    # 5. 分析动爻分布
    print("\n=== 动爻数量分布 ===")
    moving_dist = Counter(len(c['hexagram']['moving_lines']) for c in cases)
    for num, count in sorted(moving_dist.items()):
        print(f"  {num}个动爻: {count} ({count/len(cases)*100:.1f}%)")
    
    # 6. 分析特征与标签的相关性
    print("\n=== 特征-标签相关性分析 ===")
    engineer = FeatureEngineer()
    
    # 提取所有特征
    X = []
    y_fortune = []
    for case in cases:
        features = engineer.extract_enhanced_features(case, include_question_type=False)
        X.append(features)
        fortune_levels = ['大凶', '凶', '平', '吉', '大吉']
        y_fortune.append(fortune_levels.index(case['expert_interpretation']['fortune_level']))
    
    X = np.array(X)
    y_fortune = np.array(y_fortune)
    
    # 计算每个特征与标签的相关系数
    feature_names = engineer.get_feature_names()
    correlations = []
    for i in range(X.shape[1]):
        corr = np.corrcoef(X[:, i], y_fortune)[0, 1]
        if not np.isnan(corr):
            correlations.append((feature_names[i], abs(corr), corr))
    
    correlations.sort(key=lambda x: x[1], reverse=True)
    
    print("\n与吉凶相关性最强的Top 10特征:")
    for name, abs_corr, corr in correlations[:10]:
        print(f"  {name}: {corr:+.4f} (绝对值: {abs_corr:.4f})")
    
    # 7. 检查数据是否随机
    print("\n=== 数据随机性检查 ===")
    # 检查相同卦象的不同吉凶
    hexagram_fortunes = {}
    for case in cases:
        name = case['hexagram']['name']
        fortune = case['expert_interpretation']['fortune_level']
        if name not in hexagram_fortunes:
            hexagram_fortunes[name] = []
        hexagram_fortunes[name].append(fortune)
    
    # 统计同一卦象有多少种不同吉凶
    multi_fortune_count = sum(1 for fortunes in hexagram_fortunes.values() if len(set(fortunes)) > 1)
    print(f"同一卦象有不同吉凶解读的数量: {multi_fortune_count}/{len(hexagram_fortunes)}")
    
    # 举例
    print("\n示例（同一卦象不同吉凶）:")
    for name, fortunes in list(hexagram_fortunes.items())[:3]:
        if len(set(fortunes)) > 1:
            fortune_counts = Counter(fortunes)
            print(f"  {name}: {dict(fortune_counts)}")


if __name__ == '__main__':
    analyze_data()
