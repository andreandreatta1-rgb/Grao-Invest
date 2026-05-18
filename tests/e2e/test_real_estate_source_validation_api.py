from __future__ import annotations

import pytest

from app.main import AUTH_DISABLED
from app.services.real_estate_source_validation import SourceValidationResult


def _candidate_payload(source_url: str = "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html") -> dict[str, object]:
    return {
        "title": "Apto Fonte Expirada",
        "source_url": source_url,
        "origin": "Imovelweb",
        "strategy": "Arbitragem sem reforma + venda direta",
        "city": "Sao Paulo",
        "neighborhood": "Saude",
        "property_type": "Apartamento",
        "asking_price": 390000.0,
        "market_value_estimate": 520000.0,
        "estimated_sale_conservative": 500000.0,
        "estimated_sale_base": 520000.0,
        "renovation_type": "leve",
        "renovation_budget": 25000.0,
        "carrying_months": 6,
        "monthly_carrying_cost": 1800.0,
        "acquisition_costs": 19000.0,
        "selling_commission_pct": 6.0,
        "cash_needed": 132000.0,
        "occupancy_status": "desconhecido",
        "has_registration": False,
        "condo_debt_known": False,
        "iptu_debt_known": False,
        "sale_comparables_count": 1,
        "rent_comparables_count": 0,
        "plan_b": "Usar como comparavel se a fonte nao estiver viva.",
    }


def test_candidate_with_expired_source_is_quarantined_and_not_open(
    client,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    monkeypatch.setattr(
        main_module,
        "validate_real_estate_source_url",
        lambda url: SourceValidationResult(
            url=url,
            status="expired",
            reason="Fonte informa que o anuncio nao esta mais publicado.",
            checked_at="2026-05-18T12:00:00+00:00",
            http_status=200,
        ),
    )

    create_response = client.post(
        "/api/real-estate/candidates",
        json=_candidate_payload(),
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["source_validation_status"] == "expired"
    assert created["source_validation_reason"] == "Fonte informa que o anuncio nao esta mais publicado."
    assert created["status"] == "Fonte indisponivel"
    assert created["analysis"]["suggested_status"] == "Descartado"
    assert created["analysis"]["next_action"] == "Fonte informa que o anuncio nao esta mais publicado."

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    original_data_dir = main_module.data_dir
    original_bundled_data_dir = main_module.bundled_data_dir
    main_module.data_dir = runtime_dir
    main_module.bundled_data_dir = runtime_dir
    try:
        dashboard_response = client.get("/api/dashboard/summary/1")
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
    finally:
        main_module.data_dir = original_data_dir
        main_module.bundled_data_dir = original_bundled_data_dir

    row = next(
        item
        for item in dashboard["thesis_open_operations"]
        if item["thesis_id"] == f"IM-RADAR-{created['id']}"
    )
    assert row["status"] == "Fechada"
    assert row["outcome"] == "Fonte indisponivel"
    assert row["is_open"] is False
    assert row["real_estate_analysis"]["source_validation"]["status"] == "expired"


def test_candidate_with_valid_source_keeps_source_validation_in_payload(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    monkeypatch.setattr(
        main_module,
        "validate_real_estate_source_url",
        lambda url: SourceValidationResult(
            url=url,
            status="valid",
            reason="Fonte individual validada.",
            checked_at="2026-05-18T12:05:00+00:00",
            http_status=200,
        ),
    )

    create_response = client.post(
        "/api/real-estate/candidates",
        json=_candidate_payload(
            "https://www.frazaoleiloes.com.br/Auction/LotDetails/37528",
        ),
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["source_validation_status"] == "valid"
    assert created["source_checked_at"] == "2026-05-18T12:05:00+00:00"
    assert created["analysis"]["source_validation"]["status"] == "valid"
    assert {item["key"] for item in created["analysis"]["clarified_items"]} >= {
        "source_validation"
    }
