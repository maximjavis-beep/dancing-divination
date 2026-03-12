"""
模型集成
结合GBM和规则引擎的优势
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.gbm_predictor import GBMHexagramPredictor
from model.rule_engine import RuleEngine

class EnsemblePredictor:
    """集成预测器"""
    
    FORTUNE_LEVELS = ['大吉', '吉', '平', '凶', '大凶']
    
    def __init__(self, gbm_weight=0.7, rule_weight=0.3):
        self.gbm = GBMHexagramPredictor()
        self.rule = RuleEngine()
        self.gbm_weight = gbm_weight
        self.rule_weight = rule_weight
        
        # 加载GBM模型
        try:
            self.gbm.load_model()
            self.gbm_loaded = True
        except:
            self.gbm_loaded = False
            print("GBM模型未加载，仅使用规则引擎")
    
    def predict(self, case: Dict) -> Dict:
        """集成预测"""
        # GBM预测
        if self.gbm_loaded:
            gbm_result = self.gbm.predict(case)
            gbm_probs = np.array([gbm_result['fortune_probabilities'][level] for level in self.FORTUNE_LEVELS])
        else:
            gbm_probs = np.ones(5) / 5  # 均匀分布
        
        # 规则引擎预测
        rule_result = self.rule.predict(case)
        rule_probs = np.array([rule_result['fortune_probabilities'][level] for level in self.FORTUNE_LEVELS])
        
        # 加权融合
        ensemble_probs = self.gbm_weight * gbm_probs + self.rule_weight * rule_probs
        ensemble_pred = np.argmax(ensemble_probs)
        
        return {
            'fortune_level': self.FORTUNE_LEVELS[ensemble_pred],
            'fortune_probabilities': {
                level: float(ensemble_probs[i])
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
            'components': {
                'gbm': gbm_result if self.gbm_loaded else None,
                'rule': rule_result,
            },
            'weights': {
                'gbm': self.gbm_weight,
                'rule': self.rule_weight,
            }
        }
    
    def evaluate(self, cases: List[Dict]) -> Dict:
        """评估集成模型"""
        from sklearn.metrics import accuracy_score
        
        y_true = []
        y_ensemble = []
        y_gbm = []
        y_rule = []
        
        for case in cases:
            true_label = self.FORTUNE_LEVELS.index(case['expert_interpretation']['fortune_level'])
            y_true.append(true_label)
            
            # 集成预测
            ensemble_result = self.predict(case)
            y_ensemble.append(self.FORTUNE_LEVELS.index(ensemble_result['fortune_level']))
            
            # GBM预测
            if self.gbm_loaded:
                gbm_result = self.gbm.predict(case)
                y_gbm.append(self.FORTUNE_LEVELS.index(gbm_result['fortune_level']))
            
            # 规则预测
            rule_result = self.rule.predict(case)
            y_rule.append(self.FORTUNE_LEVELS.index(rule_result['fortune_level']))
        
        results = {
            'ensemble_accuracy': accuracy_score(y_true, y_ensemble),
        }
        
        if self.gbm_loaded:
            results['gbm_accuracy'] = accuracy_score(y_true, y_gbm)
        
        results['rule_accuracy'] = accuracy_score(y_true, y_rule)
        
        return results

def evaluate_ensemble():
    """评估集成模型"""
    # 加载数据
    with open(os.path.join('..', 'data', 'cases.json'), 'r') as f:
        mock_cases = json.load(f)
    with open(os.path.join('..', 'data', 'gudian_cases.json'), 'r') as f:
        gudian_cases = json.load(f)
    
    cases = mock_cases + gudian_cases
    print(f"总案例数: {len(cases)}")
    
    # 测试不同权重
    print("\\n测试不同权重组合:")
    print("=" * 60)
    
    best_weight = 0
    best_acc = 0
    
    for gbm_w in [0.5, 0.6, 0.7, 0.8, 0.9]:
        rule_w = 1 - gbm_w
        ensemble = EnsemblePredictor(gbm_weight=gbm_w, rule_weight=rule_w)
        results = ensemble.evaluate(cases[:500])  # 用前500个测试
        
        print(f"GBM:{gbm_w:.1f} + Rule:{rule_w:.1f} => 集成准确率: {results['ensemble_accuracy']:.2%}")
        
        if results['ensemble_accuracy'] > best_acc:
            best_acc = results['ensemble_accuracy']
            best_weight = gbm_w
    
    print(f"\\n最佳权重: GBM={best_weight:.1f}, Rule={1-best_weight:.1f}")
    print(f"最佳集成准确率: {best_acc:.2%}")
    
    # 用最佳权重评估全部数据
    print("\\n用最佳权重评估全部数据:")
    ensemble = EnsemblePredictor(gbm_weight=best_weight, rule_weight=1-best_weight)
    results = ensemble.evaluate(cases)
    
    print(f"GBM准确率: {results.get('gbm_accuracy', 0):.2%}")
    print(f"规则引擎准确率: {results['rule_accuracy']:.2%}")
    print(f"集成准确率: {results['ensemble_accuracy']:.2%}")

if __name__ == '__main__':
    evaluate_ensemble()
