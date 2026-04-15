#!/bin/bash
# Web3 News Push - Cron 运行脚本
# 被 crontab 直接调用，负责加载环境并执行主程序

set -e

PROJECT_DIR="/Users/limohan/code_projects/web3/web3-news-push"
PYTHON="$PROJECT_DIR/venv/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/cron_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 开始执行 =====" >> "$LOG_FILE"

# 加载 .env
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

cd "$PROJECT_DIR"

"$PYTHON" src/main.py >> "$LOG_FILE" 2>&1

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 执行完成 =====" >> "$LOG_FILE"
