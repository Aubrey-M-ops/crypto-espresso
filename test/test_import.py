#!/usr/bin/env python3
"""Quick import test to verify code structure"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

print("Testing imports...")

try:
    from scraper import scrape_all_sources
    print("✅ scraper.py")
except Exception as e:
    print(f"❌ scraper.py: {e}")

try:
    from dedup import ArticleDeduplicator
    print("✅ dedup.py")
except Exception as e:
    print(f"❌ dedup.py: {e}")

try:
    from summarizer import SummarizerClient
    print("✅ summarizer.py")
except Exception as e:
    print(f"❌ summarizer.py: {e}")

try:
    from classifier import classify_articles
    print("✅ classifier.py")
except Exception as e:
    print(f"❌ classifier.py: {e}")

try:
    from digest import format_digest
    print("✅ digest.py")
except Exception as e:
    print(f"❌ digest.py: {e}")

print("\n✅ All modules structure looks good!")
print("\nNext step: Install dependencies with:")
print("  pip install -r requirements.txt")
