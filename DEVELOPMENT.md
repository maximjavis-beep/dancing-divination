# 开发指南

## 本地开发

### 1. 创建虚拟环境

```bash
cd projects/Dancing
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行开发服务器

```bash
python api/index.py
```

服务将在 http://localhost:5002 启动

## 模型训练

### 训练GBM模型

```python
from model.gbm_predictor import GBMHexagramPredictor

# 加载案例数据
import json
with open('data/cases.json', 'r', encoding='utf-8') as f:
    cases = json.load(f)

# 训练模型
model = GBMHexagramPredictor()
model.train(cases)
model.save_model()
```

### 交叉验证

```bash
python model/cross_validate.py
```

## 添加新案例

案例格式：

```json
{
  "case_id": 1,
  "datetime": "2021-01-26T09:00:00",
  "year": 2021,
  "month": 1,
  "day": 26,
  "hour": 9,
  "question_type": "事业",
  "hexagram": {
    "name": "地天泰",
    "upper_trigram": "坤",
    "lower_trigram": "乾",
    "lines": [1, 1, 1, 0, 0, 0],
    "moving_lines": [1],
    "special_pattern": "六合"
  },
  "changed_hexagram": {
    "name": "地泽临",
    "upper_trigram": "坤",
    "lower_trigram": "兑"
  },
  "analysis": {
    "世爻": 3,
    "应爻": 6,
    "用神": "官鬼"
  },
  "expert_interpretation": {
    "fortune_level": "吉",
    "time_window": "中期（一月内）",
    "fortune_comment": "泰卦象征通泰，事业有发展机会"
  }
}
```

## 项目结构说明

### liuyao/ - 六爻核心

- `engine.py`: 核心起卦算法
  - `generate_hexagram()`: 生成卦象
  - `analyze()`: 分析卦象
  - 包含64卦定义、八卦定义、五行关系

- `bazi.py`: 八字计算
  - `calculate_bazi()`: 计算四柱
  - `get_bazi_info()`: 获取完整八字信息

- `bazi_hexagram.py`: 联合分析
  - `analyze_bazi_hexagram()`: 八字六爻联合解读

- `trend_analyzer.py`: 趋势分析
  - `analyze_trend()`: 分析12小时趋势

- `baihua.py`: 白话解读
  - `generate_full_baihua()`: 生成白话解读
  - 包含64卦白话解释

### model/ - 预测模型

- `gbm_predictor.py`: GBM预测器
  - 使用scikit-learn的GradientBoostingClassifier
  - 支持吉凶预测和时间窗口预测

- `ensemble.py`: 集成预测
  - 结合GBM和规则引擎

- `rule_engine.py`: 规则引擎
  - 基于传统六爻规则的预测

### api/ - Web接口

- `index.py`: Flask应用
  - 所有API路由定义
  - 前端页面渲染

## 调试技巧

### 查看卦象计算过程

```python
from liuyao.engine import generate_hexagram, analyze

hexagram = generate_hexagram(2024, 3, 14, 10)
print(f"卦名: {hexagram.name}")
print(f"上卦: {hexagram.upper_trigram}")
print(f"下卦: {hexagram.lower_trigram}")
print(f"动爻: {hexagram.moving_lines}")

analysis = analyze(2024, 3, 14, 10, "财运")
print(analysis)
```

### 测试八字计算

```python
from liuyao.bazi import get_bazi_info

bazi = get_bazi_info(1990, 1, 1, 12, "男")
print(bazi)
```

## 常见问题

### 模型未加载

如果看到 "演示模式：模型未训练或加载失败"，需要：
1. 确保有训练好的模型文件 `model/gbm_model.pkl`
2. 或运行训练脚本生成模型

### 案例数据加载失败

检查 `data/cases.json` 和 `data/gudian_cases.json` 文件是否存在。

## 性能优化

### 已实现的优化

1. **模型预测缓存** (`model/performance_utils.py`)
   - `PredictionCache` 类提供内存+磁盘两级缓存
   - 自动缓存预测结果，减少重复计算
   - 使用案例特征哈希作为缓存键

2. **案例数据懒加载** (`model/performance_utils.py`)
   - `LazyDataLoader` 类按需加载案例数据
   - 支持按问事类型和卦名快速筛选
   - 首次访问时才加载，减少启动时间

3. **模型训练管理** (`model/train_model.py`)
   - 一键训练、验证、查看模型信息
   - 支持自动训练（模型不存在时自动训练）
   - 命令行工具：`python model/train_model.py [train|validate|info|auto]`

4. **数据验证修复** (`data/validate_and_fix.py`)
   - 自动检查案例数据完整性
   - 修复古籍案例缺失的 `special_pattern` 字段
   - 确保数据格式一致性

### 使用方法

```bash
# 验证并修复数据
python data/validate_and_fix.py

# 训练模型（如果不存在则自动训练）
python model/train_model.py auto

# 强制重新训练
python model/train_model.py train --force

# 验证模型
python model/train_model.py validate

# 查看模型信息
python model/train_model.py info
```

## 贡献代码

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request
