#!/bin/bash
# Web3 News Push - 快速部署脚本

set -e

PROJECT_DIR="/Users/limohan/code_projects/web3/web3-news-push"
cd "$PROJECT_DIR"

echo "🚀 Web3 News Push - 部署检查"
echo "================================"

# 1. 检查环境变量
echo ""
echo "📋 Step 1/5: 检查环境变量..."
if [ ! -f .env ]; then
    echo "❌ .env 文件不存在！"
    echo "   请复制 .env.example 并填入配置"
    exit 1
fi

if ! grep -q "TELEGRAM_CHANNEL_ID=7967372524" .env; then
    echo "⚠️  TELEGRAM_CHANNEL_ID 可能未配置"
fi

if ! grep -q "ANTHROPIC_API_KEY=sk-ant-" .env; then
    echo "❌ ANTHROPIC_API_KEY 未配置！"
    exit 1
fi

echo "✅ 环境变量配置完成"

# 2. 检查依赖
echo ""
echo "📦 Step 2/5: 检查 Python 依赖..."
if ! python3 -c "import anthropic, feedparser, httpx" 2>/dev/null; then
    echo "⚠️  部分依赖缺失，正在安装..."
    pip3 install -r requirements.txt --quiet
fi
echo "✅ 依赖检查完成"

# 3. 测试运行
echo ""
echo "🧪 Step 3/5: 测试 dry-run..."
if python3 src/main.py --dry-run --max-articles 1 2>&1 | grep -q "completed successfully"; then
    echo "✅ Dry-run 测试通过"
else
    echo "❌ Dry-run 测试失败！"
    echo "   运行 'python3 src/main.py --dry-run --verbose' 查看详情"
    exit 1
fi

# 4. 显示 cron 配置
echo ""
echo "⏰ Step 4/5: OpenClaw Cron 配置"
echo "================================"
echo "添加以下配置到你的 OpenClaw config.yaml:"
echo ""
cat openclaw-cron.yaml | grep -A 10 "cron:"
echo ""
echo "配置文件可能位置:"
echo "  - ~/.openclaw/config.yaml"
echo "  - 项目根目录/openclaw.config.yaml"
echo ""

# 5. 重启提示
echo "🔄 Step 5/5: 重启 OpenClaw"
echo "================================"
echo "配置完成后，运行:"
echo "  openclaw gateway restart"
echo ""
echo "检查 cron 任务:"
echo "  openclaw cron list"
echo ""

echo "✅ 部署检查完成！"
echo ""
echo "📊 下一步:"
echo "  1. 将 openclaw-cron.yaml 中的 cron 配置复制到 OpenClaw config"
echo "  2. 运行 'openclaw gateway restart'"
echo "  3. 明早 8:00 查收第一条推送！"
