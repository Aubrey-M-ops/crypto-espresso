import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from summarizer import SummarizerClient

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
