VPS_HOST    ?= $(shell grep -E '^VPS_HOST='    .env.deploy 2>/dev/null | cut -d= -f2)
VPS_USER    ?= $(shell grep -E '^VPS_USER='    .env.deploy 2>/dev/null | cut -d= -f2 || echo root)
INSTALL_DIR ?= $(shell grep -E '^INSTALL_DIR=' .env.deploy 2>/dev/null | cut -d= -f2 || echo /opt/web3-news-push)
SSH         := ssh $(VPS_USER)@$(VPS_HOST)

.PHONY: help \
        install test test-monitor dry-run dry-run-kol dry-run-news \
        deploy setup auth run run-kol run-news logs status restart stop

# ─────────────────────────────────────────────
# 帮助
# ─────────────────────────────────────────────
help:
	@echo ""
	@echo "本地开发命令"
	@echo "  make install        安装 Python 依赖（venv）"
	@echo "  make test           运行本地测试"
	@echo "  make test-monitor   测试告警模块是否能送达 Telegram"
	@echo "  make dry-run        本地跑一遍 pipeline，打印 digest，不发送"
	@echo "  make dry-run-kol    本地只跑 KOL pipeline，打印 digest，不发送"
	@echo "  make dry-run-news   本地只跑 news pipeline，打印 digest，不发送"
	@echo ""
	@echo "VPS 远程命令（需要 .env.deploy 配置 VPS_HOST / VPS_USER）"
	@echo "  make deploy         推送代码更新到 VPS 并重启"
	@echo "  make setup          VPS 一次性初始化（首次部署）"
	@echo "  make auth           VPS 上执行 Telegram 首次授权"
	@echo "  make run            VPS 立即触发一次推送"
	@echo "  make run-kol        VPS 只触发 KOL pipeline"
	@echo "  make run-news       VPS 只触发 news pipeline"
	@echo "  make logs           实时查看 VPS 服务日志"
	@echo "  make status         VPS 定时器 + 最近执行状态"
	@echo "  make restart        重启 VPS systemd 定时器"
	@echo "  make stop           停止 VPS 定时器（不卸载）"
	@echo ""

# ─────────────────────────────────────────────
# 本地开发
# ─────────────────────────────────────────────
install:
	python3 -m venv venv
	venv/bin/pip install -r requirements.txt

test:
	venv/bin/python -m pytest test/ -v

test-monitor:
	venv/bin/python test/test_monitor.py

dry-run:
	venv/bin/python src/main.py --dry-run

dry-run-kol:
	venv/bin/python src/main.py --dry-run --kol-only

dry-run-news:
	venv/bin/python src/main.py --dry-run --news-only

# ─────────────────────────────────────────────
# VPS 远程操作
# ─────────────────────────────────────────────
deploy:
	@bash deploy/deploy-vps.sh $(VPS_HOST) $(VPS_USER) $(INSTALL_DIR)

setup:
	@echo ">>> 上传初始化脚本到 VPS..."
	scp deploy/setup-vps.sh $(VPS_USER)@$(VPS_HOST):/tmp/setup-vps.sh
	$(SSH) "bash /tmp/setup-vps.sh $(VPS_USER)"

auth:
	$(SSH) "cd $(INSTALL_DIR) && venv/bin/python src/telegram_auth.py"

run:
	$(SSH) "systemctl start web3-news-push@$(VPS_USER)"

run-kol:
	$(SSH) "cd $(INSTALL_DIR) && venv/bin/python src/main.py --kol-only"

run-news:
	$(SSH) "cd $(INSTALL_DIR) && venv/bin/python src/main.py --news-only"

logs:
	$(SSH) "journalctl -u 'web3-news-push@*' -f"

status:
	$(SSH) "systemctl list-timers 'web3-news-push*' --no-pager && echo '' && journalctl -u 'web3-news-push@*' -n 30 --no-pager"

restart:
	$(SSH) "systemctl restart web3-news-push.timer"

stop:
	$(SSH) "systemctl stop web3-news-push.timer"
