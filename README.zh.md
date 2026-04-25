![banner](assets/banner.svg)

# web3-news-push

<div align="right">
  <a href="README.md">English</a>
</div>

> **订阅频道：** [t.me/morningm_news](https://t.me/morningm_news)

本项目是 Telegram 频道 [@morningm_news](https://t.me/morningm_news) 的开源推送源码。每天 08:00 和 17:00 自动抓取主流加密货币新闻，用 Claude AI 生成大白话中文摘要并推送到 Telegram，适合地铁上汲取碎片信息。

---

## 功能

| 功能 | 状态 |
|------|------|
| RSS 新闻抓取（CoinTelegraph / Decrypt / The Block） | ✅ |
| AI 中文摘要生成（Claude Sonnet） | ✅ |
| 智能分类（必读 / 进阶） | ✅ |
| Telegram 自动推送 | ✅ |
| 去重机制（7 天哈希窗口） | ✅ |
| 每日 08:00 + 17:00 定时推送 | ✅ |
| Telegram KOL 频道抓取 | ✅ |

---

## 输出示例

```
🌅 今日加密货币新闻 | 2026-04-25

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

## 自部署

### 1. 安装依赖

```bash
make install
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填写以下内容：

| 变量 | 说明 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_NEWS_CHANNEL_ID` | 新闻频道 ID |
| `TELEGRAM_KOL_CHANNEL_ID` | KOL 频道 ID |
| `TELEGRAM_API_ID` | Telegram API ID（KOL 抓取用） |
| `TELEGRAM_PHONE` | 手机号（KOL 抓取用） |

### 3. 本地预览（不发送）

```bash
make dry-run        # 完整 pipeline，打印 digest
make dry-run-news   # 只跑 news pipeline
make dry-run-kol    # 只跑 KOL pipeline
```

### 4. 测试 Telegram 推送

```bash
make test-send        # 发送测试消息到两个频道
make test-send-news   # 只发到 news 频道
make test-send-kol    # 只发到 KOL 频道
```

### 5. 部署到 VPS

```bash
# 首次初始化
make setup

# 推送代码并重启
make deploy
```

详细步骤见 [docs/DEPLOY.md](docs/DEPLOY.md)。

---

## Make 命令速查

```
── 本地开发 ────────────────────────────────────────
  install          安装 Python 依赖（venv）
  test             运行单元测试
  test-monitor     测试告警模块 → 实际发送到 Telegram

── 本地预览（不发送）──────────────────────────────
  dry-run          跑完整 pipeline，打印 digest，不推送
  dry-run-kol      只跑 KOL pipeline，不推送
  dry-run-news     只跑 news pipeline，不推送

── 频道推送测试（真实发送）───────────────────────
  test-send        发送测试消息 → news + KOL 两个频道
  test-send-news   发送测试消息 → news 频道
  test-send-kol    发送测试消息 → KOL 频道

── VPS 远程 ────────────────────────────────────────
  deploy           推送代码到 VPS 并重启服务
  setup            VPS 一次性初始化（首次部署）
  auth             VPS 上执行 Telegram 首次授权
  run              VPS 立即触发一次完整推送
  run-kol          VPS 只触发 KOL pipeline
  run-news         VPS 只触发 news pipeline
  logs             实时查看 VPS 服务日志
  status           VPS 定时器 + 最近执行状态
  restart          重启 VPS systemd 定时器
  stop             停止 VPS 定时器（不卸载）
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| RSS 解析 | feedparser |
| HTTP | httpx |
| AI 摘要 | anthropic（Claude Sonnet） |
| KOL 抓取 | telethon |
| 去重存储 | SQLite |
| 定时调度 | cron / systemd |

---

## 文档

- [部署指南](docs/DEPLOY.md)
- [技术设计](docs/project-design.md)
- [Telegram 配置](docs/telegram-setup.md)

---

## 许可证

MIT
