#!/bin/bash
# VPS 一次性初始化脚本
# 用法：bash setup-vps.sh [用户名，默认 deploy]
set -e

DEPLOY_USER="${1:-deploy}"
INSTALL_DIR="/opt/web3-news-push"
REPO_URL="https://github.com/Aubrey-M-ops/crypto-espresso.git"

echo "=== Web3 News Push VPS 初始化 ==="
echo "安装目录: $INSTALL_DIR"
echo "运行用户: $DEPLOY_USER"
echo ""

# 1. 安装系统依赖
echo ">>> 安装系统依赖..."
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip git

# 2. 创建运行用户（如果不存在）
if ! id "$DEPLOY_USER" &>/dev/null; then
    useradd -r -s /bin/bash -m "$DEPLOY_USER"
    echo ">>> 创建用户 $DEPLOY_USER"
fi

# 3. clone 项目
if [ -d "$INSTALL_DIR/.git" ]; then
    echo ">>> 更新代码..."
    git -C "$INSTALL_DIR" pull
else
    echo ">>> 克隆代码..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$INSTALL_DIR"

# 4. 安装 Python 依赖
echo ">>> 安装 Python 依赖..."
sudo -u "$DEPLOY_USER" python3 -m venv "$INSTALL_DIR/venv"
sudo -u "$DEPLOY_USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet

# 5. 配置 .env
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo ""
    echo ">>> 未找到 .env，请手动创建："
    echo "    nano $INSTALL_DIR/.env"
    echo ""
    echo "    必填项："
    echo "      ANTHROPIC_API_KEY=sk-ant-..."
    echo "      TELEGRAM_BOT_TOKEN=..."
    echo "      TELEGRAM_CHANNEL_ID=..."
    echo "      TG_API_ID=...    # Telethon KOL 抓取"
    echo "      TG_API_HASH=..."
    echo ""
fi

# 6. Telethon 首次登录（交互）
echo ">>> Telethon 首次授权（只需一次）..."
echo "    如果 sessions/ 目录已有 .session 文件可跳过，直接按 Ctrl+C"
echo ""
read -p "现在进行 Telethon 授权？[y/N] " do_auth
if [[ "$do_auth" =~ ^[Yy]$ ]]; then
    source "$INSTALL_DIR/.env"
    sudo -u "$DEPLOY_USER" "$INSTALL_DIR/venv/bin/python" - <<'EOF'
import asyncio
from telethon import TelegramClient
import os

api_id = int(os.environ["TG_API_ID"])
api_hash = os.environ["TG_API_HASH"]
session = "sessions/kol_monitor"

async def auth():
    client = TelegramClient(session, api_id, api_hash)
    await client.start()
    me = await client.get_me()
    print(f"登录成功: {me.first_name} (@{me.username})")
    await client.disconnect()

asyncio.run(auth())
EOF
fi

# 7. 安装 systemd 单元
echo ">>> 安装 systemd 定时器..."
cp "$INSTALL_DIR/deploy/web3-news-push.service" /etc/systemd/system/web3-news-push@.service
cp "$INSTALL_DIR/deploy/web3-news-push.timer"   /etc/systemd/system/web3-news-push.timer

# 修正 service 中的用户占位符
sed -i "s/%i/$DEPLOY_USER/g" /etc/systemd/system/web3-news-push@.service

systemctl daemon-reload
systemctl enable --now "web3-news-push.timer"

echo ""
echo "=== 完成 ==="
echo ""
echo "常用命令："
echo "  systemctl status web3-news-push.timer    # 查看定时器状态"
echo "  systemctl list-timers web3-news-push     # 查看下次触发时间"
echo "  journalctl -u 'web3-news-push@*' -f      # 实时日志"
echo "  systemctl start web3-news-push@$DEPLOY_USER  # 立即触发一次"
