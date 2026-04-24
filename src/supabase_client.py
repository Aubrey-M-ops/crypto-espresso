"""
Supabase client for persisting crypto terms extracted from article summaries.

Required table (run once in Supabase SQL editor):

    create table if not exists crypto_terms (
        id bigserial primary key,
        term_en text not null default '',
        term_cn text not null default '',
        explanation text not null,
        article_url text,
        article_title text,
        category text,
        date date not null,
        created_at timestamptz default now(),
        unique (term_en, term_cn, date)
    );
"""

import logging
import os
from datetime import date as date_type
from typing import Optional

logger = logging.getLogger(__name__)


def _get_client():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def save_terms(
    terms: list[tuple[str, str, str]],
    article_url: str,
    article_title: str,
    category: str,
    pub_date: Optional[str] = None,
) -> int:
    """
    Upsert extracted terms into the crypto_terms table.

    On conflict (same term_en + term_cn + date), the existing row is updated
    so the freshest source wins.

    Args:
        terms: List of (term_en, term_cn, explanation) tuples from SummaryResult.terms
        article_url: Source article URL
        article_title: Source article title
        category: Article category tag (e.g. "#比特币")
        pub_date: ISO date string YYYY-MM-DD; defaults to today

    Returns:
        Number of rows upserted (0 on error)
    """
    if not terms:
        return 0

    today = pub_date or date_type.today().isoformat()
    rows = [
        {
            "term_en": term_en,
            "term_cn": term_cn,
            "explanation": explanation,
            "article_url": article_url,
            "article_title": article_title,
            "category": category,
            "date": today,
        }
        for term_en, term_cn, explanation in terms
    ]

    try:
        client = _get_client()
        result = (
            client.table("crypto_terms")
            .upsert(rows, on_conflict="term_en,term_cn,date")
            .execute()
        )
        count = len(result.data) if result.data else 0
        logger.info(f"✅ Saved {count} term(s) to Supabase for: {article_title[:50]}")
        return count
    except Exception as e:
        logger.warning(f"⚠️ Failed to save terms to Supabase: {e}")
        return 0
