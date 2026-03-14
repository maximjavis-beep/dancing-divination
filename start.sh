#!/bin/bash
# Dancing 项目启动脚本
# 自动检查环境、训练模型（如需要）、启动服务

set -e

echo "=============================================="
echo "    Dancing 六爻预测系统启动脚本"
echo "=============================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境不存在，正在创建...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查依赖
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  依赖未安装，正在安装...${NC}"
    pip install -r requirements.txt
fi

# 验证并修复数据
echo "📊 验证数据..."
python data/validate_and_fix.py

# 检查模型是否存在，如不存在则自动训练
if [ ! -f "model/gbm_model.pkl" ]; then
    echo -e "${YELLOW}⚠️  模型不存在，开始自动训练...${NC}"
    python model/train_model.py train --force
else
    echo -e "${GREEN}✅ 模型已存在${NC}"
fi

# 验证模型
echo "🔍 验证模型..."
python model/train_model.py validate

echo ""
echo "=============================================="
echo -e "${GREEN}🚀 启动服务...${NC}"
echo "=============================================="
echo ""

# 启动服务
python api/index.py
