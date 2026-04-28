import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import tempfile, pathlib
from unittest.mock import patch

from summarizer import SummarizerClient
from kol_tracker import generate_project_wiki, _wiki_path, save_project_mentions

RAW_WITH_PROJECTS = '{"summary": "某KOL看好FET和ARB两个项目。","terms": [],"beginner_perspective": "了解KOL如何筛选项目。","projects": [{"name": "FET","sentiment": "看多","context": "FET是AI赛道最纯正的标的"},{"name": "ARB","sentiment": "中性","context": "ARB短期有压力但长期看好"}]}'

def test_parse_kol_projects():
    client = SummarizerClient.__new__(SummarizerClient)
    result = client._parse_kol_response(RAW_WITH_PROJECTS)
    assert len(result.projects) == 2
    assert result.projects[0].project_name == "FET"
    assert result.projects[0].sentiment == "看多"
    assert "AI赛道" in result.projects[0].context
    assert result.projects[1].project_name == "ARB"
    assert result.projects[1].sentiment == "中性"


def test_parse_kol_projects_missing_key():
    """Response without 'projects' key should produce empty list."""
    client = SummarizerClient.__new__(SummarizerClient)
    raw = '{"summary": "No projects mentioned.", "terms": [], "beginner_perspective": "学习。"}'
    result = client._parse_kol_response(raw)
    assert result.projects == []


def test_parse_kol_projects_invalid_sentiment_normalized():
    """Invalid sentiment should be normalized to 中性."""
    client = SummarizerClient.__new__(SummarizerClient)
    raw = '{"summary": "Test.", "terms": [], "beginner_perspective": "Test.", "projects": [{"name": "BTC", "sentiment": "bullish", "context": "looking good"}]}'
    result = client._parse_kol_response(raw)
    assert len(result.projects) == 1
    assert result.projects[0].sentiment == "中性"


def test_parse_kol_projects_null_becomes_empty():
    """projects: null should produce empty list without raising."""
    client = SummarizerClient.__new__(SummarizerClient)
    raw = '{"summary": "Test.", "terms": [], "beginner_perspective": "Test.", "projects": null}'
    result = client._parse_kol_response(raw)
    assert result.projects == []


def test_wiki_created_for_new_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = pathlib.Path(tmpdir)
        generate_project_wiki(
            project_name="FET",
            kol_name="WuBlockchain",
            mention_date="2026-04-27",
            sentiment="看多",
            context="FET 是 AI 赛道最纯正的标的",
            wiki_dir=wiki_dir,
        )
        wiki_file = wiki_dir / "FET.md"
        assert wiki_file.exists()
        content = wiki_file.read_text(encoding="utf-8")
        assert "# FET" in content
        assert "WuBlockchain" in content
        assert "2026-04-27" in content
        assert "🟢 看多" in content
        assert "FET 是 AI 赛道最纯正的标的" in content
        assert "累计提及次数：1" in content
        assert "首次发现：2026-04-27" in content


def test_wiki_updated_on_second_mention():
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = pathlib.Path(tmpdir)
        generate_project_wiki("FET", "WuBlockchain", "2026-04-27", "看多",
                              "FET 是 AI 赛道最纯正的标的", wiki_dir)
        generate_project_wiki("FET", "AltcoinGordon", "2026-05-01", "中性",
                              "短期回调但长期看好", wiki_dir)
        content = (wiki_dir / "FET.md").read_text(encoding="utf-8")
        assert "WuBlockchain" in content
        assert "AltcoinGordon" in content
        assert "累计提及次数：2" in content
        assert "提及 KOL 数：2" in content
        assert "首次发现：2026-04-27" in content


def test_wiki_path_normalizes_name():
    assert _wiki_path(pathlib.Path("/tmp"), "ARB") == pathlib.Path("/tmp/ARB.md")
    assert _wiki_path(pathlib.Path("/tmp"), "Fetch AI") == pathlib.Path("/tmp/Fetch_AI.md")


def test_save_project_mentions_no_supabase():
    """save_project_mentions writes wiki files even without SUPABASE_URL."""
    from summarizer import KolProjectMention

    projects = [
        KolProjectMention(project_name="SOL", sentiment="看多", context="SOL 表现强劲"),
        KolProjectMention(project_name="ETH", sentiment="中性", context="ETH 横盘中"),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = pathlib.Path(tmpdir)
        with patch.dict(os.environ, {}, clear=True):
            # Remove SUPABASE_URL if present
            os.environ.pop("SUPABASE_URL", None)

            result = save_project_mentions(
                kol_name="TestKOL",
                mention_date="2026-04-27",
                projects=projects,
                wiki_dir=wiki_dir,
            )

        # No Supabase configured → returns 0
        assert result == 0

        # Wiki files are still created
        assert (wiki_dir / "SOL.md").exists()
        assert (wiki_dir / "ETH.md").exists()

        sol_content = (wiki_dir / "SOL.md").read_text(encoding="utf-8")
        assert "SOL 表现强劲" in sol_content
        assert "TestKOL" in sol_content
