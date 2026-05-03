from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "services" / "api" / "static"


def test_finvest_uses_runtime_open_state_without_reviving_mock_rows() -> None:
    script = (STATIC_DIR / "finvest.jsx").read_text(encoding="utf-8")

    assert "const tesesPosGoLiveViewOpen = runtime ? runtime.currentOpen : tesesPosGoLive;" in script
    assert "runtime?.currentOpen?.length ? runtime.currentOpen : tesesPosGoLive" not in script
    assert "rowOrStatus?.is_open === false" in script
    assert "const currentOpen = current.filter((row) => isOpenStatus(row));" in script
