#!/usr/bin/env python3
"""
Web3 News Push - Main Entry Point

Orchestrates the entire news pipeline.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scraper import scrape_all_sources
from dedup import ArticleDeduplicator
from summarizer import SummarizerClient
from classifier import classify_articles
from digest import build_digest, format_empty_digest

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def send_telegram(channel_id: str, message: str, dry_run: bool = False) -> bool:
    """
    Send message to Telegram via Bot API.

    Args:
        channel_id: Telegram chat/channel ID to send to
        message: Message content (Markdown)
        dry_run: If True, print to console instead of sending

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print("=" * 80)
        print("DRY RUN - Message would be sent to Telegram:")
        print("=" * 80)
        print(message)
        print("=" * 80)
        return True

    if not channel_id:
        logger.error("TELEGRAM_CHANNEL_ID not configured")
        return False

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    try:
        import httpx
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        payload = {
            "chat_id": channel_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        resp = httpx.post(url, json=payload, timeout=30)

        # Fallback: if Markdown causes 400, retry as plain text
        if resp.status_code == 400:
            logger.warning(f"⚠️ Telegram 400 error: {resp.text}")
            logger.warning("⚠️ Retrying as plain text...")
            payload.pop("parse_mode")
            resp = httpx.post(url, json=payload, timeout=30)
            if resp.status_code == 400:
                logger.error(f"❌ Plain text also failed: {resp.text}")

        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            logger.error(f"❌ Telegram API error: {data}")
            return False
        logger.info(f"✅ Message sent successfully to {channel_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send Telegram message: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Web3 News Push - Daily crypto news digest'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print digest to console instead of sending'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        help='Max articles to process (default: from env or 10)'
    )
    parser.add_argument(
        '--kol-only',
        action='store_true',
        help='Only scrape and send KOL messages, skip news articles'
    )
    parser.add_argument(
        '--no-dedup',
        action='store_true',
        help='Skip deduplication (send all scraped content regardless of seen history)'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config
    telegram_channel_id = os.getenv('TELEGRAM_CHANNEL_ID', '')
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
    max_articles = args.max_articles or int(os.getenv('MAX_ARTICLES', '10'))
    
    if not anthropic_api_key:
        logger.error("❌ ANTHROPIC_API_KEY not set in environment")
        return 1
    
    logger.info("🚀 Starting Web3 News Push...")
    logger.info(f"📊 Max articles: {max_articles}")
    logger.info(f"🔍 Dry run: {args.dry_run}")
    logger.info(f"📱 KOL only: {args.kol_only}")
    logger.info(f"🔄 No dedup: {args.no_dedup}")
    
    try:
        # Step 1: Scrape articles
        logger.info("📰 Step 1/6: Scraping news sources...")
        all_articles = [] if args.kol_only else scrape_all_sources()

        # Step 1b: Scrape Telegram KOL channels (kept separate from RSS articles)
        kol_messages = []
        if os.getenv('TELEGRAM_API_ID') and os.getenv('TELEGRAM_PHONE'):
            try:
                import asyncio
                from telegram_scraper import scrape_telegram_sources
                from telegram_filter import filter_crypto_messages

                logger.info("   📱 Scraping Telegram KOL sources...")
                telegram_msgs = asyncio.run(scrape_telegram_sources())
                kol_messages = filter_crypto_messages(telegram_msgs)
                logger.info(f"   ✅ Got {len(kol_messages)} KOL messages after filtering")
            except Exception as e:
                logger.warning(f"   ⚠️ Telegram KOL scraping failed: {e}")
        
        if not all_articles and not args.kol_only:
            logger.warning("⚠️ No articles found")
            if not args.dry_run and telegram_channel_id:
                send_telegram(
                    telegram_channel_id,
                    format_empty_digest(),
                    dry_run=args.dry_run
                )
            return 0
        
        logger.info(f"✅ Scraped {len(all_articles)} articles")
        
        # Step 2: Deduplicate
        logger.info("🔄 Step 2/6: Deduplicating articles...")
        max_kol = int(os.getenv('MAX_KOL_MESSAGES', '5'))

        if args.no_dedup:
            logger.info("   ⏭️ Skipping deduplication (--no-dedup)")
            unique_articles = all_articles
            unique_kol = kol_messages[:max_kol] if kol_messages else []
        else:
            dedup = ArticleDeduplicator()
            unique_articles = dedup.filter_duplicates(all_articles)
            unique_kol = dedup.filter_duplicates(kol_messages) if kol_messages else []
            unique_kol = unique_kol[:max_kol]
            dedup.cleanup_old_entries()

        if unique_kol:
            logger.info(f"   ✅ {len(unique_kol)} KOL message(s) to include")

        if not args.kol_only:
            if not unique_articles:
                logger.info("✅ No new articles (all duplicates)")
                if not kol_messages:
                    return 0
            else:
                logger.info(f"✅ {len(unique_articles)} unique articles")
        
        # Limit to max_articles
        articles_to_process = [] if args.kol_only else unique_articles[:max_articles]
        if not args.kol_only and len(unique_articles) > max_articles:
            logger.info(f"📉 Limiting to {max_articles} articles")

        # Step 3: Summarize with AI
        logger.info(f"🤖 Step 3/6: Generating AI summaries ({len(articles_to_process)} articles)...")
        summarizer = SummarizerClient(api_key=anthropic_api_key)

        # Step 3b: AI-interpret KOL messages in beginner-friendly Chinese
        if unique_kol:
            logger.info(f"   📱 Generating KOL interpretations ({len(unique_kol)} messages)...")
            interpreted_kol = []
            for kol_msg in unique_kol:
                source = kol_msg.get("source", "")
                channel = source.split("/")[-1] if "/" in source else source
                content = kol_msg.get("content", "").strip()
                # Skip AI interpretation for image-only / link-only posts (too short to summarize)
                if len(content) < 30:
                    logger.info(f"   ⏭️ Skipping KOL @{channel} (content too short, using raw preview)")
                    interpreted_kol.append(kol_msg)
                    continue
                try:
                    kol_result = summarizer.summarize_kol(channel=channel, content=content)
                    kol_msg = dict(kol_msg)
                    kol_msg["kol_summary"] = summarizer.format_kol_summary(kol_result)
                except Exception as e:
                    logger.warning(f"   ⚠️ Failed to interpret KOL @{channel}: {e}")
                interpreted_kol.append(kol_msg)
            unique_kol = interpreted_kol
            logger.info(f"   ✅ KOL interpretations done")
        
        summarized_articles = []
        for i, article in enumerate(articles_to_process, 1):
            try:
                logger.info(f"   Processing {i}/{len(articles_to_process)}: {article['title'][:50]}...")
                
                result = summarizer.summarize(
                    title=article['title'],
                    url=article['url'],
                    content=article['content']
                )
                
                summarized_articles.append({
                    'title': article['title'],
                    'url': article['url'],
                    'summary': summarizer.format_summary(result),
                    'beginner_score': result.beginner_score
                })
                
            except Exception as e:
                logger.error(f"   ❌ Failed to summarize article {i}: {e}")
                continue
        
        if not summarized_articles and not args.kol_only:
            logger.error("❌ No articles successfully summarized")
            return 1

        logger.info(f"✅ Summarized {len(summarized_articles)} articles")
        
        # Step 4: Classify
        logger.info("📊 Step 4/6: Classifying articles...")
        classified = classify_articles(summarized_articles) if summarized_articles else {"must_read": [], "advanced": []}
        logger.info(f"✅ Must-Read: {len(classified['must_read'])}, Advanced: {len(classified['advanced'])}")
        
        # Step 5: Build digest
        logger.info("📝 Step 5/6: Building digest...")
        today = datetime.now().strftime("%Y-%m-%d")
        messages = build_digest(classified, date=today, kol_messages=unique_kol)
        logger.info(f"✅ Generated {len(messages)} message(s)")
        
        # Step 6: Send to Telegram
        logger.info("📤 Step 6/6: Sending to Telegram...")
        for i, message in enumerate(messages, 1):
            success = send_telegram(telegram_channel_id, message, dry_run=args.dry_run)
            if not success and not args.dry_run:
                logger.error(f"❌ Failed to send message {i}/{len(messages)}")
                return 1
        
        logger.info("🎉 Web3 News Push completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
