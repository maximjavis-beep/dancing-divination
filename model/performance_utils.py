#!/usr/bin/env python3
"""
性能优化工具
- 模型预测缓存
- 案例数据按需加载
- 内存使用优化
"""

import os
import sys
import json
import functools
import time
from typing import Dict, List, Optional
import pickle
import hashlib

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PredictionCache:
    """预测结果缓存"""
    
    def __init__(self, cache_dir: str = None, max_size: int = 1000):
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '..', '.cache')
        self.max_size = max_size
        self.memory_cache = {}
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_key(self, case: Dict) -> str:
        """生成缓存键"""
        # 使用案例的关键字段生成哈希
        key_data = {
            'year': case.get('year'),
            'month': case.get('month'),
            'day': case.get('day'),
            'hour': case.get('hour'),
            'question_type': case.get('question_type'),
            'hexagram_name': case.get('hexagram', {}).get('name'),
            'moving_lines': case.get('hexagram', {}).get('moving_lines', [])
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, case: Dict) -> Optional[Dict]:
        """获取缓存结果"""
        key = self._get_cache_key(case)
        
        # 先查内存缓存
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # 再查磁盘缓存
        cache_file = os.path.join(self.cache_dir, f'{key}.pkl')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    result = pickle.load(f)
                # 放入内存缓存
                self.memory_cache[key] = result
                return result
            except Exception:
                return None
        
        return None
    
    def set(self, case: Dict, result: Dict):
        """设置缓存结果"""
        key = self._get_cache_key(case)
        
        # 存入内存缓存
        self.memory_cache[key] = result
        
        # 限制内存缓存大小
        if len(self.memory_cache) > self.max_size:
            # 移除最旧的条目（简单实现：移除第一个）
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
        
        # 存入磁盘缓存
        cache_file = os.path.join(self.cache_dir, f'{key}.pkl')
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            print(f"缓存写入失败: {e}")
    
    def clear(self):
        """清空缓存"""
        self.memory_cache.clear()
        # 清空磁盘缓存
        for f in os.listdir(self.cache_dir):
            if f.endswith('.pkl'):
                try:
                    os.remove(os.path.join(self.cache_dir, f))
                except Exception:
                    pass

class LazyDataLoader:
    """懒加载案例数据"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), '..', 'data')
        self._cases = None
        self._gudian_cases = None
        self._load_time = None
    
    def _load_cases(self):
        """加载现代案例"""
        if self._cases is None:
            start = time.time()
            cases_path = os.path.join(self.data_dir, 'cases.json')
            with open(cases_path, 'r', encoding='utf-8') as f:
                self._cases = json.load(f)
            self._load_time = time.time() - start
            print(f"📊 加载 {len(self._cases)} 个现代案例，耗时 {self._load_time:.3f}s")
        return self._cases
    
    def _load_gudian_cases(self):
        """加载古籍案例"""
        if self._gudian_cases is None:
            gudian_path = os.path.join(self.data_dir, 'gudian_cases.json')
            if os.path.exists(gudian_path):
                start = time.time()
                with open(gudian_path, 'r', encoding='utf-8') as f:
                    self._gudian_cases = json.load(f)
                print(f"📚 加载 {len(self._gudian_cases)} 个古籍案例，耗时 {time.time() - start:.3f}s")
            else:
                self._gudian_cases = []
        return self._gudian_cases
    
    @property
    def cases(self) -> List[Dict]:
        """获取所有现代案例"""
        return self._load_cases()
    
    @property
    def gudian_cases(self) -> List[Dict]:
        """获取所有古籍案例"""
        return self._load_gudian_cases()
    
    @property
    def all_cases(self) -> List[Dict]:
        """获取所有案例"""
        return self.cases + self.gudian_cases
    
    def get_cases_by_type(self, question_type: str) -> List[Dict]:
        """按问事类型获取案例"""
        return [c for c in self.all_cases if c.get('question_type') == question_type]
    
    def get_cases_by_hexagram(self, hexagram_name: str) -> List[Dict]:
        """按卦名获取案例"""
        return [c for c in self.all_cases 
                if c.get('hexagram', {}).get('name') == hexagram_name]

def cached_predict(cache: PredictionCache):
    """预测结果缓存装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, case: Dict, *args, **kwargs):
            # 尝试从缓存获取
            cached_result = cache.get(case)
            if cached_result is not None:
                return cached_result
            
            # 执行预测
            result = func(self, case, *args, **kwargs)
            
            # 存入缓存
            cache.set(case, result)
            
            return result
        return wrapper
    return decorator

# 全局缓存实例
_global_cache = None
_global_loader = None

def get_cache() -> PredictionCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = PredictionCache()
    return _global_cache

def get_loader() -> LazyDataLoader:
    """获取全局数据加载器"""
    global _global_loader
    if _global_loader is None:
        _global_loader = LazyDataLoader()
    return _global_loader

def clear_all_cache():
    """清空所有缓存"""
    global _global_cache
    if _global_cache:
        _global_cache.clear()
        print("✅ 缓存已清空")

def print_memory_usage():
    """打印内存使用情况"""
    import psutil
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"💾 内存使用: {mem_info.rss / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    print("=" * 50)
    print("性能优化工具测试")
    print("=" * 50)
    
    # 测试懒加载
    print("\n1. 测试懒加载:")
    loader = LazyDataLoader()
    print(f"   案例数量: {len(loader.all_cases)}")
    
    # 测试缓存
    print("\n2. 测试缓存:")
    cache = PredictionCache()
    test_case = {'year': 2024, 'month': 3, 'day': 14, 'hour': 10, 
                 'question_type': '财运', 'hexagram': {'name': '地天泰', 'moving_lines': [1]}}
    test_result = {'fortune_level': '吉', 'time_window': '近期'}
    
    cache.set(test_case, test_result)
    cached = cache.get(test_case)
    print(f"   缓存命中: {cached == test_result}")
    
    print("\n✅ 测试完成!")
