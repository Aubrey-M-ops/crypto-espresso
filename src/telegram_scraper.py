#!/usr/bin/env python3
"""
Telegram Channel Scraper

Scrapes recent messages from configured Telegram channels using Telethon.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import Message
from dotenv import load_dotenv

from telegram_auth import TelegramAuth

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# Default channels to scrape (can be overridden by env var)
DEFAULT_CHANNELS = [
    # Example channels (replace with real KOL channels)
    # "crypto_news_channel",
    # "bitcoin_updates",
    # "defi_alpha"
]


async def scrape_channel(
    client: TelegramClient,
    channel: str,
    hours: int = 24,
    limit: int = 50
) -> List[Dict]:
    """
    Scrape recent messages from a Telegram channel.
    
    Args:
        client: Authenticated TelegramClient
        channel: Channel username (without @) or numeric ID
        hours: How many hours back to scrape
        limit: Maximum messages to fetch
    
    Returns:
        List of message dicts with keys: title, content, url, source, timestamp
    """
    messages = []
    
    try:
        # Calculate time threshold
        time_threshold = datetime.now() - timedelta(hours=hours)
        
        logger.info(f"   Scraping @{channel} (last {hours}h, max {limit} msgs)...")
        
        # Fetch messages
        async for message in client.iter_messages(channel, limit=limit):
            # Skip if too old
            if message.date.replace(tzinfo=None) < time_threshold:
                break
            
            # Skip non-text messages
            if not message.text:
                continue
            
            # Extract content
            text = message.text.strip()
            
            # Skip very short messages (likely not informative)
            if len(text) < 50:
                continue
            
            # Build message dict
            msg_dict = {
                'title': text[:100] + ('...' if len(text) > 100 else ''),  # First 100 chars as title
                'content': text,
                'url': f"https://t.me/{channel}/{message.id}",
                'source': f"Telegram/{channel}",
                'timestamp': message.date.isoformat()
            }
            
            messages.append(msg_dict)
        
        logger.info(f"   ✅ Scraped {len(messages)} messages from @{channel}")
        
    except Exception as e:
        logger.error(f"   ❌ Failed to scrape @{channel}: {e}")
    
    return messages


async def scrape_telegram_sources(
    channels: Optional[List[str]] = None,
    hours: int = 24,
    limit_per_channel: int = 50
) -> List[Dict]:
    """
    Scrape messages from multiple Telegram channels.
    
    Configuration:
        TELEGRAM_CHANNELS: Comma-separated list of channel usernames (env var)
        TELEGRAM_API_ID: Telegram API ID (required)
        TELEGRAM_API_HASH: Telegram API hash (required)
        TELEGRAM_PHONE: Phone number for authentication (required)
    
    Args:
        channels: List of channel usernames (without @). 
                 If None, reads from TELEGRAM_CHANNELS env var.
        hours: How many hours back to scrape (default: 24)
        limit_per_channel: Max messages per channel (default: 50)
    
    Returns:
        List of all scraped messages from all channels
    
    Example:
        >>> messages = await scrape_telegram_sources(
        ...     channels=['crypto_news', 'bitcoin_updates'],
        ...     hours=12
        ... )
        >>> print(f"Scraped {len(messages)} messages")
    """
    # Get channels from parameter or environment
    if channels is None:
        env_channels = os.getenv('TELEGRAM_CHANNELS', '').strip()
        if env_channels:
            channels = [ch.strip() for ch in env_channels.split(',')]
        else:
            channels = DEFAULT_CHANNELS
    
    if not channels:
        logger.warning("No Telegram channels configured. Set TELEGRAM_CHANNELS env var.")
        return []
    
    logger.info(f"Scraping {len(channels)} Telegram channel(s)...")
    
    all_messages = []
    auth = None
    
    try:
        # Authenticate
        auth = TelegramAuth()
        client = await auth.get_client()
        
        # Scrape each channel
        for channel in channels:
            channel = channel.strip().lstrip('@')  # Remove @ if present
            
            if not channel:
                continue
            
            channel_messages = await scrape_channel(
                client=client,
                channel=channel,
                hours=hours,
                limit=limit_per_channel
            )
            
            all_messages.extend(channel_messages)
        
        logger.info(f"✅ Total scraped: {len(all_messages)} messages from {len(channels)} channel(s)")
        
    except Exception as e:
        logger.error(f"❌ Telegram scraping failed: {e}")
        raise
    
    finally:
        # Cleanup
        if auth:
            await auth.disconnect()
    
    return all_messages


# Main function for testing
async def main():
    """Test the Telegram scraper"""
    import sys
    
    print("=" * 80)
    print("TELEGRAM SCRAPER TEST")
    print("=" * 80)
    
    # Check environment
    required_vars = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_PHONE']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"\n❌ Missing required environment variables: {', '.join(missing)}")
        print("\nSet them in .env file:")
        print("  TELEGRAM_API_ID=your_api_id")
        print("  TELEGRAM_API_HASH=your_api_hash")
        print("  TELEGRAM_PHONE=+1234567890")
        print("  TELEGRAM_CHANNELS=channel1,channel2,channel3")
        print("\nGet API credentials from: https://my.telegram.org")
        return 1
    
    channels_env = os.getenv('TELEGRAM_CHANNELS', '').strip()
    if not channels_env:
        print("\n⚠️  No TELEGRAM_CHANNELS configured. Using test mode.")
        print("   Set TELEGRAM_CHANNELS=channel1,channel2 in .env to scrape real channels.\n")
        
        # Test with user's own "Saved Messages"
        test_channels = ['me']
    else:
        test_channels = None  # Use from env
    
    try:
        # Run scraper
        messages = await scrape_telegram_sources(
            channels=test_channels,
            hours=24,
            limit_per_channel=20
        )
        
        print(f"\n✅ Scraped {len(messages)} message(s)\n")
        
        # Show sample
        if messages:
            print("Sample messages:")
            print("-" * 80)
            for i, msg in enumerate(messages[:3], 1):
                print(f"\n{i}. {msg['title']}")
                print(f"   Source: {msg['source']}")
                print(f"   URL: {msg['url']}")
                print(f"   Content: {msg['content'][:200]}...")
            
            if len(messages) > 3:
                print(f"\n... and {len(messages) - 3} more message(s)")
        
        print("\n" + "=" * 80)
        print("✅ Test complete!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.exception("Full error:")
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    exit(exit_code)
