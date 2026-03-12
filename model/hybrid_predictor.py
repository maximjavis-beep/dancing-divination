"""
混合预测模型
整合规则引擎、GBM模型和案例匹配
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List

# 直接导入，避免__init__.py中的torch依赖
sys.path.insert(0, os.path.dirname(__file__))
from rule_engine import RuleEngine
from case_matcher import CaseMatcher
from gbm_predictor import GBMHexagramPredictor

class HybridPredictor:
    """
    混合预测模型
    
    权重分配：
    - 规则引擎: 40%
    - GBM模型: 40%
    - 案例匹配: 20%
    """
    
    FORTUNE_LEVELS = ['大吉', '吉', '平', '凶', '大凶']
    
    # 模型权重
    WEIGHTS = {
        'rule_engine': 0.40,
        'gbm': 0.40,
        'case_matcher': 0.20
    }
    
    def __init__(self, gbm_model_path=None):
        """
        初始化混合预测器
        
        Args:
            gbm_model_path: GBM模型文件路径
        """
        print("初始化混合预测模型...")
        
        # 初始化各组件
        self.rule_engine = RuleEngine()
        self.case_matcher = CaseMatcher()
        self.gbm = GBMHexagramPredictor(gbm_model_path)
        
        # 尝试加载GBM模型
        self.gbm_loaded = False
        try:
            self.gbm.load_model()
            self.gbm_loaded = True
            print("GBM模型加载成功")
        except Exception as e:
            print(f"GBM模型未加载: {e}")
        
        print("混合预测模型初始化完成")
    
    def _convert_to_numeric(self, fortune_level):
        """将吉凶等级转换为数值（用于加权计算）"""
        mapping = {
            '大吉': 2,
            '吉': 1,
            '平': 0,
            '凶': -1,
            '大凶': -2
        }
        return mapping.get(fortune_level, 0)
    
    def _convert_from_numeric(self, value):
        """将数值转换回吉凶等级"""
        if value >= 1.5:
            return '大吉'
        elif value >= 0.5:
            return '吉'
        elif value >= -0.5:
            return '平'
        elif value >= -1.5:
            return '凶'
        else:
            return '大凶'
    
    def _merge_probabilities(self, results: Dict[str, Dict]) -> Dict:
        """
        合并各模型的概率分布
        
        Args:
            results: 各模型的预测结果
            
        Returns:
            dict: 合并后的概率分布
        """
        merged = {level: 0.0 for level in self.FORTUNE_LEVELS}
        
        for model_name, result in results.items():
            weight = self.WEIGHTS.get(model_name, 0)
            probs = result.get('probabilities', {})
            
            for level in self.FORTUNE_LEVELS:
                merged[level] += probs.get(level, 0) * weight
        
        # 归一化
        total = sum(merged.values())
        if total > 0:
            merged = {k: v / total for k, v in merged.items()}
        
        return merged
    
    def predict(self, case: Dict, return_components=False) -> Dict:
        """
        预测接口
        
        Args:
            case: 案例字典
            return_components: 是否返回各组件的预测结果
            
        Returns:
            dict: 预测结果
        """
        results = {}
        
        # 1. 规则引擎预测
        try:
            rule_result = self.rule_engine.predict(case)
            results['rule_engine'] = rule_result
        except Exception as e:
            print(f"规则引擎预测失败: {e}")
            results['rule_engine'] = {
                'fortune_level': '平',
                'probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS}
            }
        
        # 确保规则引擎结果有probabilities
        if 'probabilities' not in results['rule_engine']:
            results['rule_engine']['probabilities'] = {level: 0.2 for level in self.FORTUNE_LEVELS}
        
        # 2. GBM模型预测
        if self.gbm_loaded:
            try:
                gbm_result = self.gbm.predict(case)
                results['gbm'] = gbm_result
            except Exception as e:
                print(f"GBM预测失败: {e}")
                results['gbm'] = {
                    'fortune_level': '平',
                    'probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS}
                }
        else:
            # 如果GBM未加载，使用规则引擎结果作为替代
            results['gbm'] = results['rule_engine'].copy()
        
        # 确保GBM结果有probabilities
        if 'probabilities' not in results['gbm']:
            results['gbm']['probabilities'] = {level: 0.2 for level in self.FORTUNE_LEVELS}
        
        # 3. 案例匹配预测
        try:
            case_result = self.case_matcher.predict(case)
            results['case_matcher'] = case_result
        except Exception as e:
            print(f"案例匹配预测失败: {e}")
            results['case_matcher'] = {
                'fortune_level': '平',
                'probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS}
            }
        
        # 确保案例匹配结果有probabilities
        if 'probabilities' not in results['case_matcher']:
            results['case_matcher']['probabilities'] = {level: 0.2 for level in self.FORTUNE_LEVELS}
        
        # 合并概率分布
        merged_probs = self._merge_probabilities(results)
        
        # 确定最终预测结果
        final_fortune = max(merged_probs, key=merged_probs.get)
        
        # 构建返回结果
        response = {
            'fortune_level': final_fortune,
            'probabilities': merged_probs,
            'confidence': merged_probs[final_fortune],
            'method': 'hybrid',
            'weights': self.WEIGHTS
        }
        
        # 如果要求返回各组件结果
        if return_components:
            response['components'] = {
                name: {
                    'fortune_level': result['fortune_level'],
                    'probabilities': result['probabilities'],
                    'weight': self.WEIGHTS.get(name, 0)
                }
                for name, result in results.items()
            }
            
            # 添加规则引擎的详细规则
            if 'rule_details' in results.get('rule_engine', {}):
                response['components']['rule_engine']['rule_details'] = \
                    results['rule_engine']['rule_details']
            
            # 添加案例匹配的相似案例
            if 'similar_cases' in results.get('case_matcher', {}):
                response['components']['case_matcher']['similar_cases'] = \
                    results['case_matcher']['similar_cases']
        
        return response
    
    def explain_prediction(self, prediction: Dict) -> str:
        """
        生成预测解释
        
        Args:
            prediction: 预测结果
            
        Returns:
            str: 解释文本
        """
        fortune = prediction['fortune_level']
        confidence = prediction['confidence']
        
        explanation = f"预测结果：{fortune}（置信度：{confidence:.1%}）\n\n"
        
        if 'components' in prediction:
            explanation += "各模型预测：\n"
            for name, component in prediction['components'].items():
                name_map = {
                    'rule_engine': '规则引擎',
                    'gbm': 'GBM模型',
                    'case_matcher': '案例匹配'
                }
                explanation += f"  - {name_map.get(name, name)}: {component['fortune_level']} "
                explanation += f"(权重{component['weight']:.0%})\n"
            
            # 规则明细
            if 'rule_details' in prediction['components'].get('rule_engine', {}):
                explanation += "\n规则引擎分析：\n"
                for rule in prediction['components']['rule_engine']['rule_details'][:3]:
                    explanation += f"  - {rule['description']}\n"
            
            # 相似案例
            if 'similar_cases' in prediction['components'].get('case_matcher', {}):
                explanation += "\n参考案例：\n"
                for case in prediction['components']['case_matcher']['similar_cases'][:3]:
                    explanation += f"  - {case['case_id']}: {case['hexagram_name']} "
                    explanation += f"({case['fortune_level']})\n"
        
        return explanation
    
    def evaluate(self, cases: List[Dict]) -> Dict:
        """
        评估模型性能
        
        Args:
            cases: 测试案例列表
            
        Returns:
            dict: 评估结果
        """
        correct = 0
        total = len(cases)
        
        # 各模型准确率
        rule_correct = 0
        gbm_correct = 0
        case_correct = 0
        
        for case in cases:
            actual = case['expert_interpretation']['fortune_level']
            
            # 混合模型预测（带组件结果）
            prediction = self.predict(case, return_components=True)
            if prediction['fortune_level'] == actual:
                correct += 1
            
            # 各组件单独评估
            if 'components' in prediction:
                if prediction['components']['rule_engine']['fortune_level'] == actual:
                    rule_correct += 1
                if prediction['components']['gbm']['fortune_level'] == actual:
                    gbm_correct += 1
                if prediction['components']['case_matcher']['fortune_level'] == actual:
                    case_correct += 1
        
        accuracy = correct / total if total > 0 else 0
        
        return {
            'total_cases': total,
            'correct_predictions': correct,
            'accuracy': accuracy,
            'component_accuracy': {
                'rule_engine': rule_correct / total if total > 0 else 0,
                'gbm': gbm_correct / total if total > 0 else 0,
                'case_matcher': case_correct / total if total > 0 else 0
            }
        }


def train_and_evaluate():
    """训练并评估混合模型"""
    print("=" * 50)
    print("混合模型训练与评估")
    print("=" * 50)
    
    # 初始化混合预测器
    predictor = HybridPredictor()
    
    # 加载所有案例
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    gudian_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gudian_cases.json')
    
    all_cases = []
    
    # 加载模拟案例
    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            sim_cases = json.load(f)
            all_cases.extend(sim_cases)
            print(f"加载 {len(sim_cases)} 个模拟案例")
    
    # 加载古籍案例
    if os.path.exists(gudian_path):
        with open(gudian_path, 'r', encoding='utf-8') as f:
            gudian_cases = json.load(f)
            all_cases.extend(gudian_cases)
            print(f"加载 {len(gudian_cases)} 个古籍案例")
    
    print(f"\n总计 {len(all_cases)} 个案例")
    
    # 如果没有GBM模型，先训练
    if not predictor.gbm_loaded and len(all_cases) > 0:
        print("\n训练GBM模型...")
        try:
            predictor.gbm.train(all_cases)
            predictor.gbm_loaded = True
            print("GBM模型训练完成")
        except Exception as e:
            print(f"GBM模型训练失败: {e}")
    
    # 交叉验证
    print("\n进行交叉验证...")
    from sklearn.model_selection import KFold
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    fold_results = []
    
    for fold, (train_idx, test_idx) in enumerate(kf.split(all_cases)):
        print(f"\nFold {fold + 1}/5")
        
        test_cases = [all_cases[i] for i in test_idx]
        
        # 评估
        result = predictor.evaluate(test_cases)
        fold_results.append(result)
        
        print(f"  混合模型准确率: {result['accuracy']:.2%}")
        print(f"  规则引擎准确率: {result['component_accuracy']['rule_engine']:.2%}")
        print(f"  GBM模型准确率: {result['component_accuracy']['gbm']:.2%}")
        print(f"  案例匹配准确率: {result['component_accuracy']['case_matcher']:.2%}")
    
    # 平均结果
    avg_accuracy = sum(r['accuracy'] for r in fold_results) / len(fold_results)
    avg_rule = sum(r['component_accuracy']['rule_engine'] for r in fold_results) / len(fold_results)
    avg_gbm = sum(r['component_accuracy']['gbm'] for r in fold_results) / len(fold_results)
    avg_case = sum(r['component_accuracy']['case_matcher'] for r in fold_results) / len(fold_results)
    
    print("\n" + "=" * 50)
    print("交叉验证平均结果")
    print("=" * 50)
    print(f"混合模型准确率: {avg_accuracy:.2%}")
    print(f"规则引擎准确率: {avg_rule:.2%}")
    print(f"GBM模型准确率: {avg_gbm:.2%}")
    print(f"案例匹配准确率: {avg_case:.2%}")
    
    return predictor


if __name__ == '__main__':
    # 训练并评估
    predictor = train_and_evaluate()
    
    # 测试预测
    print("\n" + "=" * 50)
    print("测试预测")
    print("=" * 50)
    
    test_case = {
        'hexagram': {
            'name': '天风姤',
            'upper_trigram': '乾',
            'lower_trigram': '巽',
            'lines': [1, 1, 1, 1, 1, 0],
            'moving_lines': [6]
        },
        'analysis': {
            'shi_position': 1,
            'ying_position': 4,
            'deity_type': '妻财',
            'deity_element': '金',
            'element_relation': '比和'
        },
        'question_type': '财运',
        'year': 2024,
        'month': 3,
        'day': 15,
        'hour': 10
    }
    
    result = predictor.predict(test_case, return_components=True)
    print(predictor.explain_prediction(result))
