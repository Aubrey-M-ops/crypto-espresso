#!/bin/bash
# 本地运行：将最新代码推送到 VPS 并重启服务
# 用法：./deploy/deploy-vps.sh [vps_host] [vps_user] [install_dir]
#
# 示例：
#   ./deploy/deploy-update.sh 1.2.3.4
#   VPS_HOST=1.2.3.4 ./deploy/deploy-update.sh
#
# 依赖：本地已有 SSH 免密登录（ssh-copy-id）

set -euo pipefail

# ── 配置（优先命令行参数，其次环境变量，最后默认值）──────────────────────
VPS_HOST="${1:-${VPS_HOST:?'请设置 VPS_HOST 环境变量或作为第一个参数传入'}}"
VPS_USER="${2:-${VPS_USER:-deploy}}"
INSTALL_DIR="${3:-${INSTALL_DIR:-/opt/web3-news-push}}"
SSH_TARGET="$VPS_USER@$VPS_HOST"

echo "======================================"
echo "  Web3 News Push — 部署更新"
echo "  目标: $SSH_TARGET:$INSTALL_DIR"
echo "======================================"
echo ""

# ── Step 1: 本地确认 git 状态 ──────────────────────────────────────────────
echo ">>> [1/4] 检查本地 git 状态..."
BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git log -1 --format="%h %s")
echo "    当前分支: $BRANCH"
echo "    最新提交: $COMMIT"

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo ""
    echo "⚠️  有未提交的本地改动，是否继续？[y/N]"
    read -r confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "已取消。"; exit 1; }
fi
echo ""

# ── Step 2: 推送代码到远端 ────────────────────────────────────────────────
echo ">>> [2/4] 推送代码到 VPS..."
ssh "$SSH_TARGET" bash -s -- "$INSTALL_DIR" "$BRANCH" <<'REMOTE'
set -euo pipefail
INSTALL_DIR="$1"
BRANCH="$2"

cd "$INSTALL_DIR"

# 拉取最新代码
git fetch origin
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "    代码已更新至: $(git log -1 --format='%h %s')"
REMOTE
echo ""

# ── Step 3: 更新 Python 依赖 ──────────────────────────────────────────────
echo ">>> [3/4] 安装/更新 Python 依赖..."
ssh "$SSH_TARGET" bash -s -- "$INSTALL_DIR" <<'REMOTE'
set -euo pipefail
INSTALL_DIR="$1"
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet --upgrade
echo "    依赖更新完成"
REMOTE
echo ""

# ── Step 4: 同步 systemd 文件并重载服务 ──────────────────────────────────
echo ">>> [4/4] 重载 systemd 服务..."
ssh "$SSH_TARGET" bash -s -- "$INSTALL_DIR" <<'REMOTE'
set -euo pipefail
INSTALL_DIR="$1"

# 如果 service/timer 文件有更新，重新安装
SERVICE_SRC="$INSTALL_DIR/deploy/web3-news-push.service"
TIMER_SRC="$INSTALL_DIR/deploy/web3-news-push.timer"
SERVICE_DST="/etc/systemd/system/web3-news-push@.service"
TIMER_DST="/etc/systemd/system/web3-news-push.timer"

RELOAD_NEEDED=false

if ! cmp -s "$SERVICE_SRC" "$SERVICE_DST" 2>/dev/null; then
    sudo cp "$SERVICE_SRC" "$SERVICE_DST"
    RELOAD_NEEDED=true
    echo "    service 文件已更新"
fi

if ! cmp -s "$TIMER_SRC" "$TIMER_DST" 2>/dev/null; then
    sudo cp "$TIMER_SRC" "$TIMER_DST"
    RELOAD_NEEDED=true
    echo "    timer 文件已更新"
fi

if $RELOAD_NEEDED; then
    sudo systemctl daemon-reload
    sudo systemctl restart web3-news-push.timer
    echo "    systemd 已重载并重启定时器"
else
    echo "    systemd 文件无变化，跳过重载"
fi

# 打印定时器下次触发时间
echo ""
echo "    当前定时器状态:"
systemctl list-timers web3-news-push.timer --no-pager 2>/dev/null || true
REMOTE

echo ""
echo "======================================"
echo "  ✅ 部署完成！"
echo ""
echo "  实用命令（在 VPS 上运行）:"
echo "    journalctl -u 'web3-news-push@*' -f      # 实时日志"
echo "    systemctl start web3-news-push@deploy     # 立即触发一次"
echo "    systemctl status web3-news-push.timer     # 查看定时器"
echo "======================================"
