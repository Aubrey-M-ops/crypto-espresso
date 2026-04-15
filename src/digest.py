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
    """Build the KOL 观点 section string (no length check)."""
    if not kol_messages:
        return ""
    section = "\n📱 KOL 观点\n"
    for i, msg in enumerate(kol_messages, 1):
        msg_text = format_kol_message(msg, i)
        section += f"\n{msg_text}\n"
        if i < len(kol_messages):
            section += f"\n{SEPARATOR}\n"
    return section


def _split_kol_section(kol_messages: List[Dict], header: str) -> List[str]:
    """Split KOL messages into multiple Telegram-sized chunks."""
    chunks = []
    current = f"{header}\n📱 KOL 观点\n"
    global_index = 1

    for msg in kol_messages:
        msg_text = format_kol_message(msg, global_index)
        separator = f"\n{SEPARATOR}\n" if global_index > 1 and current != f"{header}\n📱 KOL 观点\n" else "\n"
        candidate = current + separator + msg_text + "\n"

        if len(candidate) <= TELEGRAM_MAX_LENGTH:
            current = candidate
        else:
            if current.strip():
                chunks.append(current)
            current = f"{header}\n📱 KOL 观点 (续)\n\n{msg_text}\n"

        global_index += 1

    if current.strip():
        chunks.append(current)

    return chunks if chunks else [header]


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

    # KOL section: split into chunks if needed, then append/attach
    if kol:
        kol_chunks = _split_kol_section(kol, continuation_header)
        if messages and len(messages[-1]) + len(kol_chunks[0]) <= TELEGRAM_MAX_LENGTH:
            messages[-1] = (messages[-1] + "\n" + kol_chunks[0]).strip()
            messages.extend(chunk.strip() for chunk in kol_chunks[1:])
        else:
            messages.extend(chunk.strip() for chunk in kol_chunks)

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
            "summary": """📰 大白话总结：美国正式批准比特币ETF上市，这意味着普通人现在可以直接在股票账户里买卖比特币相关基金，不需要自己注册加密货币交易所。这次批准被认为是比特币走向主流金融市场的重要里程碑。机构投资者也因此可以更方便地配置比特币资产，预计会带来大量新资金流入。对普通投资者来说，门槛大大降低了，但风险同样存在。

📖 术语高亮：
  - ETF = 一种股票型基金，可以在证券账户买卖
  - SEC = 美国证券交易委员会，监管股票市场的机构

🏷️ 分类标签：#监管 | #比特币

💡 延伸一问：ETF让比特币投资更简单，但这会让比特币变得和股票一样受监管吗？
💡 答：很可能会。一旦比特币进入传统金融体系，监管机构就有了更多介入的理由和工具。好处是投资者保护更完善、市场更透明；但比特币最初的"去中心化、无需许可"精神可能会受到一定程度的削弱。""",
            "beginner_score": 9
        },
        {
            "title": "Ethereum Dencun Upgrade",
            "url": "https://cointelegraph.com/dencun",
            "summary": """📰 大白话总结：以太坊完成了代号"Dencun"的重大技术升级，核心变化是大幅降低了Layer 2网络的数据存储成本，直接导致用户交易手续费减少了90%以上。这次升级对普通用户最直观的感受就是转账和操作DeFi应用变便宜了很多。开发者也对此表示欢迎，认为这会加速以太坊生态的应用落地。以太坊的竞争力因此得到了显著提升。

📖 术语高亮：
  - Dencun = 以太坊的一次技术升级代号
  - Layer 2 = 以太坊的"快车道"，帮助处理更多交易

🏷️ 分类标签：#以太坊

💡 延伸一问：交易费降低会吸引更多人使用以太坊吗？
💡 答：短期内很可能会。手续费一直是以太坊用户流失的主因之一，降费后使用门槛明显降低，尤其对小额用户友好。但长期来看，还要看应用生态能否跟上，毕竟便宜只是吸引用户的条件之一，好用的产品才是留住用户的关键。""",
            "beginner_score": 7
        },
        {
            "title": "DeFi Protocol TVL Analysis",
            "url": "https://theblock.co/defi-tvl",
            "summary": """📰 大白话总结：链上数据显示，DeFi各大协议的资金锁定总量再创历史新高，说明越来越多的人把资产放进这些无需银行的金融应用里赚取收益。这一数字的上涨通常被看作市场信心回升的信号。其中借贷和流动性挖矿类协议增长最明显，部分原因是近期加密市场整体回暖。不过TVL高涨也意味着系统性风险在积累。

📖 术语高亮：
  - DeFi = 去中心化金融，不依赖银行的金融服务
  - TVL = 总锁定价值，衡量DeFi协议规模的指标

🏷️ 分类标签：#DeFi

💡 延伸一问：更多资金进入DeFi意味着什么风险和机会？
💡 答：机会在于流动性增加会让各类产品的收益更稳定，参与者也更多。风险在于一旦某个大协议出现漏洞或被黑客攻击，连锁反应会更严重。历史上多次DeFi崩盘都发生在TVL高点附近，投资者在享受高收益的同时，需要格外注意合约审计情况和资产分散。""",
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
