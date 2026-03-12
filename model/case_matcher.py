"""
案例匹配引擎
基于卦象名称和问事类型匹配历史案例
"""

import json
import os
from typing import Dict, List
from collections import Counter

class CaseMatcher:
    """案例匹配引擎"""
    
    FORTUNE_LEVELS = ['大吉', '吉', '平', '凶', '大凶']
    
    def __init__(self, cases_path=None):
        """
        初始化案例匹配器
        
        Args:
            cases_path: 案例文件路径，默认为data/gudian_cases.json
        """
        if cases_path is None:
            cases_path = os.path.join(
                os.path.dirname(__file__), '..', 'data', 'gudian_cases.json'
            )
        
        self.cases = []
        self.cases_by_hexagram = {}  # 按卦象分类
        self.cases_by_type = {}       # 按问事类型分类
        
        self._load_cases(cases_path)
    
    def _load_cases(self, cases_path):
        """加载案例数据"""
        if os.path.exists(cases_path):
            with open(cases_path, 'r', encoding='utf-8') as f:
                self.cases = json.load(f)
            
            # 建立索引
            for case in self.cases:
                hex_name = case['hexagram']['name']
                q_type = case['question_type']
                
                if hex_name not in self.cases_by_hexagram:
                    self.cases_by_hexagram[hex_name] = []
                self.cases_by_hexagram[hex_name].append(case)
                
                if q_type not in self.cases_by_type:
                    self.cases_by_type[q_type] = []
                self.cases_by_type[q_type].append(case)
            
            print(f"案例匹配器已加载 {len(self.cases)} 个案例")
        else:
            print(f"案例文件不存在: {cases_path}")
    
    def calculate_similarity(self, case1, case2):
        """
        计算两个案例的相似度
        
        相似度计算维度：
        1. 卦象名称相同：+0.5
        2. 问事类型相同：+0.3
        3. 动爻数量相近：+0.1
        4. 世爻位置相同：+0.1
        """
        similarity = 0.0
        
        # 卦象名称
        if case1['hexagram']['name'] == case2['hexagram']['name']:
            similarity += 0.5
        
        # 问事类型
        if case1['question_type'] == case2['question_type']:
            similarity += 0.3
        
        # 动爻数量
        moving1 = len(case1['hexagram'].get('moving_lines', []))
        moving2 = len(case2['hexagram'].get('moving_lines', []))
        if moving1 == moving2:
            similarity += 0.1
        elif abs(moving1 - moving2) == 1:
            similarity += 0.05
        
        # 世爻位置
        if case1['analysis']['shi_position'] == case2['analysis']['shi_position']:
            similarity += 0.1
        
        return similarity
    
    def find_similar_cases(self, hexagram_name, question_type, 
                          moving_lines=None, shi_position=None, limit=10):
        """
        查找相似案例
        
        Args:
            hexagram_name: 卦象名称
            question_type: 问事类型
            moving_lines: 动爻列表（可选）
            shi_position: 世爻位置（可选）
            limit: 返回案例数量上限
            
        Returns:
            list: 相似案例列表，按相似度排序
        """
        # 构建查询案例
        query_case = {
            'hexagram': {
                'name': hexagram_name,
                'moving_lines': moving_lines or []
            },
            'question_type': question_type,
            'analysis': {
                'shi_position': shi_position or 1
            }
        }
        
        # 计算所有案例的相似度
        similar_cases = []
        for case in self.cases:
            sim = self.calculate_similarity(query_case, case)
            if sim > 0:  # 只保留有相似度的案例
                similar_cases.append((case, sim))
        
        # 按相似度排序
        similar_cases.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前N个
        return similar_cases[:limit]
    
    def weighted_vote(self, similar_cases):
        """
        基于相似案例进行加权投票
        
        Args:
            similar_cases: (案例, 相似度) 元组列表
            
        Returns:
            dict: 投票结果
        """
        if not similar_cases:
            return {
                'fortune_level': '平',
                'probabilities': {level: 0.2 for level in self.FORTUNE_LEVELS},
                'vote_count': 0,
                'total_weight': 0
            }
        
        # 加权投票
        weighted_votes = {level: 0.0 for level in self.FORTUNE_LEVELS}
        total_weight = 0.0
        
        for case, similarity in similar_cases:
            fortune = case['expert_interpretation']['fortune_level']
            weight = similarity
            weighted_votes[fortune] += weight
            total_weight += weight
        
        # 归一化为概率
        if total_weight > 0:
            probabilities = {
                level: weighted_votes[level] / total_weight 
                for level in self.FORTUNE_LEVELS
            }
        else:
            probabilities = {level: 0.2 for level in self.FORTUNE_LEVELS}
        
        # 确定最终吉凶
        max_level = max(probabilities, key=probabilities.get)
        
        return {
            'fortune_level': max_level,
            'probabilities': probabilities,
            'vote_count': len(similar_cases),
            'total_weight': total_weight,
            'vote_details': [
                {
                    'case_id': case['case_id'],
                    'hexagram_name': case['hexagram']['name'],
                    'fortune_level': case['expert_interpretation']['fortune_level'],
                    'similarity': sim,
                    'weight': sim
                }
                for case, sim in similar_cases[:5]  # 只显示前5个
            ]
        }
    
    def predict(self, case, limit=10):
        """
        预测接口
        
        Args:
            case: 案例字典
            limit: 查找相似案例数量
            
        Returns:
            dict: 预测结果
        """
        hexagram_name = case['hexagram']['name']
        question_type = case['question_type']
        moving_lines = case['hexagram'].get('moving_lines', [])
        shi_position = case['analysis'].get('shi_position', 1)
        
        # 查找相似案例
        similar_cases = self.find_similar_cases(
            hexagram_name, question_type, moving_lines, shi_position, limit
        )
        
        # 加权投票
        vote_result = self.weighted_vote(similar_cases)
        
        return {
            'fortune_level': vote_result['fortune_level'],
            'probabilities': vote_result['probabilities'],
            'similar_cases': vote_result['vote_details'],
            'vote_count': vote_result['vote_count'],
            'method': 'case_matcher'
        }
    
    def get_case_statistics(self, hexagram_name=None, question_type=None):
        """
        获取案例统计信息
        
        Args:
            hexagram_name: 卦象名称（可选）
            question_type: 问事类型（可选）
            
        Returns:
            dict: 统计信息
        """
        # 筛选案例
        filtered = self.cases
        if hexagram_name:
            filtered = [c for c in filtered if c['hexagram']['name'] == hexagram_name]
        if question_type:
            filtered = [c for c in filtered if c['question_type'] == question_type]
        
        if not filtered:
            return {'count': 0}
        
        # 统计吉凶分布
        fortune_counts = Counter(
            c['expert_interpretation']['fortune_level'] for c in filtered
        )
        
        return {
            'count': len(filtered),
            'fortune_distribution': dict(fortune_counts),
            'hexagram_count': len(set(c['hexagram']['name'] for c in filtered)),
            'type_distribution': dict(Counter(c['question_type'] for c in filtered))
        }


if __name__ == '__main__':
    # 测试案例匹配器
    matcher = CaseMatcher()
    
    # 测试案例
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
        'question_type': '财运'
    }
    
    result = matcher.predict(test_case)
    print(f"预测结果: {result['fortune_level']}")
    print(f"概率分布: {result['probabilities']}")
    print(f"相似案例数: {result['vote_count']}")
    print("\n相似案例:")
    for case in result['similar_cases'][:3]:
        print(f"  - {case['case_id']}: {case['hexagram_name']} ({case['fortune_level']}) 相似度: {case['similarity']:.2f}")
