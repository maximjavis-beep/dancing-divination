#!/usr/bin/env python3
"""
为案例数据添加特殊格局字段
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import (
    LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS,
    YOUHUN_HEXAGRAMS, GUIHUN_HEXAGRAMS
)

def get_special_pattern(hexagram_name: str) -> str:
    """获取特殊格局"""
    if hexagram_name in LIUCHONG_HEXAGRAMS:
        return '六冲'
    elif hexagram_name in LIUHE_HEXAGRAMS:
        return '六合'
    elif hexagram_name in YOUHUN_HEXAGRAMS:
        return '游魂'
    elif hexagram_name in GUIHUN_HEXAGRAMS:
        return '归魂'
    else:
        return '普通'

def update_cases_file(filepath: str):
    """更新案例文件，添加特殊格局字段"""
    with open(filepath, 'r', encoding='utf-8') as f:
        cases = json.load(f)

    updated_count = 0
    for case in cases:
        hexagram_name = case['hexagram'].get('name', '')
        special_pattern = get_special_pattern(hexagram_name)

        # 添加到 hexagram 中
        if 'special_pattern' not in case['hexagram']:
            case['hexagram']['special_pattern'] = special_pattern
            updated_count += 1

    # 保存更新后的文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    print(f"已更新 {updated_count} 个案例: {filepath}")
    return cases

if __name__ == '__main__':
    # 更新 cases.json
    cases_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    if os.path.exists(cases_path):
        update_cases_file(cases_path)

    # 更新 gudian_cases.json（如果存在）
    gudian_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gudian_cases.json')
    if os.path.exists(gudian_path):
        update_cases_file(gudian_path)

    print("\n数据更新完成!")
