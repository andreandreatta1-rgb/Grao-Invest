from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "data-context-refresh.yml"


def test_github_actions_data_context_refresh_workflow_is_configured() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "name: Data context refresh" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "30 11,21 * * *"' in workflow
    assert "https://grao-invest.vercel.app" in workflow
    assert "/api/ops/data-context-refresh" in workflow
    assert "run_fundamentals=true" in workflow
    assert "run_news=true" in workflow
    assert "max_instruments=10" in workflow
    assert "news_lookback_days=3" in workflow
    assert "max_articles_per_instrument=20" in workflow
    assert "fundamentals_provider=auto" in workflow
    assert "fundamentals_only_missing=false" in workflow
    assert "Authorization: Bearer ${{ secrets.CRON_SECRET }}" in workflow
    assert "X-GitHub-Actions-Refresh: data-context-twice-daily" in workflow
    assert "--request POST" in workflow
    assert "--fail-with-body" in workflow
    assert "--max-time 180" in workflow
