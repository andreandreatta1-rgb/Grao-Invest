from scripts.run_real_estate_radar_maturation_cycle import (
    MEGA_INDEXES_BY_CITY,
    _extract_occupancy_status_from_signals_text,
    _extract_mega_code,
    _extract_private_area_m2_from_pdf_text,
    _focus_pdf_text_for_extracted_location,
    _format_brl,
    _mega_property_type_from_url,
)


def test_extract_mega_code_from_url() -> None:
    assert (
        _extract_mega_code(
            "https://www.megaleiloes.com.br/imoveis/apartamentos/sp/sao-paulo/"
            "apartamento-79-m2-02-vagas-moema-sao-paulo-sp-x122477"
        )
        == "X122477"
    )
    assert (
        _extract_mega_code(
            "https://www.megaleiloes.com.br/imoveis/apartamentos/sp/campinas/"
            "apartamento-239-m2-02-vagas-centro-campinas-sp-j122547"
        )
        == "J122547"
    )


def test_format_brl_handles_negative_and_zero() -> None:
    assert _format_brl(0.0) == "R$ 0,00"
    assert _format_brl(12.3) == "R$ 12,30"
    assert _format_brl(-12.3) == "-R$ 12,30"
    assert _format_brl(-1234.5) == "-R$ 1.234,50"


def test_mega_indexes_include_commercial_for_campinas() -> None:
    assert any("imoveis-comerciais" in url for url in MEGA_INDEXES_BY_CITY["Campinas"])


def test_mega_property_type_detects_commercial() -> None:
    assert (
        _mega_property_type_from_url(
            "https://www.megaleiloes.com.br/imoveis/imoveis-comerciais/sp/campinas/"
            "imovel-comercial-com-4860-m2-parque-italia-campinas-sp-j123490"
        )
        == "Comercial"
    )


def test_focus_pdf_text_prevents_cross_lot_area_leakage() -> None:
    raw = (
        "LOTE 01 - APARTAMENTO. Rua Foo. Area real privativa de 79,42 m2.\n"
        "LOTE 03 - APARTAMENTO. Av. General Olimpio da Silveira, n 196. Area util 36,61m2.\n"
    )
    extracted = {"location": {"street": "Avenida General Olímpio da Silveira, 196"}}
    focused = _focus_pdf_text_for_extracted_location(raw=raw, extracted=extracted)
    assert "36,61" in focused
    assert "79,42" not in focused
    assert _extract_private_area_m2_from_pdf_text(raw) == 79.42
    assert _extract_private_area_m2_from_pdf_text(focused) == 36.61


def test_extract_occupancy_status_ignores_desocupacao_phrase() -> None:
    text = "Obs.: (i) Imovel ocupado por locatario. Desocupacao por conta do arrematante."
    assert _extract_occupancy_status_from_signals_text(text) == "ocupado"
    assert _extract_occupancy_status_from_signals_text("IMOVEL DESOCUPADO.") == "desocupado"
