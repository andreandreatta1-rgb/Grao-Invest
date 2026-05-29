from scripts.run_real_estate_radar_maturation_cycle import _extract_mega_code, _format_brl


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
