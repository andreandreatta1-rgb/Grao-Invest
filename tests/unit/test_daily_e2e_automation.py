from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_daily_e2e_script_orchestrates_job_deploy_and_public_verification() -> None:
    script = (ROOT / "scripts" / "run_grao_daily_e2e.ps1").read_text(encoding="utf-8")

    assert "run_b3_automation_cycle.ps1" in script
    assert "-FlushRetries" in script
    assert "run_quality_gate.ps1" in script
    assert "run_visual_smoke.ps1" in script
    assert "/api/frontend/version" in script
    assert "Wait-FrontendDeploy" in script
    assert "git rev-parse HEAD" in script
    assert "StrictMobile" in script


def test_daily_e2e_script_keeps_skip_switches_for_safe_local_runs() -> None:
    script = (ROOT / "scripts" / "run_grao_daily_e2e.ps1").read_text(encoding="utf-8")

    assert "[switch]$SkipDailyJob" in script
    assert "[switch]$SkipFrontendBuild" in script
    assert "[switch]$SkipDeployWait" in script
    assert "[switch]$SkipVisualSmoke" in script


def test_daily_e2e_script_keeps_child_output_out_of_step_summary() -> None:
    script = (ROOT / "scripts" / "run_grao_daily_e2e.ps1").read_text(encoding="utf-8")

    assert "$stepOutput = & $Action 2>&1" in script
    assert "foreach ($line in $stepOutput)" in script
