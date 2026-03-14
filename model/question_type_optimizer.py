"""
问事类型预测优化模块
基于用神类型和卦象特征预测问事类型
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.feature_engineer import FeatureEngineer

# 用神类型与问事类型的对应关系
DEITY_QUESTION_MAPPING = {
    '妻财': ['财运'],
    '官鬼': ['事业', '健康', '诉讼'],
    '父母': ['事业', '健康'],
    '子孙': ['健康', '诉讼'],
    '兄弟': ['财运', '事业'],
}

# 卦象与问事类型的关联权重（基于传统六爻理论）
HEXAGRAM_QUESTION_WEIGHTS = {
    # 财运相关卦
    '财运': {
        '大有': 3, '小畜': 3, '丰': 3, '泰': 2, '比': 2, '同人': 2,
        '损': -3, '困': -3, '剥': -3, '蹇': -2, '坎': -2,
    },
    # 事业相关卦
    '事业': {
        '乾': 3, '升': 3, '晋': 3, '鼎': 2, '革': 2, '履': 2,
        '遁': -2, '否': -3, '明夷': -3, '困': -2, '蛊': -2,
    },
    # 婚姻相关卦
    '婚姻': {
        '咸': 3, '恒': 3, '家人': 3, '泰': 2, '益': 2, '渐': 2,
        '姤': -3, '归妹': -2, '睽': -2, '革': -2, '小畜': 2,
    },
    # 健康相关卦
    '健康': {
        '颐': 3, '复': 3, '泰': 2, '既济': 2, '豫': 2, '解': 2,
        '坎': -3, '明夷': -3, '蛊': -3, '讼': -2, '师': -2,
    },
    # 诉讼相关卦
    '诉讼': {
        '讼': 3, '师': 2, '夬': 2, '履': 2, '比': 2, '同人': 2,
        '大有': 2, '困': -2, '坎': -2, '明夷': -2,
    },
}


class QuestionTypeFeatureExtractor:
    """问事类型特征提取器"""
    
    QUESTION_TYPES = ['财运', '事业', '婚姻', '健康', '诉讼']
    DEITY_TYPES = ['妻财', '官鬼', '父母', '子孙', '兄弟']
    
    def __init__(self):
        self.base_engineer = FeatureEngineer()
    
    def extract_features(self, case: Dict) -> np.ndarray:
        """提取问事类型预测特征"""
        features = []
        
        # 1. 基础特征（不含问事类型）
        base_features = self.base_engineer.extract_enhanced_features(case, include_question_type=False)
        features.extend(base_features)
        
        # 2. 用神类型 one-hot (5维)
        deity_type = case['analysis']['deity_type']
        deity_onehot = [1 if d == deity_type else 0 for d in self.DEITY_TYPES]
        features.extend(deity_onehot)
        
        # 3. 用神五行 (5维)
        deity_element = case['analysis']['deity_element']
        elements = ['金', '木', '水', '火', '土']
        element_onehot = [1 if e == deity_element else 0 for e in elements]
        features.extend(element_onehot)
        
        # 4. 卦象-问事类型关联特征 (5维)
        hexagram_name = case['hexagram']['name']
        for qtype in self.QUESTION_TYPES:
            weights = HEXAGRAM_QUESTION_WEIGHTS.get(qtype, {})
            score = 0
            for key, weight in weights.items():
                if key in hexagram_name:
                    score = weight
                    break
            # 归一化到0-1
            features.append((score + 3) / 6.0)
        
        # 5. 世爻位置与用神关系 (1维)
        shi_pos = case['analysis']['shi_position']
        moving_lines = case['hexagram']['moving_lines']
        shi_is_moving = 1 if shi_pos in moving_lines else 0
        features.append(shi_is_moving)
        
        # 6. 应爻位置与用神关系 (1维)
        ying_pos = case['analysis']['ying_position']
        ying_is_moving = 1 if ying_pos in moving_lines else 0
        features.append(ying_is_moving)
        
        # 7. 动爻数量与用神关系 (1维)
        num_moving = len(moving_lines)
        features.append(num_moving / 6.0)
        
        # 8. 卦象五行与用神五行关系 (4维 one-hot)
        upper_trigram = case['hexagram']['upper_trigram']
        lower_trigram = case['hexagram']['lower_trigram']
        
        from liuyao.engine import TRIGRAMS
        upper_element = TRIGRAMS[upper_trigram]['element']
        lower_element = TRIGRAMS[lower_trigram]['element']
        
        # 计算与用神五行的关系
        element_cycle = {
            '金': {'生': '水', '克': '木'},
            '木': {'生': '火', '克': '土'},
            '水': {'生': '木', '克': '火'},
            '火': {'生': '土', '克': '金'},
            '土': {'生': '金', '克': '水'},
        }
        
        # 上卦与用神的关系
        if upper_element == deity_element:
            upper_relation = '比和'
        elif element_cycle[upper_element]['生'] == deity_element:
            upper_relation = '生'
        elif element_cycle[upper_element]['克'] == deity_element:
            upper_relation = '克'
        elif element_cycle[deity_element]['生'] == upper_element:
            upper_relation = '被生'
        else:
            upper_relation = '被克'
        
        relation_onehot = [1 if r == upper_relation else 0 for r in ['生', '被生', '克', '被克', '比和']]
        features.extend(relation_onehot)
        
        return np.array(features, dtype=np.float32)
    
    def get_feature_names(self) -> List[str]:
        """获取特征名称"""
        base_names = self.base_engineer.get_feature_names()
        names = list(base_names)
        
        names.extend([f'deity_{d}' for d in self.DEITY_TYPES])
        names.extend([f'deity_elem_{e}' for e in ['金', '木', '水', '火', '土']])
        names.extend([f'hex_qtype_{q}' for q in self.QUESTION_TYPES])
        names.extend(['shi_moving', 'ying_moving', 'num_moving'])
        names.extend([f'upper_deity_relation_{r}' for r in ['生', '被生', '克', '被克', '比和']])
        
        return names


def analyze_question_type_patterns():
    """分析问事类型的模式"""
    # 加载数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'theory_cases.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    print("=== 问事类型与用神类型的关系 ===")
    
    # 统计每种问事类型的用神分布
    question_deity = {}
    for c in cases:
        qtype = c['question_type']
        deity = c['analysis']['deity_type']
        if qtype not in question_deity:
            question_deity[qtype] = []
        question_deity[qtype].append(deity)
    
    for qtype in ['财运', '事业', '婚姻', '健康', '诉讼']:
        deities = question_deity[qtype]
        deity_dist = Counter(deities)
        print(f'\n{qtype}:')
        for deity in ['妻财', '官鬼', '父母', '子孙', '兄弟']:
            count = deity_dist.get(deity, 0)
            print(f'  {deity}: {count/len(deities)*100:.1f}%')
    
    print("\n=== 用神类型与问事类型的对应关系 ===")
    
    # 统计每种用神对应的问事类型
    deity_questions = {}
    for c in cases:
        deity = c['analysis']['deity_type']
        qtype = c['question_type']
        if deity not in deity_questions:
            deity_questions[deity] = []
        deity_questions[deity].append(qtype)
    
    for deity in ['妻财', '官鬼', '父母', '子孙', '兄弟']:
        questions = deity_questions.get(deity, [])
        if not questions:
            print(f'\n{deity}: 无数据')
            continue
        question_dist = Counter(questions)
        print(f'\n{deity}:')
        for qtype in ['财运', '事业', '婚姻', '健康', '诉讼']:
            count = question_dist.get(qtype, 0)
            print(f'  {qtype}: {count/len(questions)*100:.1f}%')


def train_question_type_model():
    """训练问事类型预测模型"""
    from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import accuracy_score, classification_report
    import pickle
    
    # 加载数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'theory_cases.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    print(f"加载案例数: {len(cases)}")
    
    # 提取特征
    extractor = QuestionTypeFeatureExtractor()
    X = []
    y = []
    
    for case in cases:
        features = extractor.extract_features(case)
        X.append(features)
        y.append(extractor.QUESTION_TYPES.index(case['question_type']))
    
    X = np.array(X)
    y = np.array(y)
    
    print(f"特征维度: {X.shape[1]}")
    
    # 交叉验证
    print("\n=== 5折交叉验证 ===")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    model = GradientBoostingClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42
    )
    scores = cross_val_score(model, X, y, cv=skf, scoring='accuracy')
    print(f"准确率: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")
    print(f"各折: {[f'{s:.2%}' for s in scores]}")
    
    # 训练模型
    print("\n=== 训练模型 ===")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"测试集准确率: {accuracy:.2%}")
    print("\n分类报告:")
    print(classification_report(y_test, y_pred, target_names=extractor.QUESTION_TYPES))
    
    # 特征重要性
    feature_names = extractor.get_feature_names()
    importance = model.feature_importances_
    top_indices = np.argsort(importance)[::-1][:10]
    
    print("\nTop 10 重要特征:")
    for idx in top_indices:
        print(f"  {feature_names[idx]}: {importance[idx]:.4f}")
    
    # 保存模型
    model_path = os.path.join(os.path.dirname(__file__), 'question_type_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({'model': model, 'extractor': extractor}, f)
    print(f"\n模型已保存至: {model_path}")
    
    return accuracy


if __name__ == '__main__':
    print("分析问事类型模式...")
    analyze_question_type_patterns()
    
    print("\n" + "="*50)
    print("训练问事类型预测模型...")
    train_question_type_model()
