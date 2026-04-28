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
