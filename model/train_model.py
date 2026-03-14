#!/usr/bin/env python3
"""
模型训练管理脚本
提供一键训练、验证和部署模型的功能
"""

import os
import sys
import json
import argparse
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.gbm_predictor import GBMHexagramPredictor, train_gbm_model

def check_model_exists():
    """检查模型文件是否存在"""
    model_path = os.path.join(os.path.dirname(__file__), '..', 'model', 'gbm_model.pkl')
    return os.path.exists(model_path)

def get_model_info():
    """获取模型信息"""
    model_path = os.path.join(os.path.dirname(__file__), '..', 'model', 'gbm_model.pkl')
    if os.path.exists(model_path):
        stat = os.stat(model_path)
        return {
            'exists': True,
            'path': model_path,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    return {'exists': False}

def train_model(force=False):
    """训练模型"""
    if check_model_exists() and not force:
        info = get_model_info()
        print(f"⚠️ 模型已存在 (大小: {info['size_mb']}MB, 修改时间: {info['modified']})")
        print("使用 --force 参数强制重新训练")
        return False
    
    print("🚀 开始训练模型...")
    print("-" * 50)
    
    try:
        model = train_gbm_model()
        print("\n" + "=" * 50)
        print("✅ 模型训练完成!")
        
        # 显示模型信息
        info = get_model_info()
        print(f"📁 模型路径: {info['path']}")
        print(f"📊 模型大小: {info['size_mb']}MB")
        
        return True
    except Exception as e:
        print(f"\n❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_model():
    """验证模型"""
    print("🔍 验证模型...")
    
    if not check_model_exists():
        print("❌ 模型文件不存在，请先训练模型")
        return False
    
    try:
        model = GBMHexagramPredictor()
        model.load_model()
        
        # 检查模型组件
        required_models = ['fortune', 'type', 'time']
        for task in required_models:
            if task in model.models:
                print(f"  ✅ {task} 模型已加载")
            else:
                print(f"  ⚠️ {task} 模型缺失")
        
        # 测试预测
        test_case = {
            'year': 2024,
            'month': 3,
            'day': 14,
            'hour': 10,
            'question_type': '财运',
            'hexagram': {
                'name': '地天泰',
                'upper_trigram': '坤',
                'lower_trigram': '乾',
                'lines': [1, 1, 1, 0, 0, 0],
                'moving_lines': [1],
                'special_pattern': '六合'
            },
            'analysis': {
                'shi_position': 2,
                'ying_position': 5,
                'element_relation': '生'
            }
        }
        
        result = model.predict(test_case)
        print(f"\n🧪 测试预测结果:")
        print(f"  吉凶: {result['fortune_level']}")
        print(f"  时间窗口: {result['time_window']}")
        
        print("\n✅ 模型验证通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='模型训练管理工具')
    parser.add_argument('command', choices=['train', 'validate', 'info', 'auto'], 
                        help='命令: train=训练, validate=验证, info=查看信息, auto=自动训练（如不存在）')
    parser.add_argument('--force', action='store_true', help='强制重新训练')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Dancing 模型训练管理工具")
    print("=" * 50)
    
    if args.command == 'train':
        train_model(force=args.force)
    elif args.command == 'validate':
        validate_model()
    elif args.command == 'info':
        info = get_model_info()
        if info['exists']:
            print(f"📁 模型路径: {info['path']}")
            print(f"📊 模型大小: {info['size_mb']}MB")
            print(f"🕐 修改时间: {info['modified']}")
        else:
            print("❌ 模型文件不存在")
    elif args.command == 'auto':
        if check_model_exists():
            print("✅ 模型已存在，跳过训练")
            validate_model()
        else:
            print("⚠️ 模型不存在，开始自动训练...")
            if train_model():
                validate_model()

if __name__ == '__main__':
    main()
