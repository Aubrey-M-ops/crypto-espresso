![banner](assets/banner.svg)

# web3-news-push

每日自动抓取主流加密货币新闻，Claude AI 生成大白话中文摘要，自动推送 Telegram 频道。

---

## 功能状态

**核心功能 (100%)**

| 功能 | 状态 |
|------|------|
| RSS 新闻抓取（CoinDesk / CoinTelegraph / Decrypt） | ✅ |
| AI 中文摘要生成（Claude Sonnet） | ✅ |
| 智能分类（必读 / 进阶） | ✅ |
| Telegram 自动推送 | ✅ |
| 去重机制（7 天哈希窗口） | ✅ |

**Telegram KOL 抓取（代码完成，待配置）**

| 功能 | 状态 |
|------|------|
| Telethon 认证模块 | ✅ |
| 频道消息抓取 | ✅ |
| 内容过滤 | ✅ |
| API 凭证配置 | ⏳ |

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
ANTHROPIC_API_KEY=sk-ant-...        # Claude API Key
TELEGRAM_BOT_TOKEN=...              # Telegram Bot Token
TELEGRAM_CHANNEL_ID=@yourchannel   # 频道 ID
TELEGRAM_API_ID=...                 # Telegram App ID（来自 my.telegram.org）
TELEGRAM_API_HASH=...               # Telegram App Hash
```

### 3. 测试运行

```bash
python src/main.py --dry-run
```

### 4. 定时部署（OpenClaw Cron）

将 `openclaw-cron.yaml` 中的配置添加到 `~/.openclaw/config.yaml`，每天早上 8 点自动推送。

详细步骤见 [docs/DEPLOY.md](docs/DEPLOY.md)。


---

## 输出示例

```
🌅 今日加密货币新闻 | 2026-04-13

🟢 必读

📰 大白话总结：比特币价格突破10万美元，创历史新高

📖 术语高亮：
  - ATH = All-Time High，历史最高价

🏷️ #比特币

💡 延伸一问：如果比特币继续上涨，传统金融机构会如何应对？

─────────────────

🔵 进阶

[技术深度文章...]
```

---

## 调试

```bash
# 查看运行日志
tail -f ~/.openclaw/logs/cron.log | grep "web3-news"

# 手动执行一次
python src/main.py

# 检查去重数据库
sqlite3 db/articles.db "SELECT title, timestamp FROM seen_articles ORDER BY timestamp DESC LIMIT 10;"
```

---

## 技术栈

- **Python 3.11+**
- **feedparser** — RSS 解析
- **httpx** — 异步 HTTP
- **anthropic** — Claude API
- **telethon** — Telegram KOL 抓取
- **SQLite** — 本地去重存储
- **OpenClaw** — 定时调度 + Bot 推送

## 成本参考

- Claude API：约 $0.05–0.10 / 天（处理 5–10 篇文章）
- 无需额外服务器：本地 OpenClaw 实例运行

---

## 文档

- [技术设计](docs/project-design.md)
- [部署指南](docs/DEPLOY.md)
- [Telegram 配置](docs/telegram-setup.md)

## License

MIT
