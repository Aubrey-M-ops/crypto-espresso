"""
Digest Builder

Formats classified articles into Telegram-ready message(s).
Handles Telegram's 4096-character limit by splitting into multiple messages.
"""

from datetime import datetime
from typing import List, Dict, Optional, TypedDict


class Article(TypedDict):
    """Structured article with summary and metadata."""
    title: str
    url: str
    summary: str
    beginner_score: int


class ClassifiedArticles(TypedDict):
    """Classification result."""
    must_read: List[Article]
    advanced: List[Article]


# Telegram message length limit
TELEGRAM_MAX_LENGTH = 4096

# Message template parts
SEPARATOR = "---"

# Max chars shown for a KOL message preview
KOL_PREVIEW_LENGTH = 200


def format_article(article: Article, index: int) -> str:
    """
    Format a single article for Telegram.
    
    Format:
    **[Index]. [Title]**
    [URL]
    
    [Summary]
    
    Args:
        article: Article with title, url, and summary
        index: Article number in the section (1-based)
        
    Returns:
        Formatted string for one article
    """
    return f"""**{index}. {article['title']}**
{article['url']}

{article['summary']}"""


def format_kol_message(message: Dict, index: int) -> str:
    """
    Format a single KOL Telegram message for display.

    Format:
    **[Index]. 📣 @channel_name**
    [Message preview...]
    🔗 [URL]

    Args:
        message: Message dict with keys: title, content, url, source, timestamp
        index: Message number (1-based)

    Returns:
        Formatted string for one KOL message
    """
    source = message.get("source", "")
    # source is "Telegram/channel_name" → extract channel
    channel = source.split("/")[-1] if "/" in source else source

    # Use AI-generated summary if available, otherwise fall back to raw preview
    if message.get("kol_summary"):
        body = message["kol_summary"]
    else:
        content = message.get("content", "").strip()
        body = content[:KOL_PREVIEW_LENGTH]
        if len(content) > KOL_PREVIEW_LENGTH:
            body += "..."

    url = message.get("url", "")

    return f"**{index}. 📣 @{channel}**\n{body}\n🔗 {url}"


def _build_kol_section(kol_messages: List[Dict]) -> str:
    """Build the KOL 观点 section string."""
    if not kol_messages:
        return ""
    section = "\n📱 KOL 观点\n"
    for i, msg in enumerate(kol_messages, 1):
        msg_text = format_kol_message(msg, i)
        section += f"\n{msg_text}\n"
        if i < len(kol_messages):
            section += f"\n{SEPARATOR}\n"
    return section


def build_digest(classified: ClassifiedArticles, date: str = None, kol_messages: Optional[List[Dict]] = None) -> List[str]:
    """
    Build complete digest message(s) from classified articles.
    
    Message structure:
    🌅 今日加密货币新闻 | YYYY-MM-DD
    
    🟢 必读
    [Article 1]
    ---
    [Article 2]
    ---
    [Article 3]
    
    🔵 进阶
    [Article 4]
    ---
    [Article 5]
    
    If total length exceeds 4096 chars, splits into:
    1. Header + Must-Read section
    2. Advanced section (with continuation header)
    
    Args:
        classified: Dictionary with 'must_read' and 'advanced' lists
        date: Date string (YYYY-MM-DD), defaults to today
        kol_messages: Optional list of KOL Telegram message dicts to include
            as a separate "📱 KOL 观点" section

    Returns:
        List of message strings (1 if fits, 2+ if split needed)
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    must_read = classified.get("must_read", [])
    advanced = classified.get("advanced", [])
    kol = kol_messages or []

    # Build header
    header = f"🌅 今日加密货币新闻 | {date}\n"

    # Build Must-Read section
    must_read_section = ""
    if must_read:
        must_read_section = "\n🟢 必读\n"
        for i, article in enumerate(must_read, 1):
            article_text = format_article(article, i)
            must_read_section += f"\n{article_text}\n"
            if i < len(must_read):
                must_read_section += f"\n{SEPARATOR}\n"

    # Build Advanced section
    advanced_section = ""
    if advanced:
        advanced_section = "\n🔵 进阶\n"
        for i, article in enumerate(advanced, 1):
            article_text = format_article(article, i)
            advanced_section += f"\n{article_text}\n"
            if i < len(advanced):
                advanced_section += f"\n{SEPARATOR}\n"

    # Build KOL section
    kol_section = _build_kol_section(kol)

    # Try to fit everything in one message
    full_message = header + must_read_section + advanced_section + kol_section

    if len(full_message) <= TELEGRAM_MAX_LENGTH:
        return [full_message.strip()]

    # Split into multiple messages
    messages = []

    # Message 1: Header + Must-Read
    msg1 = header + must_read_section
    if len(msg1) <= TELEGRAM_MAX_LENGTH:
        messages.append(msg1.strip())
    else:
        # Must-Read section itself is too long (rare)
        # Split Must-Read into chunks
        messages.extend(_split_section(header, "🟢 必读", must_read))

    # Message 2+: Advanced (with continuation header)
    continuation_header = f"🌅 今日加密货币新闻 | {date} (续)\n"
    if advanced:
        msg2 = continuation_header + advanced_section
        if len(msg2) <= TELEGRAM_MAX_LENGTH:
            messages.append(msg2.strip())
        else:
            # Advanced section too long, split into chunks
            messages.extend(_split_section(continuation_header, "🔵 进阶", advanced))

    # KOL section: append to last message if it fits, otherwise new message
    if kol_section:
        if messages and len(messages[-1]) + len(kol_section) <= TELEGRAM_MAX_LENGTH:
            messages[-1] = (messages[-1] + "\n" + kol_section).strip()
        else:
            kol_msg = continuation_header + kol_section
            messages.append(kol_msg.strip())

    return messages


def _split_section(header: str, section_title: str, articles: List[Article]) -> List[str]:
    """
    Split a section into multiple messages when it exceeds the limit.
    
    Strategy:
    - Each message gets header + section title
    - Pack as many full articles as possible per message
    - Never split an article across messages
    
    Args:
        header: Message header (e.g., "🌅 今日加密货币新闻 | 2024-04-13")
        section_title: Section emoji+title (e.g., "🟢 必读")
        articles: List of articles to pack
        
    Returns:
        List of message chunks
    """
    messages = []
    current_msg = f"{header}\n{section_title}\n"
    current_index = 1
    
    for article in articles:
        article_text = format_article(article, current_index)
        separator = f"\n{SEPARATOR}\n" if current_index > 1 else "\n"
        
        # Try adding this article to current message
        test_msg = current_msg + separator + article_text
        
        if len(test_msg) <= TELEGRAM_MAX_LENGTH:
            current_msg = test_msg
            current_index += 1
        else:
            # Current message is full, start a new one
            messages.append(current_msg.strip())
            current_msg = f"{header}\n{section_title} (续)\n\n{article_text}\n"
            current_index = 1
    
    # Add last message
    if current_msg.strip():
        messages.append(current_msg.strip())
    
    return messages


def format_empty_digest(date: str = None) -> str:
    """
    Format message when no articles are available.
    
    Args:
        date: Date string (YYYY-MM-DD), defaults to today
        
    Returns:
        Empty digest message
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    return f"""🌅 今日加密货币新闻 | {date}

今日暂无新文章。

_如果这是错误，请检查新闻源配置或网络连接。_"""


if __name__ == "__main__":
    # Test with sample data
    from classifier import classify_articles
    
    sample_articles = [
        {
            "title": "Bitcoin ETF Approval",
            "url": "https://coindesk.com/btc-etf",
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
            "url": "https://cointelegraph.com/dencun",
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
            "url": "https://theblock.co/defi-tvl",
            "summary": """📰 大白话总结：去中心化金融协议锁定资金量创新高

📖 术语高亮：
  - DeFi = 去中心化金融，不依赖银行的金融服务
  - TVL = 总锁定价值，衡量DeFi协议规模的指标

🏷️ 分类标签：#DeFi

💡 延伸一问：更多资金进入DeFi意味着什么风险和机会？""",
            "beginner_score": 5
        }
    ]
    
    # Classify articles
    classified = classify_articles(sample_articles)
    
    # Build digest
    messages = build_digest(classified, "2024-04-13")
    
    # Print result
    for i, msg in enumerate(messages, 1):
        print(f"{'='*60}")
        print(f"Message {i} ({len(msg)} chars):")
        print(f"{'='*60}")
        print(msg)
        print()
    
    # Test empty digest
    print(f"{'='*60}")
    print("Empty Digest:")
    print(f"{'='*60}")
    print(format_empty_digest("2024-04-13"))
