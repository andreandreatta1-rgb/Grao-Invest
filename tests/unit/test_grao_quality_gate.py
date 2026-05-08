from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_grao_quality_gate as gate


def _write_frontend_dist(tmp_path: Path, bundle: str) -> Path:
    dist = tmp_path / "frontend_dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><div id="root"></div>'
        '<script type="module" crossorigin src="/assets/index-test.js"></script>',
        encoding="utf-8",
    )
    (assets / "index-test.js").write_text(bundle, encoding="utf-8")
    return dist


def test_frontend_gate_rejects_dashboard_mock_as_initial_state(tmp_path: Path) -> None:
    dist = _write_frontend_dist(
        tmp_path,
        "function App(){let [state,setState]=(0,_.useState)(()=>Hn(_n(xn)));return state}",
    )

    with pytest.raises(gate.QualityGateFailure, match="mock dashboard"):
        gate.inspect_frontend_bundle(dist)


def test_frontend_gate_accepts_loading_before_official_dashboard(tmp_path: Path) -> None:
    dist = _write_frontend_dist(
        tmp_path,
        "function Yz(e){return Wz.reduce((t,n)=>(t[n]=e?.[n]??"
        "(n===`dashboardSummary`?{}:xn[n]),t),{})}"
        "function App(){let [state,setState]=(0,_.useState)(()=>Hn(_n({})));"
        "return `Carregando laboratorio cientifico`}",
    )

    result = gate.inspect_frontend_bundle(dist)

    assert result["entry_asset"] == "assets/index-test.js"
    assert result["initial_dashboard_source"] == "empty"


def test_frontend_gate_rejects_legacy_1727_dashboard_kpi_literal(tmp_path: Path) -> None:
    dist = _write_frontend_dist(
        tmp_path,
        "const fallback={dashboardSummary:{thesis_history_overview:{total_tested:1727}}};"
        "function App(){let [state,setState]=(0,_.useState)(()=>Hn(_n({})));return state}",
    )

    with pytest.raises(gate.QualityGateFailure, match="1727"):
        gate.inspect_frontend_bundle(dist)


def test_dashboard_payload_gate_rejects_inconsistent_tested_counts() -> None:
    payload = {
        "ops_health": {"status": "ok"},
        "thesis_history_overview": {"total_tested": 879},
        "historical_analysis_summary": {"thesis_count": 1727},
        "thesis_open_operations": [],
    }

    with pytest.raises(gate.QualityGateFailure, match="879.*1727"):
        gate.inspect_dashboard_payload(payload)


def test_dashboard_payload_gate_accepts_current_public_contract() -> None:
    payload = {
        "ops_health": {"status": "ok"},
        "thesis_history_overview": {"total_tested": 879},
        "historical_analysis_summary": {"thesis_count": 879},
        "thesis_open_operations": [
            {
                "front": "imoveis",
                "is_open": True,
                "action": "Apto Sao Miguel",
                "real_estate_analysis": {"score": 63, "confidence": 51},
            }
        ],
    }

    result = gate.inspect_dashboard_payload(payload)

    assert result["total_tested"] == 879
    assert result["historical_thesis_count"] == 879
    assert result["real_estate_operations"] == 1


def test_dashboard_payload_gate_requires_real_estate_analysis_when_imoveis_exist() -> None:
    payload = {
        "ops_health": {"status": "ok"},
        "thesis_history_overview": {"total_tested": 879},
        "historical_analysis_summary": {"thesis_count": 879},
        "thesis_open_operations": [{"front": "imoveis", "is_open": True}],
    }

    with pytest.raises(gate.QualityGateFailure, match="real_estate_analysis"):
        gate.inspect_dashboard_payload(payload)


def test_cli_writes_json_report_for_local_checks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dist = _write_frontend_dist(
        tmp_path,
        "function Yz(e){return Wz.reduce((t,n)=>(t[n]=e?.[n]??"
        "(n===`dashboardSummary`?{}:xn[n]),t),{})}"
        "function App(){let [state,setState]=(0,_.useState)(()=>Hn(_n({})));"
        "return `Carregando laboratorio cientifico`}",
    )

    exit_code = gate.main(["--frontend-dist", str(dist), "--json"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ok"
    assert output["frontend"]["entry_asset"] == "assets/index-test.js"
