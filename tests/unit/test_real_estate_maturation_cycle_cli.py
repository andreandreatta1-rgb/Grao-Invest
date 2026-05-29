import subprocess
import sys
from pathlib import Path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "run_real_estate_radar_maturation_cycle.py"


def test_cli_help_does_not_run_cycle() -> None:
    result = subprocess.run(
        [sys.executable, str(_script_path()), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "RADAR_MATURATION_PIN_CAMPINAS_URL" in (result.stdout or "")
    assert "candidate_count" not in (result.stdout or "")


def test_cli_rejects_unknown_args() -> None:
    result = subprocess.run(
        [sys.executable, str(_script_path()), "--unknown-arg"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "Unexpected args" in (result.stderr or "")

