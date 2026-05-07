from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "microtrades-refresh.yml"


def test_github_actions_microtrades_refresh_workflow_is_configured() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "name: Microtrades data refresh" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "cron: \"0 * * * *\"" in workflow
    assert "https://grao-invest.vercel.app" in workflow
    assert "/api/ops/microtrades-data-refresh" in workflow
    assert "Authorization: Bearer ${{ secrets.CRON_SECRET }}" in workflow
    assert "X-GitHub-Actions-Refresh: microtrades-hourly" in workflow
    assert "--request POST" in workflow
    assert "--fail-with-body" in workflow
    assert "--max-time 120" in workflow
