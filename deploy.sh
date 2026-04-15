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

# 4. 安装/检查 crontab
echo ""
echo "⏰ Step 4/5: 检查系统 Cron 配置"
echo "================================"
if crontab -l 2>/dev/null | grep -q "web3-news-push/run.sh"; then
    echo "✅ Cron 已配置："
    crontab -l | grep "web3-news-push"
else
    echo "⚠️  Cron 未配置，正在安装..."
    chmod +x run.sh
    (crontab -l 2>/dev/null; echo "0 8,17 * * * $PROJECT_DIR/run.sh") | crontab -
    echo "✅ Cron 已安装（每天 08:00 和 17:00）"
fi
echo ""

# 5. 完成提示
echo "🎉 Step 5/5: 部署完成"
echo "================================"
echo "✅ 部署检查完成！"
echo ""
echo "📊 下一步（如果还没做）:"
echo "  1. 在 Telegram APP 中将频道设为公开，设置 @username"
echo "  2. 把频道链接分享给订阅者"
echo "  3. 等待 08:00 或 17:00 自动推送！"
echo ""
echo "🔍 查看日志:"
echo "  tail -f logs/cron_\$(date +%Y%m%d).log"
echo ""
echo "📋 查看 Cron 任务:"
echo "  crontab -l"
