"""
Article Classifier

Classifies articles into "Must-Read" and "Advanced" tiers based on BEGINNER_SCORE.
"""

import os
from typing import List, Dict, TypedDict


class Article(TypedDict):
    """Structured article with summary and metadata."""
    title: str
    url: str
    summary: str  # Full structured summary from LLM
    beginner_score: int  # 1-10 score from LLM


class ClassifiedArticles(TypedDict):
    """Classification result."""
    must_read: List[Article]
    advanced: List[Article]


# Configuration
MUST_READ_COUNT = int(os.getenv("MUST_READ_COUNT", "3"))


def classify_articles(articles: List[Article]) -> ClassifiedArticles:
    """
    Classify articles into Must-Read and Advanced tiers.
    
    Algorithm:
    1. Sort articles by BEGINNER_SCORE (descending)
    2. Top MUST_READ_COUNT articles → Must-Read
    3. Remaining articles → Advanced
    
    Args:
        articles: List of articles with beginner_score field
        
    Returns:
        Dictionary with 'must_read' and 'advanced' lists
    """
    if not articles:
        return {"must_read": [], "advanced": []}
    
    # Sort by beginner_score (highest first)
    sorted_articles = sorted(
        articles,
        key=lambda x: x.get("beginner_score", 0),
        reverse=True
    )
    
    # Split into tiers
    must_read_count = min(MUST_READ_COUNT, len(sorted_articles))
    must_read = sorted_articles[:must_read_count]
    advanced = sorted_articles[must_read_count:]
    
    return {
        "must_read": must_read,
        "advanced": advanced
    }


def classify_with_fallback(articles: List[Article]) -> ClassifiedArticles:
    """
    Classify articles with tie-breaking for equal scores.
    
    Tie-breaking priority:
    1. Regulatory/market-moving news (#监管, #宏观经济)
    2. Bitcoin/Ethereum news (#比特币, #以太坊)
    3. Earliest timestamp (first scraped)
    
    Args:
        articles: List of articles with beginner_score and optional tags
        
    Returns:
        Dictionary with 'must_read' and 'advanced' lists
    """
    if not articles:
        return {"must_read": [], "advanced": []}
    
    # Define priority tags for tie-breaking
    priority_tags = {"#监管", "#宏观经济", "#比特币", "#以太坊"}
    
    def sort_key(article: Article):
        score = article.get("beginner_score", 0)
        # Extract tags from summary (tags are in line starting with 🏷️)
        summary = article.get("summary", "")
        has_priority_tag = any(tag in summary for tag in priority_tags)
        
        # Return tuple: (score DESC, has_priority_tag DESC, article index ASC)
        # Note: We negate score and use -1 for True to get DESC order
        return (-score, -int(has_priority_tag), articles.index(article))
    
    sorted_articles = sorted(articles, key=sort_key)
    
    must_read_count = min(MUST_READ_COUNT, len(sorted_articles))
    must_read = sorted_articles[:must_read_count]
    advanced = sorted_articles[must_read_count:]
    
    return {
        "must_read": must_read,
        "advanced": advanced
    }


if __name__ == "__main__":
    # Test with sample data
    sample_articles = [
        {
            "title": "Bitcoin ETF Approval",
            "url": "https://example.com/btc-etf",
            "summary": """📰 大白话总结：美国批准比特币基金上市，普通人可以在股票账户买比特币了

📖 术语高亮：
  - ETF = 一种股票型基金，可以在证券账户买卖
  - SEC = 美国证券交易委员会，监管股票市场的机构

🏷️ 分类标签：#监管 | #比特币

💡 延伸一问：ETF让比特币投资更简单，但这会让比特币变得和股票一样受监管吗？""",
            "beginner_score": 9
        },
        {
            "title": "Ethereum Dencun Upgrade",
            "url": "https://example.com/dencun",
            "summary": """📰 大白话总结：以太坊完成技术升级，交易费用大幅降低

📖 术语高亮：
  - Dencun = 以太坊的一次技术升级代号
  - Layer 2 = 以太坊的"快车道"，帮助处理更多交易

🏷️ 分类标签：#以太坊

💡 延伸一问：交易费降低会吸引更多人使用以太坊吗？""",
            "beginner_score": 7
        },
        {
            "title": "DeFi Protocol TVL Analysis",
            "url": "https://example.com/defi-tvl",
            "summary": """📰 大白话总结：去中心化金融协议锁定资金量创新高

📖 术语高亮：
  - DeFi = 去中心化金融，不依赖银行的金融服务
  - TVL = 总锁定价值，衡量DeFi协议规模的指标

🏷️ 分类标签：#DeFi

💡 延伸一问：更多资金进入DeFi意味着什么风险和机会？""",
            "beginner_score": 5
        }
    ]
    
    result = classify_articles(sample_articles)
    
    print("🟢 Must-Read Articles:")
    for i, article in enumerate(result["must_read"], 1):
        print(f"{i}. {article['title']} (score: {article['beginner_score']})")
    
    print("\n🔵 Advanced Articles:")
    for i, article in enumerate(result["advanced"], 1):
        print(f"{i}. {article['title']} (score: {article['beginner_score']})")
