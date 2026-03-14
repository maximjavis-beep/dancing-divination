# 🔮 Dancing - 六爻八字联合预测系统

Dancing 是一个基于传统中国命理学的智能预测系统，结合六爻占卜与八字命理，使用机器学习技术提供智能化的预测分析。

## ✨ 核心特性

- **🎯 六爻预测**：基于时间起卦，自动计算卦象、世应、用神、变卦
- **📅 八字分析**：精确计算四柱八字，分析十神关系
- **🔮 联合分析**：六爻与八字结合，提供更全面的预测结果
- **🤖 AI预测**：使用Gradient Boosting等机器学习模型进行智能预测
- **📚 古籍案例**：内置经典古籍案例库，支持相似案例匹配
- **💬 白话解读**：将专业术语转化为通俗易懂的语言
- **📈 趋势分析**：12小时卦象趋势预测

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
cd projects/Dancing
pip install -r requirements.txt
```

### 本地运行

#### 快速启动（推荐）

```bash
./start.sh
```

脚本会自动：
- 检查并创建虚拟环境
- 安装依赖
- 验证并修复数据
- 训练模型（如不存在）
- 启动服务

#### 手动启动

```bash
# 1. 验证数据
python data/validate_and_fix.py

# 2. 训练模型（如不存在）
python model/train_model.py auto

# 3. 启动服务
python api/index.py
```

访问 http://localhost:5002 即可使用。

### Vercel 部署

项目已配置 Vercel Serverless 部署：

```bash
vercel --prod
```

## 📁 项目结构

```
Dancing/
├── api/
│   └── index.py              # Flask API 主入口
├── liuyao/                   # 六爻核心引擎
│   ├── engine.py             # 起卦算法、卦象计算
│   ├── bazi.py               # 八字计算
│   ├── bazi_hexagram.py      # 八字六爻联合分析
│   ├── trend_analyzer.py     # 趋势分析
│   └── baihua.py             # 白话解读模块
├── model/                    # AI预测模型
│   ├── gbm_predictor.py      # Gradient Boosting预测器
│   ├── train_model.py        # 模型训练管理工具 ⭐
│   ├── performance_utils.py  # 性能优化工具 ⭐
│   ├── ensemble.py           # 集成学习
│   ├── rule_engine.py        # 规则引擎
│   ├── dnn_predictor.py      # 深度学习预测器
│   ├── case_matcher.py       # 案例匹配
│   └── cross_validate.py     # 交叉验证
├── data/                     # 数据层
│   ├── cases.json            # 案例数据库 (500个)
│   ├── gudian_cases.json     # 古籍案例 (2000个)
│   ├── validate_and_fix.py   # 数据验证修复工具 ⭐
│   └── generate_cases.py     # 案例生成工具
├── templates/
│   └── index.html            # 前端页面
├── static/
│   └── style.css             # 样式文件
├── start.sh                  # 一键启动脚本 ⭐
├── requirements.txt          # Python依赖
└── vercel.json               # Vercel部署配置
```

## 🔌 API 接口

### 1. 起卦
```http
POST /api/divine
Content-Type: application/json

{
  "datetime": "2024-03-14T10:00:00",
  "question_type": "财运"
}
```

### 2. 八字计算
```http
POST /api/bazi
Content-Type: application/json

{
  "year": 1990,
  "month": 1,
  "day": 1,
  "hour": 12,
  "gender": "男"
}
```

### 3. 八字六爻联合分析
```http
POST /api/divine_with_bazi
Content-Type: application/json

{
  "birth": {"year": 1990, "month": 1, "day": 1, "hour": 12},
  "gender": "男",
  "datetime": "2024-03-14T10:00:00",
  "question_type": "事业"
}
```

### 4. 白话解读
```http
POST /api/baihua
Content-Type: application/json

{
  "hexagram_name": "乾为天",
  "deity_type": "妻财",
  "question_type": "财运",
  "moving_lines": [1]
}
```

### 5. 趋势分析
```http
POST /api/trend
Content-Type: application/json

{
  "datetime": "2024-03-14T10:00:00",
  "question_type": "财运",
  "birth": {"year": 1990, "month": 1, "day": 1, "hour": 12},
  "gender": "男"
}
```

### 6. 获取案例
```http
GET /api/cases?limit=10&offset=0&type=财运
```

### 7. 统计数据
```http
GET /api/stats
```

## 🧠 技术架构

### 六爻引擎
- **时间起卦**：基于年月日时起卦算法
- **卦象计算**：64卦生成、变卦计算
- **世应定位**：自动确定世爻、应爻位置
- **用神分析**：根据问事类型确定用神
- **五行生克**：分析五行相生相克关系
- **特殊卦象**：识别六冲卦、六合卦、游魂卦、归魂卦

### 八字模块
- **四柱计算**：年柱、月柱、日柱、时柱
- **天干地支**：精确推算
- **十神分析**：比肩、劫财、食神、伤官、偏财、正财、七杀、正官、偏印、正印
- **五行统计**：分析八字五行分布

### AI预测模型
- **GBM预测器**：使用Gradient Boosting分类器
- **特征工程**：时间特征、卦象特征、五行特征、特殊卦象特征
- **集成学习**：结合GBM和规则引擎
- **案例匹配**：基于相似度匹配历史案例

## 📊 案例数据

项目包含丰富的案例数据：
- `cases.json`：现代案例库
- `gudian_cases.json`：古籍经典案例

案例包含：
- 起卦时间信息
- 卦象数据（本卦、变卦、动爻）
- 问事类型
- 专家解读（吉凶等级、时间窗口、详细分析）

## 🎯 支持的问事类型

- 财运
- 事业
- 爱情
- 健康
- 诉讼

## 📝 开发计划

- [x] 模型训练脚本优化 ✅
- [x] 数据验证和修复工具 ✅
- [x] 性能优化（缓存、懒加载）✅
- [ ] 增加更多古籍案例
- [ ] 支持更多问事类型
- [ ] 移动端适配优化
- [ ] 用户历史记录功能
- [ ] 多语言支持

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- 传统六爻理论参考《增删卜易》《卜筮正宗》等古籍
- 八字理论参考《渊海子平》《三命通会》等经典

---

**免责声明**：本系统仅供学习和研究使用，预测结果仅供参考，不构成任何决策建议。
