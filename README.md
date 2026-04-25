![banner](assets/banner.svg)

# web3-news-push

<div align="right">
  <a href="README.zh.md">中文</a>
</div>

> **Subscribe:** [t.me/morningm_news](https://t.me/morningm_news)

Open-source backend for the Telegram channel [@morningm_news](https://t.me/morningm_news). Twice a day it scrapes the top crypto news, summarises everything in plain language with Claude AI, and pushes a digest to Telegram — so you can stay informed during your morning commute.

---

## Features

| Feature | Status |
|---------|--------|
| RSS scraping — CoinTelegraph, Decrypt, The Block | ✅ |
| AI summaries in plain Chinese (Claude Sonnet) | ✅ |
| Smart classification — Must-Read vs Advanced | ✅ |
| Automatic Telegram push | ✅ |
| 7-day hash deduplication | ✅ |
| Scheduled at 08:00 & 17:00 daily | ✅ |
| Telegram KOL channel scraping | ✅ |

---

## Sample Output

```
🌅 Crypto News Digest | 2026-04-25

🟢 Must-Read

📰 Plain summary: Bitcoin breaks $100K for the first time, setting a new ATH.

📖 Terms:
  - ATH = All-Time High, the highest price ever recorded

🏷️ #Bitcoin

💡 Think about it: If Bitcoin keeps rising, how will traditional banks respond?

─────────────────

🔵 Advanced

[In-depth technical articles...]
```

---

## Self-Hosting

### 1. Install dependencies

```bash
make install
```

### 2. Configure secrets

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_NEWS_CHANNEL_ID` | News channel ID |
| `TELEGRAM_KOL_CHANNEL_ID` | KOL channel ID |
| `TELEGRAM_API_ID` | Telegram API ID (KOL scraping) |
| `TELEGRAM_PHONE` | Phone number (KOL scraping) |

### 3. Test locally (no send)

```bash
make dry-run        # full pipeline, print only
make dry-run-news   # news channel only
make dry-run-kol    # KOL channel only
```

### 4. Test Telegram push

```bash
make test-send        # send test message to both channels
make test-send-news   # news channel only
make test-send-kol    # KOL channel only
```

### 5. Deploy to VPS

```bash
# One-time setup
make setup

# Push code and restart
make deploy
```

See [docs/DEPLOY.md](docs/DEPLOY.md) for the full VPS guide.

---

## Make Commands

```
── Local dev ──────────────────────────────────────
  install          Install Python dependencies (venv)
  test             Run unit tests
  test-monitor     Test alert module → real Telegram send

── Preview (no send) ──────────────────────────────
  dry-run          Full pipeline, print digest, no push
  dry-run-kol      KOL pipeline only, no push
  dry-run-news     News pipeline only, no push

── Push tests (real send) ─────────────────────────
  test-send        Send test message → both channels
  test-send-news   Send test message → news channel
  test-send-kol    Send test message → KOL channel

── VPS remote ─────────────────────────────────────
  deploy           Push code to VPS and restart
  setup            One-time VPS initialization
  auth             Telegram first-time auth on VPS
  run              Trigger a full push on VPS now
  run-kol          Trigger KOL pipeline on VPS
  run-news         Trigger news pipeline on VPS
  logs             Stream VPS service logs
  status           VPS timer + recent run status
  restart          Restart VPS systemd timer
  stop             Stop VPS timer (keep installed)
```

---

## Tech Stack

| Layer | Library |
|-------|---------|
| Language | Python 3.10+ |
| RSS parsing | feedparser |
| HTTP | httpx |
| AI summaries | anthropic (Claude Sonnet) |
| KOL scraping | telethon |
| Deduplication | SQLite |
| Scheduling | cron / systemd |

---

## Docs

- [Deploy Guide](docs/DEPLOY.md)
- [Technical Design](docs/project-design.md)
- [Telegram Setup](docs/telegram-setup.md)

---

## License

MIT
