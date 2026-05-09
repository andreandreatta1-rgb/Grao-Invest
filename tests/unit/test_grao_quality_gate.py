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
    (dist / "build-info.json").write_text(
        json.dumps(
            {
                "ui_revision": "UI rev soul-4",
                "source_app": "apps/grao-invest-cockpit",
                "git_commit": "1234567890abcdef",
                "git_commit_short": "1234567",
                "entry_asset": "assets/index-test.js",
            },
        ),
        encoding="utf-8",
    )
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
    assert result["build"]["git_commit_short"] == "1234567"
    assert result["build"]["source_app"] == "apps/grao-invest-cockpit"


def test_frontend_gate_rejects_missing_or_mismatched_build_fingerprint(tmp_path: Path) -> None:
    dist = _write_frontend_dist(
        tmp_path,
        "function App(){let [state,setState]=(0,_.useState)(()=>Hn(_n({})));return state}",
    )
    (dist / "build-info.json").write_text(
        json.dumps(
            {
                "ui_revision": "UI rev soul-4",
                "source_app": "apps/thesis-lab-view",
                "git_commit": "1234567890abcdef",
                "git_commit_short": "1234567",
                "entry_asset": "assets/index-other.js",
            },
        ),
        encoding="utf-8",
    )

    with pytest.raises(gate.QualityGateFailure, match="build-info"):
        gate.inspect_frontend_bundle(dist)


def test_frontend_gate_rejects_legacy_1727_dashboard_kpi_literal(tmp_path: Path) -> None:
    dist = _write_frontend_dist(
        tmp_path,
        "const fallback={dashboardSummary:{thesis_history_overview:{total_tested:1727}}};"
        "function App(){let [state,setState]=(0,_.useState)(()=>Hn(_n({})));return state}",
    )

    with pytest.raises(gate.QualityGateFailure, match="1727"):
        gate.inspect_frontend_bundle(dist)


def test_frontend_gate_rejects_any_legacy_1727_frontend_literal(tmp_path: Path) -> None:
    dist = _write_frontend_dist(
        tmp_path,
        "const historicalConsolidated={testedTheses:1727};"
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
        "ops_health": {
            "status": "ok",
            "stages": {
                "market_feed": {
                    "status": "ok",
                    "fronts": {
                        "b3": {"age_days": 0.2, "max_age_days": 4},
                        "crypto": {"age_days": 0.01, "max_age_days": 1},
                    },
                }
            },
        },
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
    assert result["freshness"]["status"] == "online"
    assert result["freshness"]["sources"]["b3"] == "online"
    assert result["freshness"]["sources"]["crypto"] == "online"
    assert result["freshness"]["sources"]["imoveis"] == "online"


def test_dashboard_payload_gate_reports_partial_freshness_without_ops_fronts() -> None:
    payload = {
        "ops_health": {"status": "ok"},
        "thesis_history_overview": {"total_tested": 879},
        "historical_analysis_summary": {"thesis_count": 879},
        "thesis_open_operations": [],
    }

    result = gate.inspect_dashboard_payload(payload)

    assert result["freshness"]["status"] == "partial"
    assert result["freshness"]["sources"]["b3"] == "missing"
    assert result["freshness"]["sources"]["crypto"] == "missing"
    assert result["freshness"]["sources"]["imoveis"] == "missing"


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


def test_dashboard_fetch_requests_identity_response_and_closed_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        del timeout
        captured.update(dict(request.header_items()))
        return FakeResponse()

    monkeypatch.setattr(gate, "urlopen", fake_urlopen)

    assert gate._fetch_json("https://example.test/api", 1.0) == {"ok": True}
    assert captured["Connection"] == "close"
    assert captured["Accept-encoding"] == "identity"


def test_dashboard_url_gate_retries_transient_fetch_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "ops_health": {"status": "ok"},
        "thesis_history_overview": {"total_tested": 879},
        "historical_analysis_summary": {"thesis_count": 879},
        "thesis_open_operations": [],
    }
    calls = {"count": 0}

    def fake_fetch_json(url: str, timeout_seconds: float) -> dict[str, object]:
        del url, timeout_seconds
        calls["count"] += 1
        if calls["count"] == 1:
            raise gate.QualityGateFailure("Falha ao buscar api: timeout")
        return payload

    monkeypatch.setattr(gate, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(gate.time, "sleep", lambda _seconds: None)

    result = gate.inspect_dashboard_url("https://example.test/api", attempts=3)

    assert calls["count"] == 4
    assert result["fetch_attempts"] == 4
    assert result["stable_total_tested"] == 879
    assert len(result["transient_errors"]) == 1
