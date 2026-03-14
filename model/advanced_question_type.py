"""
问事类型预测进一步优化
通过卦象特征和动爻位置来区分相似类型
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.question_type_optimizer import QuestionTypeFeatureExtractor

# 更精细的卦象-问事类型映射
DETAILED_HEXAGRAM_QUESTION = {
    # 财运专用卦象（与爱情区分）
    '财运': {
        '大有': 3, '小畜': 3, '丰': 3, '同人': 2, '比': 2,
        '损': -3, '困': -3, '剥': -3, '蹇': -2, '坎': -2,
        '需': 1, '既济': 1, '未济': -1,
    },
    # 爱情专用卦象（与财运区分）
    '爱情': {
        '咸': 3, '恒': 3, '家人': 3, '渐': 2, '益': 2,
        '姤': -3, '归妹': -2, '睽': -2, '革': -2,
        '屯': -1, '蒙': 0, '需': 0,
    },
    # 事业专用卦象（与诉讼区分）
    '事业': {
        '乾': 3, '升': 3, '晋': 3, '鼎': 2, '革': 2, '履': 2,
        '遁': -2, '否': -3, '明夷': -3, '困': -2, '蛊': -2,
        '谦': 1, '豫': 1,
    },
    # 诉讼专用卦象（与事业区分）
    '诉讼': {
        '讼': 3, '师': 2, '夬': 2, '履': 1,
        '比': 1, '同人': 1, '大有': 1,
        '困': -2, '坎': -2, '明夷': -2,
    },
    # 健康
    '健康': {
        '颐': 3, '复': 3, '泰': 2, '既济': 2, '豫': 2, '解': 2,
        '坎': -3, '明夷': -3, '蛊': -3, '讼': -2, '师': -2,
    },
}

# 动爻位置与问事类型的关联
MOVING_LINE_QUESTION = {
    '财运': [1, 2],      # 初爻、二爻与财运相关
    '爱情': [3, 4],      # 三爻、四爻与爱情相关
    '事业': [5],         # 五爻与事业相关
    '健康': [2, 3],      # 二爻、三爻与健康相关
    '诉讼': [4, 6],      # 四爻、上爻与诉讼相关
}


class AdvancedQuestionTypeExtractor(QuestionTypeFeatureExtractor):
    """高级问事类型特征提取器"""
    
    def extract_features(self, case: Dict) -> np.ndarray:
        """提取增强版问事类型特征"""
        # 基础特征
        features = list(super().extract_features(case))
        
        hexagram_name = case['hexagram']['name']
        moving_lines = case['hexagram']['moving_lines']
        
        # 1. 精细卦象-问事类型关联 (5维)
        for qtype in self.QUESTION_TYPES:
            weights = DETAILED_HEXAGRAM_QUESTION.get(qtype, {})
            score = 0
            for key, weight in weights.items():
                if key in hexagram_name:
                    score = weight
                    break
            features.append((score + 3) / 6.0)
        
        # 2. 动爻位置与问事类型的匹配度 (5维)
        for qtype in self.QUESTION_TYPES:
            relevant_positions = MOVING_LINE_QUESTION.get(qtype, [])
            if not moving_lines:
                match_score = 0.5  # 无动爻时中性
            else:
                matches = sum(1 for pos in moving_lines if pos in relevant_positions)
                match_score = matches / len(moving_lines) if moving_lines else 0
            features.append(match_score)
        
        # 3. 卦象名称关键词特征 (5维)
        keywords = {
            '财运': ['财', '富', '丰', '有'],
            '爱情': ['咸', '恒', '家', '归', '妹'],
            '事业': ['乾', '升', '晋', '鼎', '革'],
            '健康': ['颐', '复', '泰', '既济'],
            '诉讼': ['讼', '师', '夬', '履'],
        }
        for qtype in self.QUESTION_TYPES:
            has_keyword = any(kw in hexagram_name for kw in keywords.get(qtype, []))
            features.append(1.0 if has_keyword else 0.0)
        
        # 4. 上下卦组合特征 (用于区分相似类型)
        upper = case['hexagram']['upper_trigram']
        lower = case['hexagram']['lower_trigram']
        
        # 财运 vs 爱情：看是否有泽/山
        features.append(1.0 if '兑' in [upper, lower] else 0.0)  # 泽与财运相关
        features.append(1.0 if '艮' in [upper, lower] else 0.0)  # 山与爱情相关
        
        # 事业 vs 诉讼：看是否有乾/坎
        features.append(1.0 if '乾' in [upper, lower] else 0.0)  # 天与事业相关
        features.append(1.0 if '坎' in [upper, lower] else 0.0)  # 水与诉讼相关
        
        return np.array(features, dtype=np.float32)
    
    def get_feature_names(self) -> List[str]:
        """获取特征名称"""
        base_names = super().get_feature_names()
        names = list(base_names)
        
        # 新增特征
        names.extend([f'detailed_hex_{q}' for q in self.QUESTION_TYPES])
        names.extend([f'moving_match_{q}' for q in self.QUESTION_TYPES])
        names.extend([f'keyword_{q}' for q in self.QUESTION_TYPES])
        names.extend(['has_dui', 'has_gen', 'has_qian', 'has_kan'])
        
        return names


def train_advanced_model():
    """训练高级问事类型预测模型"""
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
    extractor = AdvancedQuestionTypeExtractor()
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
    top_indices = np.argsort(importance)[::-1][:15]
    
    print("\nTop 15 重要特征:")
    for idx in top_indices:
        print(f"  {feature_names[idx]}: {importance[idx]:.4f}")
    
    # 保存模型
    model_path = os.path.join(os.path.dirname(__file__), 'advanced_question_type_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({'model': model, 'extractor': extractor}, f)
    print(f"\n模型已保存至: {model_path}")
    
    return accuracy


if __name__ == '__main__':
    train_advanced_model()
