# OpenClaw Crypto News Telegram Bot - Project Design

## Overview

A **daily crypto news push service** delivered via Telegram bot. The service scrapes news from major crypto sources, uses AI to generate beginner-friendly summaries in Chinese, and pushes a structured digest every morning to subscribers.

**Core principle:** Make crypto news accessible to non-technical audiences through plain-language summaries, jargon explanations, category tags, and guided thinking questions.

---

## Design Decisions

### 1. Scheduling Strategy

**Recommendation: OpenClaw Cron Job**

Rationale:
- Native integration with OpenClaw's `sessions_spawn` for isolated execution
- Consistent with existing OpenClaw skills architecture
- Easy monitoring and debugging through OpenClaw session logs
- No external dependencies (GitHub Actions, Cloud Scheduler, etc.)

**Cron configuration:**
```yaml
cron:
  - schedule: "0 8 * * *"  # Daily at 8:00 AM
    task: "Run crypto news digest scraper and send to Telegram"
    runtime: "subagent"
    agentId: "main"
    timeoutSeconds: 600
```

### 2. News Source Selection

**Selected sources:** CoinDesk, CoinTelegraph, Decrypt, The Block

| Source | URL | Focus | Scraping Method |
|--------|-----|-------|----------------|
| CoinDesk | coindesk.com | General crypto, institutional | RSS feed |
| CoinTelegraph | cointelegraph.com | Breaking news, broad coverage | RSS feed |
| Decrypt | decrypt.co | Consumer-friendly, NFT/Web3 | RSS feed |
| The Block | theblock.co | Research-grade, DeFi/finance | RSS feed (fallback: HTML) |

**Rationale:**
- RSS feeds preferred over HTML scraping for stability and rate-limit avoidance
- Coverage spans institutional, consumer, and technical audiences
- Chinese crypto audiences rely heavily on these sources

### 3. AI Summary Format

**Recommendation: Structured Prompt with Fixed Taxonomy**

Each article is processed into this format:

```
📰 大白话总结：<one sentence, zero jargon>

📖 术语高亮：
  - <Term> = <one-line plain explanation>
  - <Term> = <one-line plain explanation>

🏷️ 分类标签：#监管 | #比特币 | #以太坊 | #DeFi | #新项目 | #宏观经济

💡 延伸一问：<one thinking question that builds curiosity>
```

**Fixed tag taxonomy:**
- `#监管` (Regulation)
- `#比特币` (Bitcoin)
- `#以太坊` (Ethereum)
- `#DeFi` (DeFi)
- `#新项目` (New Projects)
- `#宏观经济` (Macroeconomics)

**Rationale:**
- Consistent structure enables easy parsing and reader familiarity
- Fixed tags prevent taxonomy bloat and improve searchability
- Thinking questions build engagement beyond passive consumption

### 4. Article Classification

**Recommendation: Two-tier system**

**🟢 必读 (Must-Read)** — 2–3 articles
- Selection criteria: highest market/regulatory impact; understandable without prior knowledge
- Target audience: crypto beginners; zero assumed knowledge

**🔵 进阶 (Advanced)** — remaining articles
- Selection criteria: technical depth, protocol-level changes, research
- Target audience: readers with basic crypto knowledge

**Classification algorithm:**
- LLM assigns a "beginner-friendliness" score (1-10) to each article
- Top 2-3 highest-scoring articles → Must-Read
- Remaining → Advanced
- Tie-breaking: prioritize regulatory/market-moving news

### 5. Message Delivery

**Recommendation: Single consolidated message per day**

**Format:**
```
🌅 今日加密货币新闻 | YYYY-MM-DD

🟢 必读
[Article 1]
[Article 2]
[Article 3]

🔵 进阶
[Article 4]
[Article 5]
...
```

**Rationale:**
- Single message avoids notification spam
- Clear visual separation between tiers
- Telegram's 4096-char limit requires chunking if digest exceeds limit (split by tier)

### 6. Deduplication Strategy

**Recommendation: Content-hash based deduplication**

```python
import hashlib

def article_hash(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()[:16]
```

**Storage:**
- SQLite database with `seen_articles` table
- Schema: `(hash TEXT PRIMARY KEY, timestamp INTEGER)`
- Retention: 7 days (auto-delete older entries)

**Rationale:**
- Title+URL hash catches cross-source duplicates
- 7-day retention balances storage and collision avoidance
- SQLite sufficient for single-user/small-group deployment

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         OpenClaw Cron Trigger (daily 8:00 AM)        │
└─────────────────┬───────────────────────────────────┘
                  │
         ┌────────▼────────┐
         │  News Scraper   │  ← feedparser + httpx
         │  (4 sources)    │     RSS preferred
         └────────┬────────┘
                  │  raw articles
         ┌────────▼────────┐
         │  Deduplicator   │  ← SQLite hash lookup
         └────────┬────────┘
                  │  unique articles
         ┌────────▼────────┐
         │   AI Summarizer │  ← Claude API (sonnet-4-5)
         │  (structured)   │     Parallel processing
         └────────┬────────┘
                  │  summaries + scores
         ┌────────▼────────┐
         │  Classifier     │  ← Sort by beginner score
         └────────┬────────┘
                  │  Must-Read vs Advanced
         ┌────────▼────────┐
         │  Digest Builder │  ← Format Telegram message
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  Telegram Push  │  ← message tool (OpenClaw)
         └─────────────────┘
```

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Scraping | `feedparser` + `httpx` | Stable RSS parsing; async HTTP |
| AI | Claude API (`claude-sonnet-4-5`) | Best Chinese summarization quality |
| Deduplication | SQLite | Lightweight; sufficient for single-deployment |
| Telegram | OpenClaw `message` tool | Native integration; no external bot library needed |
| Scheduler | OpenClaw cron | Built-in; zero external dependencies |
| Language | Python 3.11+ | Best ecosystem for RSS/AI/data processing |

---

## Project Directory Structure

```
openclaw-telebot/
  docs/
    project-design.md         ← this file
  src/
    scraper.py                ← fetch articles from all sources
    dedup.py                  ← hash-based deduplication
    summarizer.py             ← LLM integration (Claude API)
    classifier.py             ← Must-Read vs Advanced logic
    digest.py                 ← format final message
    main.py                   ← entry point for cron job
  db/
    articles.db               ← SQLite database (gitignored)
  tests/
    test_scraper.py
    test_summarizer.py
  .env.example                ← template for secrets
  requirements.txt
  README.md
```

---

## Environment Variables

```bash
# Required
TELEGRAM_CHANNEL_ID=-1001234567890    # target chat/channel ID
ANTHROPIC_API_KEY=sk-ant-...          # Claude API key

# Optional
PUSH_TIME=08:00                       # cron schedule override (default: 08:00)
MAX_ARTICLES=10                       # max articles to process (default: 10)
MUST_READ_COUNT=3                     # number of Must-Read articles (default: 3)
DB_PATH=./db/articles.db              # SQLite path (default: ./db/articles.db)
```

---

## LLM Prompt Template

```
You are a crypto news translator and educator for Chinese-speaking beginners.

Given this article:
Title: {title}
URL: {url}
Content: {content}

Produce this structured output in Chinese:

📰 大白话总结：[One sentence summary using ZERO technical jargon]

📖 术语高亮：
  - [Term 1] = [10-word max plain explanation]
  - [Term 2] = [10-word max plain explanation]

🏷️ 分类标签：[SELECT EXACTLY ONE: #监管 | #比特币 | #以太坊 | #DeFi | #新项目 | #宏观经济]

💡 延伸一问：[One open-ended thinking question connecting to real-world impact]

BEGINNER_SCORE: [1-10, where 10 = understandable to someone with zero crypto knowledge]
```

---

## Implementation Phases

### Phase 1: Core Scraping + Deduplication (Week 1)
- [ ] Implement RSS scraper for 4 sources
- [ ] SQLite schema + hash-based dedup
- [ ] Basic article struct (title, url, content, timestamp)
- [ ] Unit tests for scraper

### Phase 2: AI Summarization (Week 2)
- [ ] Claude API integration
- [ ] Prompt engineering for structured output
- [ ] Parallel processing for multiple articles
- [ ] Error handling (API rate limits, malformed outputs)

### Phase 3: Classification + Digest (Week 3)
- [ ] Implement beginner-score-based classifier
- [ ] Digest builder (format Telegram message)
- [ ] Handle message chunking if > 4096 chars
- [ ] Test with sample articles

### Phase 4: Telegram + OpenClaw Integration (Week 4)
- [ ] Integrate OpenClaw `message` tool
- [ ] Configure cron job in OpenClaw config
- [ ] Test end-to-end flow
- [ ] Monitoring and error logging

### Phase 5: Polish + Deployment (Week 5)
- [ ] Create SKILL.md for OpenClaw agents
- [ ] Documentation (README, setup guide)
- [ ] Dry-run mode for testing
- [ ] Production deployment

---

## Error Handling

| Failure Scenario | Mitigation |
|------------------|------------|
| RSS feed down | Skip source; log warning; continue with others |
| LLM API rate limit | Exponential backoff; reduce batch size if needed |
| Duplicate articles | Hash check before processing; skip silently |
| Telegram API failure | Retry 3x with backoff; log error if all fail |
| No new articles | Send "No new articles today" message (optional) |
| Message > 4096 chars | Split into Must-Read and Advanced chunks |

---

## Success Metrics

**Definition of Done:**
1. Bot runs automatically each morning at 08:00 without manual intervention
2. Summaries are understandable to a crypto newcomer in < 2 minutes
3. Must-Read section contains exactly 2-3 articles
4. Zero duplicate articles in a 7-day window
5. Messages deliver to Telegram channel within 5 minutes of cron trigger

**Monitoring:**
- OpenClaw session logs for cron job execution
- SQLite row count (articles processed)
- Telegram message delivery confirmation

---

## Common Pitfalls

| Mistake | Fix |
|---------|-----|
| Scraping full HTML when RSS available | Check for `/rss` or `/feed` paths first |
| LLM outputs inconsistent format | Use JSON mode or strict few-shot examples |
| Ignoring rate limits | Add delays; use batch processing |
| Timezone confusion | Always use UTC internally; convert for display |
| Hardcoded channel ID | Use environment variable |

---

## Future Enhancements

- **User subscriptions:** Allow users to subscribe/unsubscribe via bot commands
- **Custom preferences:** Filter by tags (#DeFi only, etc.)
- **Web dashboard:** View historical digests
- **Multi-language support:** English, Japanese, Korean
- **Sentiment analysis:** Tag articles as bullish/bearish/neutral
