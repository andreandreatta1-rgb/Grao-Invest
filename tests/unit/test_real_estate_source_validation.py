from __future__ import annotations

from app.services.real_estate_source_validation import validate_real_estate_source_url


class _Response:
    def __init__(self, status_code: int, text: str, url: str = "https://example.com/imovel") -> None:
        self.status_code = status_code
        self.text = text
        self.url = url


def test_source_validation_marks_404_as_unavailable() -> None:
    result = validate_real_estate_source_url(
        "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html",
        fetcher=lambda url, timeout: _Response(404, "Nao encontrado", url),
    )

    assert result.status == "unavailable"
    assert result.reason == "Fonte retornou HTTP 404."


def test_source_validation_detects_expired_listing_phrases() -> None:
    result = validate_real_estate_source_url(
        "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html",
        fetcher=lambda url, timeout: _Response(
            200,
            "Este anuncio nao esta mais publicado pelo anunciante.",
            url,
        ),
    )

    assert result.status == "expired"
    assert "nao esta mais publicado" in result.reason


def test_source_validation_rejects_generic_search_pages() -> None:
    result = validate_real_estate_source_url(
        "https://www.imovelweb.com.br/apartamentos-venda-saude-sao-paulo.html",
        fetcher=lambda url, timeout: _Response(200, "Apartamentos a venda na Saude", url),
    )

    assert result.status == "ambiguous"
    assert result.reason == "Fonte parece ser busca/listagem generica, nao um lote ou anuncio individual."


def test_source_validation_accepts_individual_frazao_lot_details() -> None:
    result = validate_real_estate_source_url(
        "https://www.frazaoleiloes.com.br/Auction/LotDetails/37528",
        fetcher=lambda url, timeout: _Response(
            200,
            "SAO PAULO/SP - BAIRRO SAUDE - APARTAMENTO - IMOVEL OCUPADO. "
            "Area privativa: 74,140m2 Lance minimo R$ 388.700,00 Codigo do imovel 923616",
            url,
        ),
    )

    assert result.status == "valid"
    assert result.reason == "Fonte individual validada."


def test_source_validation_flags_ended_auctions_as_expired() -> None:
    result = validate_real_estate_source_url(
        "https://www.frazaoleiloes.com.br/Auction/LotDetails/11024",
        fetcher=lambda url, timeout: _Response(
            200,
            "Leilao de Apartamento - Campinas/SP. Encerrado Leilao: 23/12/2022 as 11h00.",
            url,
        ),
    )

    assert result.status == "expired"
    assert "encerrado" in result.reason.lower()


def test_source_validation_accepts_mega_leiloes_detail_pages_even_without_text_markers() -> None:
    result = validate_real_estate_source_url(
        (
            "https://www.megaleiloes.com.br/imoveis/apartamentos/sp/campinas/"
            "apartamento-79-m2-edificio-palmares-campinas-sp-j122562"
        ),
        fetcher=lambda url, timeout: _Response(200, "OK", url),
    )

    assert result.status == "valid"


def test_source_validation_accepts_mega_leiloes_x_series_detail_pages() -> None:
    result = validate_real_estate_source_url(
        (
            "https://www.megaleiloes.com.br/imoveis/apartamentos/sp/sao-paulo/"
            "apartamento-127-m2-paraiso-do-morumbi-sao-paulo-sp-x124760"
        ),
        fetcher=lambda url, timeout: _Response(200, "OK", url),
    )

    assert result.status == "valid"
