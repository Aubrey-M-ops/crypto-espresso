#!/usr/bin/env python3
"""
Quick test script for Telegram scraper setup.

Validates configuration and tests basic scraping functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def check_requirements():
    """Check if required packages are installed"""
    print("📦 Checking dependencies...")
    
    try:
        import telethon
        print("  ✅ telethon installed")
    except ImportError:
        print("  ❌ telethon not installed")
        print("     Run: pip install -r requirements.txt")
        return False
    
    try:
        import httpx
        print("  ✅ httpx installed")
    except ImportError:
        print("  ❌ httpx not installed")
        return False
    
    return True


def check_credentials():
    """Check if Telegram credentials are configured"""
    print("\n🔑 Checking credentials...")
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id:
        print("  ❌ TELEGRAM_API_ID not set")
        print("     Get from: https://my.telegram.org/apps")
        return False
    else:
        print(f"  ✅ TELEGRAM_API_ID: {api_id}")
    
    if not api_hash:
        print("  ❌ TELEGRAM_API_HASH not set")
        print("     Get from: https://my.telegram.org/apps")
        return False
    else:
        print(f"  ✅ TELEGRAM_API_HASH: {api_hash[:8]}...")
    
    return True


def check_session():
    """Check if session exists"""
    print("\n💾 Checking session...")
    
    session_file = Path.home() / '.config' / 'web3-news-push' / 'telegram_session.txt'
    session_env = os.getenv('TELEGRAM_SESSION', '')
    
    if session_env:
        print(f"  ✅ TELEGRAM_SESSION set in environment")
        return True
    elif session_file.exists():
        print(f"  ✅ Session file found: {session_file}")
        return True
    else:
        print(f"  ⚠️  No session found")
        print(f"     Run: python src/telegram_auth.py")
        return False


def test_scraper():
    """Test the scraper"""
    print("\n🧪 Testing scraper...")
    
    try:
        from telegram_scraper import scrape_telegram_sync
        
        articles = scrape_telegram_sync()
        
        print(f"\n✅ Scraper test successful!")
        print(f"   Found {len(articles)} article(s)")
        
        if articles:
            print("\n📰 Sample articles:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n{i}. [{article['source']}]")
                print(f"   Title: {article['title']}")
                print(f"   URL: {article['url']}")
        else:
            print("\nℹ️  No articles found. This could mean:")
            print("  - No channels subscribed")
            print("  - No recent messages in channels")
            print("  - TELEGRAM_FOLDER_ID is set but folder is empty")
        
        return True
        
    except RuntimeError as e:
        print(f"\n❌ {e}")
        return False
    except Exception as e:
        print(f"\n❌ Scraper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Telegram Scraper Setup Test")
    print("=" * 60)
    
    # Check dependencies
    if not check_requirements():
        print("\n❌ Please install dependencies first")
        return 1
    
    # Check credentials
    if not check_credentials():
        print("\n❌ Please configure credentials in .env")
        print("\nExample .env:")
        print("  TELEGRAM_API_ID=12345678")
        print("  TELEGRAM_API_HASH=abcdef1234567890...")
        return 1
    
    # Check session
    has_session = check_session()
    
    if not has_session:
        print("\n⚠️  Setup required:")
        print("  1. Run: python src/telegram_auth.py")
        print("  2. Enter your phone number")
        print("  3. Enter the verification code from Telegram")
        print("  4. Run this test again")
        return 1
    
    # Test scraper
    if not test_scraper():
        return 1
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Telegram scraper is ready to use.")
    print("=" * 60)
    print("\nNext steps:")
    print("  • Run full pipeline: python src/main.py --dry-run")
    print("  • Check docs: docs/TELEGRAM_SETUP.md")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
