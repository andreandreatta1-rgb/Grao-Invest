from __future__ import annotations

from pathlib import Path

from app.services.b3_daily_job import build_b3_daily_job_markdown, find_latest_snapshot_dir


def test_find_latest_snapshot_dir_picks_most_recent_date(tmp_path: Path) -> None:
    data_b3 = tmp_path / "data" / "b3"
    data_b3.mkdir(parents=True, exist_ok=True)
    (data_b3 / "historico_2026-04-20").mkdir()
    (data_b3 / "historico_2026-04-22").mkdir()
    (data_b3 / "historico_2026-04-21").mkdir()
    (data_b3 / "historico_lixo").mkdir()
    (data_b3 / "pesquisa_pregao_2026-04-18").mkdir()

    latest = find_latest_snapshot_dir(data_b3_root=data_b3, prefix="historico_")
    assert latest is not None
    assert latest.name == "historico_2026-04-22"


def test_build_b3_daily_job_markdown_renders_core_sections() -> None:
    payload = {
        "pipeline": {
            "run_at": "2026-04-23T03:00:00+00:00",
            "source_root": "data/b3/historico_2026-04-22",
            "output_root": "data/lake/b3",
        },
        "build": {
            "executed": True,
            "cotahist_silver_rows": 123,
            "cambio_input_files": 4,
            "renda_fixa_silver_rows": 10,
        },
        "load": {
            "executed": True,
            "provider": "b3-cotahist-lake",
            "inserted": 100,
            "duplicates_ignored": 20,
            "parse_errors": 1,
        },
        "case_study": {
            "executed": True,
            "thesis_id": "T-001",
            "instrument": "PETR4",
            "confidence_pct": 55.0,
            "expected_pct": 2.1,
            "realized_pct": 1.2,
        },
    }
    md = build_b3_daily_job_markdown(payload)
    assert "# B3 Daily Job" in md
    assert "cotahist_silver_rows" in md
    assert "b3-cotahist-lake" in md
    assert "PETR4" in md
