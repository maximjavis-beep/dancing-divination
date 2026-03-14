#!/usr/bin/env python3
"""
数据验证和修复工具
检查并修复案例数据中的问题
"""

import json
import os

def validate_and_fix_cases():
    """验证并修复案例数据"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 修复古籍案例 - 添加缺失的 special_pattern 字段
    gudian_path = os.path.join(base_path, 'data', 'gudian_cases.json')
    if os.path.exists(gudian_path):
        with open(gudian_path, 'r', encoding='utf-8') as f:
            gudian_cases = json.load(f)
        
        # 六冲卦列表
        liuchong_hexagrams = [
            '乾为天', '坤为地', '震为雷', '巽为风', '坎为水', '离为火', '艮为山', '兑为泽'
        ]
        # 六合卦列表
        liuhe_hexagrams = [
            '天地否', '地天泰', '水泽节', '泽水困', '火山旅', '山火贲', '雷地豫', '地雷复',
            '风泽中孚', '泽风大过', '水火既济', '火水未济'
        ]
        # 游魂卦列表
        youhun_hexagrams = [
            '火地晋', '地火明夷', '风水涣', '水风井', '天风姤', '风天小畜', '泽雷随', '雷泽归妹'
        ]
        # 归魂卦列表
        guihun_hexagrams = [
            '火天大有', '天火同人', '水地比', '地水师', '山天大畜', '天雷无妄', '泽山咸', '山泽损'
        ]
        
        fixed_count = 0
        for case in gudian_cases:
            hexagram_name = case.get('hexagram', {}).get('name', '')
            if 'special_pattern' not in case.get('hexagram', {}):
                if hexagram_name in liuchong_hexagrams:
                    case['hexagram']['special_pattern'] = '六冲'
                elif hexagram_name in liuhe_hexagrams:
                    case['hexagram']['special_pattern'] = '六合'
                elif hexagram_name in youhun_hexagrams:
                    case['hexagram']['special_pattern'] = '游魂'
                elif hexagram_name in guihun_hexagrams:
                    case['hexagram']['special_pattern'] = '归魂'
                else:
                    case['hexagram']['special_pattern'] = '普通'
                fixed_count += 1
        
        # 保存修复后的数据
        with open(gudian_path, 'w', encoding='utf-8') as f:
            json.dump(gudian_cases, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 修复了 {fixed_count} 个古籍案例的 special_pattern 字段")
        return True
    else:
        print("⚠️ 古籍案例文件不存在")
        return False

def check_data_integrity():
    """检查数据完整性"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    cases_path = os.path.join(base_path, 'data', 'cases.json')
    gudian_path = os.path.join(base_path, 'data', 'gudian_cases.json')
    
    issues = []
    
    # 检查现代案例
    if os.path.exists(cases_path):
        with open(cases_path, 'r', encoding='utf-8') as f:
            cases = json.load(f)
        print(f"📊 现代案例数量: {len(cases)}")
        
        # 检查必填字段
        required_fields = ['case_id', 'datetime', 'question_type', 'hexagram', 'analysis', 'expert_interpretation']
        for i, case in enumerate(cases):
            for field in required_fields:
                if field not in case:
                    issues.append(f"现代案例[{i}] 缺少字段: {field}")
    else:
        issues.append("现代案例文件不存在")
    
    # 检查古籍案例
    if os.path.exists(gudian_path):
        with open(gudian_path, 'r', encoding='utf-8') as f:
            gudian_cases = json.load(f)
        print(f"📚 古籍案例数量: {len(gudian_cases)}")
        
        # 检查必填字段
        for i, case in enumerate(gudian_cases):
            for field in required_fields:
                if field not in case:
                    issues.append(f"古籍案例[{i}] 缺少字段: {field}")
    else:
        issues.append("古籍案例文件不存在")
    
    if issues:
        print("\n⚠️ 发现以下问题:")
        for issue in issues[:10]:  # 只显示前10个问题
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... 还有 {len(issues) - 10} 个问题")
        return False
    else:
        print("✅ 数据完整性检查通过")
        return True

if __name__ == '__main__':
    print("=" * 50)
    print("数据验证和修复工具")
    print("=" * 50)
    
    # 先检查数据完整性
    check_data_integrity()
    
    print("\n" + "-" * 50)
    
    # 修复古籍案例
    validate_and_fix_cases()
    
    print("\n" + "=" * 50)
    print("完成!")
