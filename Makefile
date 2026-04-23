VPS_HOST ?= $(shell grep -E '^VPS_HOST=' .env.deploy 2>/dev/null | cut -d= -f2)
VPS_USER ?= $(shell grep -E '^VPS_USER=' .env.deploy 2>/dev/null | cut -d= -f2 || echo root)
INSTALL_DIR ?= $(shell grep -E '^INSTALL_DIR=' .env.deploy 2>/dev/null | cut -d= -f2 || echo /opt/web3-news-push)
SSH := ssh $(VPS_USER)@$(VPS_HOST)

.PHONY: help deploy setup auth run logs status

help:
	@echo "用法:"
	@echo "  make deploy       推送代码更新到 VPS"
	@echo "  make setup        VPS 一次性初始化（首次部署）"
	@echo "  make auth         VPS 上执行 Telegram 首次授权"
	@echo "  make run          立即在 VPS 触发一次推送"
	@echo "  make logs         实时查看 VPS 日志"
	@echo "  make status       查看 VPS 定时器状态"

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

logs:
	$(SSH) "journalctl -u 'web3-news-push@*' -f"

status:
	$(SSH) "systemctl list-timers web3-news-push.timer --no-pager"
