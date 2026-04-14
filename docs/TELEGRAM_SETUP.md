# Telegram Scraper Setup Guide

The Telegram scraper allows you to scrape messages from Telegram channels as an additional news source alongside RSS feeds.

## Overview

The scraper uses **Telethon** to fetch recent messages from your subscribed Telegram channels, with optional folder-based filtering. Messages are converted to the same format as RSS articles and processed through the same pipeline.

## Prerequisites

1. **Telegram Account** - You need an active Telegram account
2. **API Credentials** - Get from https://my.telegram.org/apps
3. **Python dependencies** - Already in `requirements.txt`

## Step 1: Get API Credentials

1. Visit https://my.telegram.org/apps
2. Log in with your Telegram account
3. Create a new application (if you haven't already)
4. Note down:
   - **API ID** (integer, e.g., 12345678)
   - **API Hash** (string, e.g., abcdef1234567890...)

## Step 2: Configure Environment Variables

Add to your `.env` file:

```bash
# Telegram Authentication (Required for scraper)
TELEGRAM_API_ID=12345678              # Your API ID from my.telegram.org
TELEGRAM_API_HASH=abcdef1234567890... # Your API Hash from my.telegram.org

# Telegram Scraper Configuration (Optional)
TELEGRAM_SESSION=                     # Auto-saved after first auth (leave empty)
TELEGRAM_FOLDER_ID=                   # Optional: Only scrape specific folder
TELEGRAM_MAX_MESSAGES_PER_CHANNEL=10  # Max messages per channel
TELEGRAM_SCRAPE_HOURS=24              # Look back N hours
```

## Step 3: First-Time Authentication

Run the interactive setup to authenticate:

```bash
python src/telegram_auth.py
```

This will:
1. Prompt for your phone number (international format, e.g., +1234567890)
2. Send a verification code to your Telegram app
3. Prompt you to enter the code
4. Save the session to `~/.config/web3-news-push/telegram_session.txt`

**Important**: You only need to do this once. The session will be reused automatically.

## Step 4: Test the Scraper

Run the test command:

```bash
python src/telegram_scraper.py
```

This will:
- Connect to Telegram using your saved session
- Fetch channels (optionally filtered by folder)
- Scrape recent messages from each channel
- Display sample results

Expected output:
```
🚀 Testing Telegram Scraper

📱 Scraping 5 Telegram channel(s)...
  ✅ CryptoNews: fetched 8 message(s)
  ✅ Web3Daily: fetched 12 message(s)
  ⚠️ PrivateChannel: Private channel (skipping)
✅ Telegram scraping complete: 20 message(s)

✅ Scraped 20 article(s)

1. [TG:CryptoNews] Bitcoin hits new ATH at $75,000...
   URL: https://t.me/cryptonewschannel/12345
   Timestamp: 2024-04-13 08:30:15
   Content: Bitcoin hits new ATH at $75,000 amid ETF inflows...
```

## Step 5: Integration with Main Pipeline

The Telegram scraper is automatically integrated into `scraper.py`. When you run:

```bash
python src/main.py
```

It will:
1. Scrape RSS feeds (as before)
2. Scrape Telegram channels (if configured)
3. Combine all articles and process normally

## Optional: Folder-Based Filtering

If you have many channels and only want to scrape specific ones, use **Telegram folders**:

### How to Find Folder ID:

1. Open Telegram Desktop
2. Create a folder (Settings → Folders → New Folder)
3. Add channels you want to scrape to this folder
4. Run this Python snippet to get the folder ID:

```python
from telethon.sync import TelegramClient
from telegram_auth import get_client

async def list_folders():
    client = get_client()
    await client.connect()
    
    dialogs = await client.get_dialogs()
    folders = {}
    
    for dialog in dialogs:
        folder_id = dialog.folder_id
        if folder_id:
            if folder_id not in folders:
                folders[folder_id] = []
            folders[folder_id].append(dialog.title)
    
    print("Your Telegram folders:")
    for fid, chats in folders.items():
        print(f"\nFolder ID: {fid}")
        print(f"  Channels: {', '.join(chats[:3])}...")
    
    await client.disconnect()

import asyncio
asyncio.run(list_folders())
```

3. Set `TELEGRAM_FOLDER_ID` in `.env` to the desired folder ID

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_API_ID` | Yes* | - | API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | Yes* | - | API Hash from my.telegram.org |
| `TELEGRAM_SESSION` | No | Auto | Session string (auto-saved) |
| `TELEGRAM_FOLDER_ID` | No | All | Filter channels by folder |
| `TELEGRAM_MAX_MESSAGES_PER_CHANNEL` | No | 10 | Max messages per channel |
| `TELEGRAM_SCRAPE_HOURS` | No | 24 | Look back N hours |

\* Only required if you want to use Telegram scraping. The pipeline will skip Telegram and only use RSS if these are missing.

### Message URL Format

Messages are converted to URLs in one of two formats:

1. **Public channels** (with username):
   ```
   https://t.me/{username}/{message_id}
   ```

2. **Private channels** (no username):
   ```
   https://t.me/c/{channel_id}/{message_id}
   ```

### Article Format

Telegram messages are converted to the standard article format:

```python
{
    'title': 'First 100 chars of message...',
    'url': 'https://t.me/channel/12345',
    'content': 'Full message text',
    'timestamp': 1713008400,  # Unix timestamp
    'source': 'TG:ChannelName'
}
```

## Troubleshooting

### "Telegram client not authorized"

**Solution**: Run `python src/telegram_auth.py` to authenticate.

### "Missing Telegram credentials"

**Solution**: Set `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in `.env`.

### "Private channel (skipping)"

**Explanation**: The scraper skips channels you don't have access to. This is normal.

### "Rate limit hit, need to wait Xs"

**Explanation**: Telegram has rate limits. The scraper will log this and skip that channel. Consider reducing `TELEGRAM_MAX_MESSAGES_PER_CHANNEL` or `TELEGRAM_SCRAPE_HOURS`.

### Session expired

**Solution**: Delete `~/.config/web3-news-push/telegram_session.txt` and run `python src/telegram_auth.py` again.

## Security Notes

1. **Session File**: The session file (`telegram_session.txt`) grants access to your Telegram account. Keep it secure and never commit it to git.

2. **API Credentials**: Similarly, never commit your API ID and hash. Use `.env` (which is gitignored).

3. **Permissions**: The scraper only has **read** access. It cannot send messages or modify channels.

4. **Session Sharing**: You can set `TELEGRAM_SESSION` env var to use the same session across multiple machines, but be cautious as this grants Telegram access.

## Advanced: Using Different Accounts

If you want to scrape with a different Telegram account:

1. Clear the current session:
   ```bash
   rm ~/.config/web3-news-push/telegram_session.txt
   ```

2. Run setup again:
   ```bash
   python src/telegram_auth.py
   ```

3. Enter the new account's phone number and code

## Performance Tips

- **Folder filtering**: Use `TELEGRAM_FOLDER_ID` to limit which channels are scraped
- **Message limits**: Reduce `TELEGRAM_MAX_MESSAGES_PER_CHANNEL` if you have many channels
- **Time window**: Adjust `TELEGRAM_SCRAPE_HOURS` based on how often you run the pipeline
- **Rate limits**: Telegram has strict rate limits. If you hit them frequently, reduce the scraping frequency or number of channels.

## Integration with Cron

The scraper works seamlessly with the cron job setup:

```bash
# Daily digest at 8 AM (includes Telegram + RSS)
0 8 * * * cd /path/to/web3-news-push && ./venv/bin/python src/main.py
```

No changes needed - Telegram scraping happens automatically if configured.
