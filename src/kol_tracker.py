"""
KOL Project Tracker

Persists project mentions extracted from KOL posts to Supabase and generates
local markdown wiki files for each tracked project.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WIKI_DIR = Path(__file__).parent.parent / "wiki" / "projects"

SENTIMENT_EMOJI = {
    "看多": "🟢 看多",
    "看空": "🔴 看空",
    "中性": "🟡 中性",
}

WIKI_TEMPLATE = """\
# {project_name}

## 📌 基本信息
- **赛道**：（待补充）
- **研究状态**：⏳ 待研究
- **关联币种报告**：-

## 🐦 KOL 提及时间线
| 日期 | KOL | 观点摘要 | 情绪 |
|:---|:---|:---|:---|
{timeline_rows}
## 📊 追踪统计
- 累计提及次数：{mention_count}
- 提及 KOL 数：{kol_count}
- 首次发现：{first_seen}

## 📝 我的笔记
（手动补充自己的研究和判断）
"""


def _wiki_path(wiki_dir: Path, project_name: str) -> Path:
    safe_name = re.sub(r'[\\/]', '_', project_name).replace(' ', '_')
    return wiki_dir / f"{safe_name}.md"


def _parse_existing_timeline(content: str) -> list[dict]:
    """Extract timeline rows from an existing wiki file."""
    rows = []
    in_table = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("| 日期") or stripped.startswith("|:---"):
            in_table = True
            continue
        if in_table:
            if not stripped.startswith("|"):
                break
            parts = [p.strip() for p in stripped.strip("|").split("|")]
            if len(parts) >= 4:
                rows.append({
                    "date": parts[0],
                    "kol": parts[1],
                    "context": parts[2],
                    "sentiment": parts[3],
                })
    return rows


def generate_project_wiki(
    project_name: str,
    kol_name: str,
    mention_date: str,
    sentiment: str,
    context: str,
    wiki_dir: Optional[Path] = None,
) -> Path:
    """
    Create or update the project wiki file for a single mention.

    Returns:
        Path to the written wiki file
    """
    wiki_dir = wiki_dir or WIKI_DIR
    wiki_dir.mkdir(parents=True, exist_ok=True)
    path = _wiki_path(wiki_dir, project_name)

    existing_rows: list[dict] = []
    first_seen = mention_date

    if path.exists():
        existing_content = path.read_text(encoding="utf-8")
        existing_rows = _parse_existing_timeline(existing_content)
        if existing_rows:
            dates = [r["date"] for r in existing_rows if r["date"]]
            if dates:
                first_seen = min(dates + [mention_date])

    sentiment_label = SENTIMENT_EMOJI.get(sentiment, sentiment)
    new_row = {
        "date": mention_date,
        "kol": f"@{kol_name}",
        "context": f'"{context}"' if context else "-",
        "sentiment": sentiment_label,
    }

    already_recorded = any(
        r["date"] == mention_date and r["kol"] == f"@{kol_name}"
        for r in existing_rows
    )
    if not already_recorded:
        existing_rows.append(new_row)

    existing_rows.sort(key=lambda r: r.get("date", ""))

    timeline_rows = "\n".join(
        f"| {r['date']} | {r['kol']} | {r['context']} | {r['sentiment']} |"
        for r in existing_rows
    )
    if timeline_rows:
        timeline_rows += "\n"

    kol_count = len({r["kol"] for r in existing_rows})
    mention_count = len(existing_rows)

    wiki_content = WIKI_TEMPLATE.format(
        project_name=project_name,
        timeline_rows=timeline_rows,
        mention_count=mention_count,
        kol_count=kol_count,
        first_seen=first_seen,
    )

    path.write_text(wiki_content, encoding="utf-8")
    logger.info(f"📝 Wiki updated: {path} ({mention_count} mention(s))")
    return path


def save_project_mentions(
    kol_name: str,
    mention_date: str,
    projects: list,
    wiki_dir: Optional[Path] = None,
) -> int:
    """
    Persist project mentions to Supabase and generate wiki files.

    Args:
        kol_name: KOL channel name
        mention_date: ISO date YYYY-MM-DD
        projects: List of KolProjectMention objects
        wiki_dir: Override default wiki dir (used in tests)

    Returns:
        Number of rows inserted to Supabase (0 if Supabase not configured or error)
    """
    if not projects:
        return 0

    inserted = 0

    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        try:
            from supabase import create_client
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            client = create_client(supabase_url, key)

            rows = [
                {
                    "project_name": p.project_name,
                    "kol_name": kol_name,
                    "mention_date": mention_date,
                    "context": p.context,
                    "sentiment": p.sentiment,
                    "research_status": "待研究",
                }
                for p in projects
            ]
            result = (
                client.table("kol_project_tracking")
                .upsert(rows, on_conflict="project_name,kol_name,mention_date")
                .execute()
            )
            inserted = len(result.data) if result.data else 0
            logger.info(f"✅ Saved {inserted} project mention(s) to Supabase for KOL @{kol_name}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save project mentions to Supabase: {e}")
    else:
        logger.debug("SUPABASE_URL not set — skipping Supabase persistence")

    for p in projects:
        try:
            generate_project_wiki(
                project_name=p.project_name,
                kol_name=kol_name,
                mention_date=mention_date,
                sentiment=p.sentiment,
                context=p.context,
                wiki_dir=wiki_dir,
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate wiki for {p.project_name}: {e}")

    return inserted
