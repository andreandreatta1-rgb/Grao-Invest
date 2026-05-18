from __future__ import annotations

import json
from pathlib import Path


def test_folha_frazao_candidates_are_seeded_with_individual_validated_sources() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    rows = [
        row
        for row in payload.get("thesis_open_operations", [])
        if str(row.get("thesis_id", "")).startswith("IM-FOLHA-FRAZAO-")
    ]

    assert {row["thesis_id"] for row in rows} >= {
        "IM-FOLHA-FRAZAO-SAUDE-37528",
        "IM-FOLHA-FRAZAO-PARADA-INGLESA-37570",
        "IM-FOLHA-FRAZAO-CAMPINAS-37386",
        "IM-FOLHA-FRAZAO-BUTANTA-37467",
        "IM-FOLHA-FRAZAO-BELENZINHO-37539",
    }
    for row in rows:
        assert "/Auction/LotDetails/" in row["source_url"]
        assert row["real_estate_analysis"]["source_validation"]["status"] == "valid"
        assert row["real_estate_analysis"]["source_validation"]["reason"] == "Fonte individual validada."
        assert row["is_open"] is True
