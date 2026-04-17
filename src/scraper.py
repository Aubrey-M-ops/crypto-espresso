"""
News scraper for crypto RSS feeds.

Fetches articles from 4 major crypto news sources:
- CoinDesk
- CoinTelegraph
- Decrypt
- The Block

Returns standardized article structures with error handling.
"""

import feedparser
import httpx
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RSS feed URLs
RSS_FEEDS = {
    # "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",  # 不提供正文，暂时禁用
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "The Block": "https://www.theblock.co/rss.xml"
}

# HTTP client timeout
TIMEOUT = 10.0


def fetch_feed(source_name: str, feed_url: str) -> List[Dict[str, str]]:
    """
    Fetch and parse RSS feed from a single source.
    
    Args:
        source_name: Name of the news source (e.g., "CoinDesk")
        feed_url: RSS feed URL
        
    Returns:
        List of article dictionaries with keys: title, url, content, timestamp, source
        Returns empty list if fetch fails.
    """
    try:
        logger.info(f"Fetching {source_name} from {feed_url}")
        
        # Fetch with timeout and follow redirects
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            response = client.get(feed_url)
            response.raise_for_status()
        
        # Parse RSS
        feed = feedparser.parse(response.content)
        
        articles = []
        for entry in feed.entries:
            # Extract article data
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            
            # Get content (try multiple fields, prefer content > description > summary)
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            elif hasattr(entry, "description"):
                content = entry.description
            elif hasattr(entry, "summary"):
                content = entry.summary
            
            # Strip HTML tags (RSS often includes HTML)
            import re
            content = re.sub(r'<[^>]+>', '', content)
            content = content.replace('\n', ' ').strip()
            
            # Parse timestamp
            timestamp = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                timestamp = int(datetime(*entry.published_parsed[:6]).timestamp())
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                timestamp = int(datetime(*entry.updated_parsed[:6]).timestamp())
            else:
                timestamp = int(datetime.now().timestamp())
            
            # Skip entries with missing critical fields
            if not title or not url:
                logger.warning(f"Skipping entry from {source_name}: missing title or URL")
                continue
            
            articles.append({
                "title": title,
                "url": url,
                "content": content.strip(),
                "timestamp": timestamp,
                "source": source_name
            })
        
        logger.info(f"Fetched {len(articles)} articles from {source_name}")
        return articles
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching {source_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing {source_name} feed: {e}")
        return []


def scrape_all_sources() -> List[Dict[str, str]]:
    """
    Scrape articles from all configured sources (RSS + Telegram).
    
    Returns:
        Combined list of all articles from all sources.
        If a source fails, it's skipped and others continue.
    """
    all_articles = []
    
    # Scrape RSS feeds
    for source_name, feed_url in RSS_FEEDS.items():
        articles = fetch_feed(source_name, feed_url)
        all_articles.extend(articles)
    
    # Telegram KOL scraping is handled separately in src/main.py.
    # Keep RSS scraping isolated here to avoid duplicate work and confusing import warnings.

    logger.info(f"Total articles scraped: {len(all_articles)}")
    return all_articles


if __name__ == "__main__":
    # Test scraper
    articles = scrape_all_sources()
    
    print(f"\n✅ Scraped {len(articles)} articles\n")
    
    # Display first 3 articles
    for i, article in enumerate(articles[:3], 1):
        print(f"{i}. [{article['source']}] {article['title']}")
        print(f"   URL: {article['url']}")
        print(f"   Timestamp: {datetime.fromtimestamp(article['timestamp'])}")
        print(f"   Content preview: {article['content'][:100]}...")
        print()
