"""
Article deduplication using SHA256 hash and SQLite storage.

Tracks seen articles by hash and automatically cleans up entries older than 7 days.
"""

import hashlib
import sqlite3
import time
from typing import List, Dict, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database settings
DEFAULT_DB_PATH = Path(__file__).parent.parent / "db" / "articles.db"
RETENTION_DAYS = 7
RETENTION_SECONDS = RETENTION_DAYS * 24 * 60 * 60


def article_hash(title: str, url: str) -> str:
    """
    Generate a 16-character hash from article title and URL.
    
    Args:
        title: Article title
        url: Article URL
        
    Returns:
        16-character hex string hash
    """
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()[:16]


class ArticleDeduplicator:
    """
    Manages article deduplication using SQLite database.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize deduplicator with database connection.
        
        Args:
            db_path: Path to SQLite database. Creates if doesn't exist.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_db_exists()
        self._init_schema()
    
    def _ensure_db_exists(self):
        """Create database directory if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _init_schema(self):
        """Initialize database schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_articles (
                    hash TEXT PRIMARY KEY,
                    timestamp INTEGER NOT NULL
                )
            """)
            # Create index on timestamp for faster cleanup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON seen_articles(timestamp)
            """)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def is_duplicate(self, title: str, url: str) -> bool:
        """
        Check if article has been seen before.
        
        Args:
            title: Article title
            url: Article URL
            
        Returns:
            True if article exists in database, False otherwise
        """
        hash_val = article_hash(title, url)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM seen_articles WHERE hash = ? LIMIT 1",
                (hash_val,)
            )
            return cursor.fetchone() is not None
    
    def mark_as_seen(self, title: str, url: str) -> str:
        """
        Mark article as seen by storing its hash.
        
        Args:
            title: Article title
            url: Article URL
            
        Returns:
            The hash value that was stored
        """
        hash_val = article_hash(title, url)
        timestamp = int(time.time())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO seen_articles (hash, timestamp) VALUES (?, ?)",
                (hash_val, timestamp)
            )
            conn.commit()
        
        return hash_val
    
    def cleanup_old_entries(self):
        """
        Delete entries older than RETENTION_DAYS.
        """
        cutoff_timestamp = int(time.time()) - RETENTION_SECONDS
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM seen_articles WHERE timestamp < ?",
                (cutoff_timestamp,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old entries")
        
        return deleted_count
    
    def filter_duplicates(self, articles: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter out duplicate articles from a list.
        
        Args:
            articles: List of article dictionaries (must have 'title' and 'url' keys)
            
        Returns:
            List of unique articles (not previously seen)
        """
        unique_articles = []
        
        for article in articles:
            title = article.get("title", "")
            url = article.get("url", "")
            
            if not title or not url:
                logger.warning("Skipping article with missing title or URL")
                continue
            
            if not self.is_duplicate(title, url):
                unique_articles.append(article)
                self.mark_as_seen(title, url)
            else:
                logger.debug(f"Duplicate: {title[:50]}...")
        
        logger.info(f"Filtered {len(articles)} articles → {len(unique_articles)} unique")
        return unique_articles
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with 'total_entries' and 'old_entries' counts
        """
        cutoff_timestamp = int(time.time()) - RETENTION_SECONDS
        
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM seen_articles").fetchone()[0]
            old = conn.execute(
                "SELECT COUNT(*) FROM seen_articles WHERE timestamp < ?",
                (cutoff_timestamp,)
            ).fetchone()[0]
        
        return {
            "total_entries": total,
            "old_entries": old
        }


if __name__ == "__main__":
    # Test deduplication
    dedup = ArticleDeduplicator()
    
    # Test articles
    test_articles = [
        {"title": "Bitcoin hits new ATH", "url": "https://example.com/1", "source": "Test"},
        {"title": "Ethereum upgrade scheduled", "url": "https://example.com/2", "source": "Test"},
        {"title": "Bitcoin hits new ATH", "url": "https://example.com/1", "source": "Test"},  # duplicate
    ]
    
    print("🧪 Testing deduplication...\n")
    
    # First pass
    unique = dedup.filter_duplicates(test_articles)
    print(f"First pass: {len(test_articles)} → {len(unique)} unique\n")
    
    # Second pass (all should be duplicates)
    unique2 = dedup.filter_duplicates(test_articles)
    print(f"Second pass: {len(test_articles)} → {len(unique2)} unique\n")
    
    # Stats
    stats = dedup.get_stats()
    print(f"📊 Database stats:")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Old entries: {stats['old_entries']}\n")
    
    # Cleanup
    dedup.cleanup_old_entries()
    print("✅ Test complete")
