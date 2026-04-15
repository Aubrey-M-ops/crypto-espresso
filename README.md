![banner](assets/banner.svg)

# web3-news-push

[**➜ 订阅频道：t.me/morningm_news**](https://t.me/morningm_news)

本项目是 Telegram 频道 [@morningm_news](https://t.me/morningm_news) 的开源推送源码。每天 08:00 和 17:00 自动抓取主流加密货币新闻，用我这种丈育也能看懂的语言总结，适合地铁看手机的时候汲取碎片信息。

---

## 功能

| 功能 | 状态 |
|------|------|
| RSS 新闻抓取（CoinDesk / CoinTelegraph / Decrypt） | ✅ |
| AI 中文摘要生成（Claude Sonnet） | ✅ |
| 智能分类（必读 / 进阶） | ✅ |
| Telegram 自动推送 | ✅ |
| 去重机制（7 天哈希窗口） | ✅ |
| 每日 08:00 + 17:00 定时推送 | ✅ |
| Telegram KOL 频道抓取 | ✅ |

---

## 快速开始（自部署）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY、TELEGRAM_BOT_TOKEN、TELEGRAM_CHANNEL_ID
```

### 3. 测试运行

```bash
python src/main.py --dry-run
```

### 4. 安装定时任务

```bash
chmod +x run.sh
(crontab -l 2>/dev/null; echo "0 8,17 * * * $(pwd)/run.sh") | crontab -
```

详细步骤见 [docs/DEPLOY.md](docs/DEPLOY.md)。

---

## 输出示例

```
🌅 今日加密货币新闻 | 2026-04-14

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

## 技术栈

- **Python 3.10+**
- **feedparser** — RSS 解析
- **httpx** — HTTP 请求
- **anthropic** — Claude API
- **telethon** — Telegram KOL 抓取
- **SQLite** — 本地去重存储
- **cron** — 定时调度


## 文档

- [部署指南](docs/DEPLOY.md)
- [技术设计](docs/project-design.md)
- [Telegram 配置](docs/telegram-setup.md)

