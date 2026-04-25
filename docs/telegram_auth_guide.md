# Telegram Authentication Guide

This guide explains how to use the `telegram_auth.py` module for authenticating with Telegram using Telethon.

## Overview

The `telegram_auth` module provides:
- 📱 **Phone-based authentication** with Telegram
- 💾 **Session persistence** (avoid re-login on every run)
- 🔐 **2FA support** (if you have two-factor authentication enabled)
- 🛡️ **Error handling** with retry logic
- 📝 **Logging** for debugging and monitoring

## Prerequisites

### 1. Get Telegram API Credentials

Before using this module, you need to obtain API credentials from Telegram:

1. Visit https://my.telegram.org
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application (or use existing one)
5. Copy your `api_id` (numeric) and `api_hash` (string)

### 2. Configure Environment Variables

Add these to your `.env` file:

```bash
# Telegram Authentication
TELEGRAM_API_ID=12345678              # Your numeric API ID
TELEGRAM_API_HASH=abcdef1234567890... # Your API hash
TELEGRAM_PHONE=+1234567890            # Your phone number (include country code with +)
```

**Important:** 
- Phone number MUST be in international format: `+[country code][number]`
- Example: `+1234567890` for a US number
- Do NOT include spaces or dashes

### 3. Install Dependencies

```bash
pip install telethon python-dotenv
```

Or install all project requirements:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage (Recommended)

Use the convenience function for simple cases:

```python
import asyncio
from telegram_auth import get_client

async def main():
    # Get authenticated client (reads credentials from .env)
    client = await get_client()
    
    # Use the client
    me = await client.get_me()
    print(f"Logged in as: {me.first_name}")
    
    # Send a message
    await client.send_message('me', 'Hello from my bot!')
    
    # Don't forget to disconnect
    await client.disconnect()

# Run
asyncio.run(main())
```

### Advanced Usage (Custom Configuration)

For more control, use the `TelegramAuth` class:

```python
import asyncio
from telegram_auth import TelegramAuth
from pathlib import Path

async def main():
    # Initialize with custom settings
    auth = TelegramAuth(
        api_id=12345678,
        api_hash="your_hash_here",
        phone="+1234567890",
        session_path=Path("./custom/path/session.session")
    )
    
    # Get client
    client = await auth.get_client()
    
    # Use client...
    
    # Disconnect when done
    await auth.disconnect()

asyncio.run(main())
```

## Authentication Flow

### First Run (New Session)

When you run the code for the first time:

1. **Code Request**: A verification code is sent to your Telegram app
2. **Console Prompt**: You'll see:
   ```
   🔐 Enter the 5-digit code from Telegram (attempt 1/3):
   ```
3. **Enter Code**: Check your Telegram app and enter the code
4. **2FA (if enabled)**: If you have 2FA, you'll be prompted:
   ```
   🔒 Enter your 2FA password (attempt 1/3):
   ```
5. **Session Saved**: Once authenticated, session is saved to `./sessions/telegram.session`

### Subsequent Runs

The module automatically reuses the saved session - **no code needed**! 🎉

## Session Management

### Session Storage

By default, sessions are stored in:
```
./sessions/telegram.session
```

This file contains encrypted session data. Keep it **secure** - it allows login without your password!

### Logout & Delete Session

To force re-authentication:

```python
import asyncio
from telegram_auth import TelegramAuth

async def logout():
    auth = TelegramAuth()
    await auth.logout()  # Removes session file

asyncio.run(logout())
```

## Testing

The module includes a built-in test:

```bash
python src/telegram_auth.py
```

This will:
1. Authenticate (or use existing session)
2. Display your user info
3. Send a test message to "Saved Messages"
4. Disconnect cleanly

Expected output:
```
============================================================
TELEGRAM AUTHENTICATION TEST
============================================================
2024-04-13 22:30:00 - telegram_auth - INFO - Initialized TelegramAuth for +1234567890 (session: sessions/telegram.session)
2024-04-13 22:30:01 - telegram_auth - INFO - ✅ Already authorized (using existing session)

✅ Successfully authenticated!
   Name: John Doe
   Username: @johndoe
   Phone: +1234567890
   User ID: 123456789

📤 Sending test message to Saved Messages...
✅ Message sent successfully!

✅ Test complete!
```

## Integration with Main Project

### Example: Send Daily Digest

```python
import asyncio
from telegram_auth import get_client

async def send_digest(chat_id: int, message: str):
    """Send formatted digest to Telegram channel."""
    client = await get_client()
    
    try:
        await client.send_message(chat_id, message, parse_mode='markdown')
        print(f"✅ Sent digest to {chat_id}")
    finally:
        await client.disconnect()

# Usage
asyncio.run(send_digest(-1001234567890, "**Daily Web3 News**\n\n..."))
```

### Example: Fetch Channel Messages

```python
import asyncio
from telegram_auth import get_client

async def get_recent_messages(channel_id: int, limit: int = 10):
    """Fetch recent messages from a channel."""
    client = await get_client()
    
    try:
        messages = await client.get_messages(channel_id, limit=limit)
        for msg in messages:
            print(f"{msg.date}: {msg.text}")
    finally:
        await client.disconnect()

asyncio.run(get_recent_messages(-1001234567890))
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ValueError: TELEGRAM_API_ID not found` | Missing API credentials | Add to `.env` file |
| `PhoneCodeInvalidError` | Wrong verification code | Re-enter code (3 attempts) |
| `PhoneCodeExpiredError` | Code expired (5 min timeout) | Restart authentication |
| `SessionPasswordNeededError` | 2FA enabled | Enter your 2FA password |
| `FloodWaitError` | Too many requests | Wait the specified seconds |

### Handling Errors in Code

```python
import asyncio
from telegram_auth import get_client, TelegramAuthError

async def safe_send():
    try:
        client = await get_client()
        await client.send_message('me', 'Hello!')
        await client.disconnect()
        
    except TelegramAuthError as e:
        print(f"Authentication failed: {e}")
        # Handle auth failure (e.g., notify admin)
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Handle other errors
```

## Security Best Practices

1. **Never commit `.env` to git** - Add to `.gitignore`
2. **Keep session files secure** - They're equivalent to login credentials
3. **Use environment variables** - Don't hardcode credentials
4. **Rotate API keys periodically** - Revoke old keys on my.telegram.org
5. **Enable 2FA** - Extra security layer for your account

## Troubleshooting

### "Phone number invalid"

Ensure format is correct: `+[country code][number]` with NO spaces.

✅ Correct: `+12025551234`  
❌ Wrong: `2025551234`, `+1 202 555 1234`, `+1-202-555-1234`

### "Session file corrupt"

Delete the session and re-authenticate:
```bash
rm ./sessions/telegram.session
python src/telegram_auth.py
```

### "Cannot find .env file"

Ensure `.env` is in the project root directory.

### "Module not found: telethon"

Install dependencies:
```bash
pip install telethon
```

## API Reference

### `TelegramAuth` Class

```python
class TelegramAuth:
    def __init__(
        self,
        api_id: Optional[int] = None,
        api_hash: Optional[str] = None,
        phone: Optional[str] = None,
        session_path: Optional[Path] = None
    )
```

**Methods:**
- `async get_client() -> TelegramClient` - Get authenticated client
- `async disconnect()` - Close connection
- `async logout()` - Logout and delete session

### `get_client()` Function

```python
async def get_client(
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
    phone: Optional[str] = None
) -> TelegramClient
```

Convenience function that creates `TelegramAuth` instance and returns client.

## Resources

- [Telethon Documentation](https://docs.telethon.dev/)
- [Telegram API](https://my.telegram.org)
- [Python asyncio Guide](https://docs.python.org/3/library/asyncio.html)

## License

Part of the web3-news-push project.
