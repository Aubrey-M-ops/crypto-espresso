"""
AI-powered article summarization using Claude API.

Generates structured Chinese summaries with beginner-friendly explanations,
term glossaries, category tags, and thought-provoking questions.
"""

import os
import time
import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Structured summary output from Claude API."""
    plain_summary: str
    terms: list[tuple[str, str]]  # [(term, explanation), ...]
    category: str
    thinking_question: str
    beginner_score: int
    raw_response: str


@dataclass
class KolSummaryResult:
    """Structured KOL message interpretation output from Claude API."""
    plain_summary: str              # 💬 KOL在说什么
    terms: list[tuple[str, str]]    # 📖 术语拆解
    beginner_perspective: str       # 🧠 小白视角
    raw_response: str


class SummarizerError(Exception):
    """Base exception for summarizer errors."""
    pass


class APIRateLimitError(SummarizerError):
    """Raised when API rate limit is hit."""
    pass


class SummarizerClient:
    """Claude API client for generating structured article summaries."""

    # Path to prompt template files
    PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "prompt_template.md")
    KOL_PROMPT_TEMPLATE_PATH = os.path.join(
        os.path.dirname(__file__), "..", "docs", "kol_prompt_template.md"
    )

    @classmethod
    def _load_prompt_template(cls) -> str:
        with open(cls.PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()

    @classmethod
    def _load_kol_prompt_template(cls) -> str:
        path = os.path.normpath(cls.KOL_PROMPT_TEMPLATE_PATH)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # Valid category tags
    VALID_CATEGORIES = {"#监管", "#比特币", "#以太坊", "#DeFi", "#新项目", "#宏观经济"}
    VALID_KOL_SENTIMENTS = {"看涨", "看跌", "中立", "提醒风险"}
    
    # Exponential backoff configuration
    MAX_RETRIES = 3
    BASE_BACKOFF = 2  # seconds
    MAX_BACKOFF = 60  # seconds
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude API client.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        
        Raises:
            ValueError: If API key is not provided or found in environment.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. "
                "Set it in .env or pass as argument."
            )
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5"
        logger.info(f"Initialized SummarizerClient with model: {self.model}")
    
    def summarize(
        self,
        title: str,
        url: str,
        content: str,
        max_retries: Optional[int] = None
    ) -> SummaryResult:
        """
        Generate structured summary for a single article.
        
        Args:
            title: Article title
            url: Article URL
            content: Article full text content
            max_retries: Override default retry count
        
        Returns:
            SummaryResult with parsed structured output
        
        Raises:
            SummarizerError: If summarization fails after retries
            APIRateLimitError: If rate limit is hit and retries exhausted
        """
        max_retries = max_retries or self.MAX_RETRIES
        
        # Truncate content if too long (Claude has 200k context but be conservative)
        max_content_chars = 10000
        if len(content) > max_content_chars:
            logger.warning(
                f"Content too long ({len(content)} chars), truncating to {max_content_chars}"
            )
            content = content[:max_content_chars] + "..."
        
        prompt = self._load_prompt_template().format(
            title=title,
            url=url,
            content=content
        )
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Summarizing: {title[:50]}... (attempt {attempt + 1}/{max_retries})")
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1500,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                raw_text = response.content[0].text
                logger.debug(f"Raw response:\n{raw_text}")
                
                # Parse structured output
                result = self._parse_response(raw_text)
                logger.info(
                    f"✅ Summarized: {title[:50]}... "
                    f"(score: {result.beginner_score}, category: {result.category})"
                )
                return result
                
            except anthropic.RateLimitError as e:
                backoff = min(
                    self.BASE_BACKOFF * (2 ** attempt),
                    self.MAX_BACKOFF
                )
                
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Rate limit hit, retrying in {backoff}s... "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(backoff)
                else:
                    logger.error("Rate limit exhausted after all retries")
                    raise APIRateLimitError(
                        f"API rate limit hit after {max_retries} retries"
                    ) from e
                    
            except anthropic.APIError as e:
                logger.error(f"Claude API error: {e}")
                if attempt < max_retries - 1:
                    backoff = self.BASE_BACKOFF * (2 ** attempt)
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    raise SummarizerError(f"API error after {max_retries} retries: {e}") from e
                    
            except Exception as e:
                logger.error(f"Unexpected error during summarization: {e}")
                raise SummarizerError(f"Failed to summarize article: {e}") from e
        
        raise SummarizerError("Unreachable: retry loop should have raised an exception")
    
    def summarize_batch(
        self,
        articles: list[Dict[str, str]],
        delay_seconds: float = 1.0
    ) -> list[SummaryResult]:
        """
        Summarize multiple articles with rate-limiting.
        
        NOTE: This processes articles serially with delays to avoid rate limits.
        For true parallel processing, consider using async/await or worker pools
        with more sophisticated rate limiting.
        
        Args:
            articles: List of dicts with keys: title, url, content
            delay_seconds: Delay between API calls to avoid rate limits
        
        Returns:
            List of SummaryResult objects (same order as input)
        
        Raises:
            SummarizerError: If any article fails after retries
        """
        results = []
        total = len(articles)
        
        logger.info(f"Starting batch summarization of {total} articles...")
        
        for i, article in enumerate(articles, 1):
            try:
                result = self.summarize(
                    title=article["title"],
                    url=article["url"],
                    content=article["content"]
                )
                results.append(result)
                
                # Rate limiting: delay between requests (except last one)
                if i < total:
                    logger.debug(f"Sleeping {delay_seconds}s before next request...")
                    time.sleep(delay_seconds)
                    
            except APIRateLimitError:
                logger.error(f"Rate limit hit on article {i}/{total}, stopping batch")
                raise
                
            except SummarizerError as e:
                logger.error(f"Failed to summarize article {i}/{total}: {e}")
                # Continue with remaining articles instead of failing entire batch
                # Caller can check len(results) vs len(articles)
                continue
        
        logger.info(
            f"✅ Batch complete: {len(results)}/{total} articles summarized successfully"
        )
        return results
    
    def summarize_kol(
        self,
        channel: str,
        content: str,
        max_retries: Optional[int] = None
    ) -> KolSummaryResult:
        """
        Generate a beginner-friendly Chinese interpretation of a KOL message.

        Args:
            channel: Channel/account name (e.g. "WuBlockchain")
            content: Raw text content of the KOL post
            max_retries: Override default retry count

        Returns:
            KolSummaryResult with parsed structured output
        """
        max_retries = max_retries or self.MAX_RETRIES

        if len(content) > 3000:
            content = content[:3000] + "..."

        prompt = self._load_kol_prompt_template().format(
            channel=channel,
            content=content
        )

        for attempt in range(max_retries):
            try:
                logger.info(f"Interpreting KOL @{channel}... (attempt {attempt + 1}/{max_retries})")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    temperature=0.5,
                    messages=[{"role": "user", "content": prompt}]
                )

                raw_text = response.content[0].text
                logger.debug(f"KOL raw response:\n{raw_text}")
                result = self._parse_kol_response(raw_text)
                logger.info(f"✅ KOL @{channel} interpreted")
                return result

            except anthropic.RateLimitError as e:
                backoff = min(self.BASE_BACKOFF * (2 ** attempt), self.MAX_BACKOFF)
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit, retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    raise APIRateLimitError(
                        f"API rate limit hit after {max_retries} retries"
                    ) from e

            except anthropic.APIError as e:
                logger.error(f"Claude API error: {e}")
                if attempt < max_retries - 1:
                    backoff = self.BASE_BACKOFF * (2 ** attempt)
                    time.sleep(backoff)
                else:
                    raise SummarizerError(f"API error after {max_retries} retries: {e}") from e

            except Exception as e:
                logger.error(f"Unexpected error during KOL interpretation: {e}")
                raise SummarizerError(f"Failed to interpret KOL message: {e}") from e

        raise SummarizerError("Unreachable: retry loop should have raised an exception")

    def _parse_kol_response(self, raw_text: str) -> KolSummaryResult:
        """Parse Claude's JSON KOL interpretation response into KolSummaryResult."""
        payload = self._extract_json_object(raw_text)

        plain_summary = str(payload.get("summary", "")).strip()
        if not plain_summary:
            raise ValueError("Missing required field: summary")

        raw_terms = payload.get("terms", [])
        if raw_terms is None:
            raw_terms = []
        if not isinstance(raw_terms, list):
            raise ValueError("Invalid field: terms must be a list")

        terms = []
        for entry in raw_terms[:3]:
            if not isinstance(entry, dict):
                continue
            term = str(entry.get("term", "")).strip()
            explanation = str(entry.get("explanation", "")).strip()
            if term and explanation:
                terms.append((term, explanation))

        beginner_perspective = str(payload.get("beginner_perspective", "")).strip()

        return KolSummaryResult(
            plain_summary=plain_summary,
            terms=terms,
            beginner_perspective=beginner_perspective,
            raw_response=raw_text
        )

    def _extract_json_object(self, raw_text: str) -> Dict[str, Any]:
        """Extract and parse the first JSON object from a model response."""
        text = raw_text.strip()
        decoder = json.JSONDecoder()

        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                payload, end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload

        raise ValueError("No valid JSON object found in KOL response")

    def format_kol_summary(self, result: KolSummaryResult) -> str:
        """Format a KolSummaryResult into display text for Telegram."""
        output = [f"💬 {result.plain_summary}"]

        if result.terms:
            output.append("\n📖 术语拆解：")
            for term, explanation in result.terms:
                output.append(f"  - {term} = {explanation}")

        if result.beginner_perspective:
            output.append(f"\n🧠 小白视角：{result.beginner_perspective}")

        return "\n".join(output)

    def _parse_response(self, raw_text: str) -> SummaryResult:
        """
        Parse Claude's structured response into SummaryResult.
        
        Args:
            raw_text: Raw text response from Claude API
        
        Returns:
            Parsed SummaryResult
        
        Raises:
            ValueError: If response format is invalid
        """
        # Strip any preamble before the first structured marker
        if "📰 大白话总结：" in raw_text:
            raw_text = raw_text[raw_text.index("📰 大白话总结："):]

        lines = raw_text.strip().split('\n')

        plain_summary = ""
        terms = []
        category = ""
        thinking_question = ""
        beginner_score = 0

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            if line.startswith("📰 大白话总结："):
                plain_summary = line.replace("📰 大白话总结：", "").strip()
                current_section = "summary"

            elif line.startswith("📖 术语高亮："):
                current_section = "terms"

            elif line.startswith("🏷️ 分类标签："):
                category_raw = line.replace("🏷️ 分类标签：", "").strip()
                # Extract first valid category tag
                for cat in self.VALID_CATEGORIES:
                    if cat in category_raw:
                        category = cat
                        break
                current_section = "category"

            elif line.startswith("💡 延伸一问："):
                thinking_question = line.replace("💡 延伸一问：", "").strip()
                current_section = "thinking"

            elif line.startswith("💡 答："):
                answer = line.replace("💡 答：", "").strip()
                if answer:
                    thinking_question = thinking_question + "\n💡 答：" + answer
                current_section = "thinking_answer"

            elif line.startswith("BEGINNER_SCORE:"):
                score_str = line.replace("BEGINNER_SCORE:", "").strip()
                try:
                    beginner_score = int(score_str)
                    if not (1 <= beginner_score <= 10):
                        logger.warning(f"Score out of range: {beginner_score}, clamping to 1-10")
                        beginner_score = max(1, min(10, beginner_score))
                except ValueError:
                    logger.warning(f"Invalid score format: {score_str}, defaulting to 5")
                    beginner_score = 5
                current_section = "score"

            elif current_section == "summary":
                # Accumulate multi-line summary
                plain_summary += "\n" + line

            elif current_section == "terms" and line.startswith("-"):
                # Parse term line: "- Term = explanation"
                term_line = line.lstrip("- ").strip()
                if " = " in term_line:
                    term, explanation = term_line.split(" = ", 1)
                    terms.append((term.strip(), explanation.strip()))
                elif "=" in term_line:
                    term, explanation = term_line.split("=", 1)
                    terms.append((term.strip(), explanation.strip()))
        
        # Validation
        if not plain_summary:
            raise ValueError("Missing required field: 大白话总结")
        if not category:
            logger.warning(f"No valid category found, defaulting to #新项目")
            category = "#新项目"
        if not thinking_question:
            logger.warning("Missing thinking question")
            thinking_question = "这个新闻对加密货币市场会有什么影响？"
        if beginner_score == 0:
            logger.warning("Missing beginner score, defaulting to 5")
            beginner_score = 5
        
        return SummaryResult(
            plain_summary=plain_summary,
            terms=terms,
            category=category,
            thinking_question=thinking_question,
            beginner_score=beginner_score,
            raw_response=raw_text
        )
    
    def format_summary(self, result: SummaryResult) -> str:
        """
        Format a SummaryResult into final display text.
        
        Args:
            result: Parsed summary result
        
        Returns:
            Formatted summary string ready for Telegram
        """
        output = [f"📰 大白话总结：{result.plain_summary}"]
        
        if result.terms:
            output.append("\n📖 术语高亮：")
            for term, explanation in result.terms:
                output.append(f"  - {term} = {explanation}")
        
        output.append(f"\n🏷️ 分类标签：{result.category}")
        output.append(f"\n💡 延伸一问：{result.thinking_question}")
        
        return "\n".join(output)


# Convenience function for single-article use
def summarize(title: str, url: str, content: str) -> SummaryResult:
    """
    Convenience function to summarize a single article.
    
    Args:
        title: Article title
        url: Article URL
        content: Article full text
    
    Returns:
        SummaryResult with structured summary
    
    Raises:
        SummarizerError: If summarization fails
    """
    client = SummarizerClient()
    return client.summarize(title, url, content)


# Example usage and testing
if __name__ == "__main__":
    # Test with sample article
    sample_article = {
        "title": "Bitcoin Surges Past $50,000 as Institutional Adoption Grows",
        "url": "https://example.com/bitcoin-50k",
        "content": """
        Bitcoin has surged past the $50,000 mark for the first time in months,
        driven by renewed institutional interest and positive regulatory developments.
        
        Major investment firms including BlackRock and Fidelity have increased their
        cryptocurrency holdings, signaling growing confidence in digital assets as
        a legitimate asset class.
        
        The rally comes amid increasing adoption of Bitcoin ETFs (exchange-traded funds)
        and clearer regulatory frameworks in major markets like the United States and
        European Union.
        
        Analysts attribute the price movement to a combination of factors including
        macroeconomic uncertainty, inflation hedging strategies, and the upcoming
        Bitcoin halving event expected in 2024.
        """
    }
    
    try:
        client = SummarizerClient()
        result = client.summarize(
            title=sample_article["title"],
            url=sample_article["url"],
            content=sample_article["content"]
        )
        
        print("=" * 60)
        print("SUMMARY RESULT")
        print("=" * 60)
        print(client.format_summary(result))
        print("=" * 60)
        print(f"\nBeginner Score: {result.beginner_score}/10")
        print(f"Category: {result.category}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
