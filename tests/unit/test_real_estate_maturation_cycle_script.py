from scripts.run_real_estate_radar_maturation_cycle import (
    MEGA_INDEXES_BY_CITY,
    _decision_from_analysis,
    _extract_auction_schedule_from_pdf_text,
    _extract_occupancy_status_from_signals_text,
    _extract_mega_code,
    _extract_private_area_m2_from_pdf_text,
    _find_location_from_html,
    _find_mega_appraisal_v2,
    _focus_pdf_text_for_extracted_location,
    _format_brl,
    _mega_property_type_from_url,
    _repair_mojibake_text_v2,
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


def test_decision_from_analysis_keeps_discard_even_with_rights_over_and_high_roi() -> None:
    analysis = {
        "suggested_status": "Descartado",
        "scenarios": {"base": {"roi_pct": 65.2}},
        "pending_items": [{"key": "rights_over_asset"}],
    }
    assert _decision_from_analysis(analysis) == "sai"


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


def test_repair_mojibake_text_v2_repairs_common_sequences() -> None:
    assert _repair_mojibake_text_v2("Jos\u00c3\u00a9") == "José"
    assert _repair_mojibake_text_v2("N\u00c2\u00ba 101") == "Nº 101"


def test_find_location_from_html_parses_rightmost_fields() -> None:
    html = (
        '<div class="locality item">'
        '<div class="header">Localizacao</div>'
        '<div class="value">'
        "Rua Jos\u00c3\u00a9 Luiz Camargo Moreira, 33, Apartamento N\u00c2\u00ba 101 - Condom\u00c3\u00adnio I Home, "
        "Mans\u00c3\u00b5es Santo Ant\u00c3\u00b4nio, Campinas, SP"
        "</div></div>"
    )
    street, neighborhood, city = _find_location_from_html(html)
    assert "Rua José Luiz Camargo Moreira" in street
    assert "33" in street
    assert neighborhood == "Mansões Santo Antônio"
    assert city == "Campinas"


def test_find_mega_appraisal_v2_reads_valor_de_avaliacao_block() -> None:
    html = '<div class="header">Valor de Avaliacao</div><div class="value">R$ 881.000,00</div>'
    assert _find_mega_appraisal_v2(html) == 881000.0


def test_extract_private_area_supports_util_de_pattern() -> None:
    raw = "com as seguintes áreas: útil de 129,78m2, comum de 29,24m2, total de 159,02m2."
    assert _extract_private_area_m2_from_pdf_text(raw) == 129.78


def test_extract_auction_schedule_reads_judicial_and_event_dates() -> None:
    judicial = (
        "DO LEILÃO - o 1º Leilão terá início no dia 19/06/2026 às 15:00 h e se encerrará dia 22/06/2026 às 15:00 h; "
        "seguir-se-á o 2º Leilão, que terá início no dia 22/06/2026 às 15:01 h e se encerrará no dia 14/07/2026 às 15:00 h."
    )
    schedule = _extract_auction_schedule_from_pdf_text(judicial)
    assert schedule["first_start_brt"] == "2026-06-19T15:00-03:00"
    assert schedule["first_end_brt"] == "2026-06-22T15:00-03:00"
    assert schedule["second_start_brt"] == "2026-06-22T15:01-03:00"
    assert schedule["second_end_brt"] == "2026-07-14T15:00-03:00"
    assert schedule["basis"] == "pdf"

    extrajudicial = "EDITAL DE LEILÃO SOMENTE ON-LINE Data: 08 de junho de 2026, às 15:00 horas"
    schedule = _extract_auction_schedule_from_pdf_text(extrajudicial)
    assert schedule["event_datetime_brt"] == "2026-06-08T15:00-03:00"
    assert schedule["basis"] == "pdf"
