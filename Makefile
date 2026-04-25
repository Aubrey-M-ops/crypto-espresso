VPS_HOST    ?= $(shell grep -E '^VPS_HOST='    .env.deploy 2>/dev/null | cut -d= -f2)
VPS_USER    ?= $(shell grep -E '^VPS_USER='    .env.deploy 2>/dev/null | cut -d= -f2 || echo root)
INSTALL_DIR ?= $(shell grep -E '^INSTALL_DIR=' .env.deploy 2>/dev/null | cut -d= -f2 || echo /opt/web3-news-push)
SSH         := ssh $(VPS_USER)@$(VPS_HOST)
PYTHON      := venv/bin/python
PIP         := venv/bin/pip

.PHONY: help \
        install test test-monitor \
        dry-run dry-run-kol dry-run-news \
        test-send test-send-news test-send-kol \
        deploy setup auth \
        run run-kol run-news \
        logs status restart stop

# ─────────────────────────────────────────────
# 默认目标
# ─────────────────────────────────────────────
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "  Web3 News Push — 可用命令"
	@echo ""
	@echo "  ── 本地开发 ───────────────────────────────────────────────"
	@echo "  install          安装 Python 依赖（venv）"
	@echo "  test             运行单元测试"
	@echo "  test-monitor     测试告警模块 → 实际发送到 Telegram"
	@echo ""
	@echo "  ── 本地预览（不发送）──────────────────────────────────────"
	@echo "  dry-run          跑完整 pipeline，打印 digest，不推送"
	@echo "  dry-run-kol      只跑 KOL pipeline，打印 digest，不推送"
	@echo "  dry-run-news     只跑 news pipeline，打印 digest，不推送"
	@echo ""
	@echo "  ── 频道推送测试（真实发送）────────────────────────────────"
	@echo "  test-send        发送测试消息 → news + KOL 两个频道"
	@echo "  test-send-news   发送测试消息 → news 频道"
	@echo "  test-send-kol    发送测试消息 → KOL 频道"
	@echo ""
	@echo "  ── VPS 远程（需 .env.deploy 配置 VPS_HOST / VPS_USER）────"
	@echo "  deploy           推送代码到 VPS 并重启服务"
	@echo "  setup            VPS 一次性初始化（首次部署）"
	@echo "  auth             VPS 上执行 Telegram 首次授权"
	@echo "  run              VPS 立即触发一次完整推送"
	@echo "  run-kol          VPS 只触发 KOL pipeline"
	@echo "  run-news         VPS 只触发 news pipeline"
	@echo "  logs             实时查看 VPS 服务日志"
	@echo "  status           VPS 定时器 + 最近执行状态"
	@echo "  restart          重启 VPS systemd 定时器"
	@echo "  stop             停止 VPS 定时器（不卸载）"
	@echo ""

# ─────────────────────────────────────────────
# 本地开发
# ─────────────────────────────────────────────
install:
	@echo ">>> 创建虚拟环境并安装依赖..."
	python3 -m venv venv
	$(PIP) install --upgrade pip -q
	$(PIP) install -r requirements.txt
	@echo "✅ 依赖安装完成"

test:
	@echo ">>> 运行单元测试..."
	$(PYTHON) -m pytest test/ -v
	@echo "✅ 测试完成"

test-monitor:
	@echo ">>> 测试告警模块（将发送真实 Telegram 消息）..."
	$(PYTHON) test/test_monitor.py
	@echo "✅ 告警测试完成"

# ─────────────────────────────────────────────
# 本地预览（不发送）
# ─────────────────────────────────────────────
dry-run:
	@echo ">>> 本地 dry-run（完整 pipeline，不推送）..."
	$(PYTHON) src/main.py --dry-run

dry-run-kol:
	@echo ">>> 本地 dry-run（KOL only，不推送）..."
	$(PYTHON) src/main.py --dry-run --kol-only

dry-run-news:
	@echo ">>> 本地 dry-run（news only，不推送）..."
	$(PYTHON) src/main.py --dry-run --news-only

# ─────────────────────────────────────────────
# 频道推送测试（真实发送）
# ─────────────────────────────────────────────
test-send:
	@echo ">>> 发送测试消息 → news + KOL 频道..."
	$(PYTHON) src/main.py --test --channel all
	@echo "✅ 测试消息已发送"

test-send-news:
	@echo ">>> 发送测试消息 → news 频道..."
	$(PYTHON) src/main.py --test --channel news
	@echo "✅ 测试消息已发送（news）"

test-send-kol:
	@echo ">>> 发送测试消息 → KOL 频道..."
	$(PYTHON) src/main.py --test --channel kol
	@echo "✅ 测试消息已发送（KOL）"

# ─────────────────────────────────────────────
# VPS 远程操作
# ─────────────────────────────────────────────
deploy:
	@echo ">>> 推送代码到 VPS ($(VPS_USER)@$(VPS_HOST))..."
	@bash deploy/deploy-vps.sh $(VPS_HOST) $(VPS_USER) $(INSTALL_DIR)
	@echo "✅ 部署完成"

setup:
	@echo ">>> 上传初始化脚本到 VPS..."
	scp deploy/setup-vps.sh $(VPS_USER)@$(VPS_HOST):/tmp/setup-vps.sh
	$(SSH) "bash /tmp/setup-vps.sh $(VPS_USER)"
	@echo "✅ VPS 初始化完成"

auth:
	@echo ">>> 在 VPS 上执行 Telegram 授权..."
	$(SSH) "cd $(INSTALL_DIR) && venv/bin/python src/telegram_auth.py"

run:
	@echo ">>> 在 VPS 上触发一次完整推送..."
	$(SSH) "systemctl start web3-news-push@$(VPS_USER)"
	@echo "✅ 已触发，查看日志: make logs"

run-kol:
	@echo ">>> 在 VPS 上触发 KOL pipeline..."
	$(SSH) "cd $(INSTALL_DIR) && venv/bin/python src/main.py --kol-only"

run-news:
	@echo ">>> 在 VPS 上触发 news pipeline..."
	$(SSH) "cd $(INSTALL_DIR) && venv/bin/python src/main.py --news-only"

logs:
	@echo ">>> 实时日志（Ctrl+C 退出）..."
	$(SSH) "journalctl -u 'web3-news-push@*' -f"

status:
	@echo ">>> VPS 定时器状态..."
	$(SSH) "systemctl list-timers 'web3-news-push*' --no-pager && echo '' && journalctl -u 'web3-news-push@*' -n 30 --no-pager"

restart:
	@echo ">>> 重启 VPS systemd 定时器..."
	$(SSH) "systemctl restart web3-news-push.timer"
	@echo "✅ 定时器已重启"

stop:
	@echo ">>> 停止 VPS 定时器..."
	$(SSH) "systemctl stop web3-news-push.timer"
	@echo "✅ 定时器已停止（服务未卸载）"
