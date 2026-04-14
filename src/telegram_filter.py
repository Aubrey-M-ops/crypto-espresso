#!/usr/bin/env python3
"""
Telegram Message Filter

Filters Telegram messages for crypto-relevant content.
"""

import re
from typing import List, Dict, Set
from datetime import datetime


class TelegramMessageFilter:
    """Filter Telegram messages for crypto relevance"""
    
    # Crypto keywords (case-insensitive)
    KEYWORDS_CN = [
        '比特币', 'BTC', '以太坊', 'ETH', '加密货币', '币圈', 
        'DeFi', 'NFT', '山寨币', 'USDT', '交易所', '区块链',
        '虚拟货币', '数字货币', 'Web3', 'DAO', '智能合约',
        '钱包', '挖矿', '矿工', '牛市', '熊市', '空投', 
        '代币', 'Token', '公链', 'Layer2', 'L2'
    ]
    
    KEYWORDS_EN = [
        'Bitcoin', 'BTC', 'Ethereum', 'ETH', 'crypto', 'cryptocurrency',
        'DeFi', 'NFT', 'altcoin', 'stablecoin', 'blockchain',
        'Web3', 'DAO', 'smart contract', 'wallet', 'mining',
        'bullish', 'bearish', 'airdrop', 'token', 'Layer2', 'L2'
    ]
    
    # Price indicators
    PRICE_PATTERNS = [
        r'\$\d+',           # $100
        r'\d+\s*USD',       # 100 USD
        r'\d+\s*USDT',      # 100 USDT
        r'\d+%',            # 10%
    ]
    
    MIN_LENGTH = 50  # Minimum character count
    
    def __init__(self):
        """Initialize filter"""
        # Combine all keywords
        self.keywords = set(
            [kw.lower() for kw in self.KEYWORDS_CN] +
            [kw.lower() for kw in self.KEYWORDS_EN]
        )
        
        # Compile price patterns
        self.price_regex = re.compile('|'.join(self.PRICE_PATTERNS), re.IGNORECASE)
        
        # Track seen messages for deduplication
        self.seen_hashes: Set[str] = set()
    
    def _contains_keywords(self, text: str) -> bool:
        """Check if text contains crypto keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.keywords)
    
    def _contains_price(self, text: str) -> bool:
        """Check if text contains price indicators"""
        return bool(self.price_regex.search(text))
    
    def _is_long_enough(self, text: str) -> bool:
        """Check if message meets minimum length"""
        return len(text.strip()) >= self.MIN_LENGTH
    
    def _get_hash(self, message: Dict) -> str:
        """Generate hash for deduplication"""
        # Use title + first 100 chars of content
        content = message.get('content', '')
        title = message.get('title', '')
        key = f"{title}{content[:100]}"
        return str(hash(key))
    
    def _is_duplicate(self, message: Dict) -> bool:
        """Check if message is duplicate"""
        msg_hash = self._get_hash(message)
        if msg_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(msg_hash)
        return False
    
    def is_crypto_relevant(self, message: Dict) -> bool:
        """
        Check if a message is crypto-relevant.
        
        Args:
            message: Message dict with 'title' and 'content'
        
        Returns:
            True if relevant, False otherwise
        """
        text = f"{message.get('title', '')} {message.get('content', '')}"
        
        # Must be long enough
        if not self._is_long_enough(text):
            return False
        
        # Must contain keywords OR price info
        has_keywords = self._contains_keywords(text)
        has_price = self._contains_price(text)
        
        return has_keywords or has_price
    
    def filter_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Filter list of messages for crypto relevance.
        
        Args:
            messages: List of message dicts
        
        Returns:
            Filtered list of crypto-relevant, non-duplicate messages
        """
        filtered = []
        
        for msg in messages:
            # Skip if not crypto-relevant
            if not self.is_crypto_relevant(msg):
                continue
            
            # Skip duplicates
            if self._is_duplicate(msg):
                continue
            
            filtered.append(msg)
        
        return filtered
    
    def reset_dedup(self):
        """Reset deduplication cache (call once per run)"""
        self.seen_hashes.clear()


# Convenience function for easy use
def filter_crypto_messages(messages: List[Dict]) -> List[Dict]:
    """
    Filter Telegram messages for crypto-relevant content.
    
    Filters by:
    - Keyword matching (Chinese & English crypto terms)
    - Price indicators ($, USD, USDT, %)
    - Minimum length (50+ characters)
    - Deduplication
    
    Args:
        messages: List of message dicts with 'title', 'content', 'url', 'source'
    
    Returns:
        Filtered list of crypto-relevant messages
    
    Example:
        >>> messages = [
        ...     {'title': 'BTC突破10万美元', 'content': '比特币价格...', 'url': '...'},
        ...     {'title': '今天天气不错', 'content': '阳光明媚', 'url': '...'}
        ... ]
        >>> filtered = filter_crypto_messages(messages)
        >>> len(filtered)  # Only crypto message
        1
    """
    filter_obj = TelegramMessageFilter()
    return filter_obj.filter_messages(messages)


if __name__ == "__main__":
    # Test the filter
    test_messages = [
        {
            'title': 'BTC突破10万美元',
            'content': '比特币价格今日突破历史新高，达到10万美元大关。市场情绪高涨，交易量激增。',
            'url': 'https://example.com/1',
            'source': 'Telegram/test_channel'
        },
        {
            'title': '以太坊升级完成',
            'content': 'Ethereum完成了最新的网络升级，Gas费用显著降低，Layer2解决方案也更加完善。',
            'url': 'https://example.com/2',
            'source': 'Telegram/test_channel'
        },
        {
            'title': '今天天气不错',
            'content': '阳光明媚',
            'url': 'https://example.com/3',
            'source': 'Telegram/test_channel'
        },
        {
            'title': '短消息',
            'content': 'BTC',
            'url': 'https://example.com/4',
            'source': 'Telegram/test_channel'
        },
    ]
    
    filtered = filter_crypto_messages(test_messages)
    
    print(f"Original: {len(test_messages)} messages")
    print(f"Filtered: {len(filtered)} crypto-relevant messages\n")
    
    for i, msg in enumerate(filtered, 1):
        print(f"{i}. {msg['title']}")
        print(f"   {msg['content'][:50]}...")
        print()
