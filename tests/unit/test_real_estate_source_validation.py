from __future__ import annotations

import app.services.real_estate_source_validation as source_validation
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


def test_source_validation_follows_leilaoimovel_edital_to_official_leiloeiro() -> None:
    aggregator_url = "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-pinheiros-2803839"
    edital_url = "https://suporteleiloes.com.br/editais/2803839-edital.pdf"
    official_url = "https://www.webleiloes.com.br/lote/12345"
    calls: list[str] = []

    def fetcher(url: str, timeout: float) -> _Response:
        calls.append(url)
        if url == aggregator_url:
            return _Response(200, f'<a href="{edital_url}">Edital</a>', url)
        if url == edital_url:
            return _Response(200, f"Edital do lote. Leiloeiro oficial: {official_url}", url)
        if url == official_url:
            return _Response(
                200,
                "Area privativa 33,50m2. Matricula 123. Lance minimo R$ 100.000,00.",
                url,
            )
        raise AssertionError(f"unexpected url: {url}")

    result = validate_real_estate_source_url(aggregator_url, fetcher=fetcher)
    payload = result.as_payload()

    assert result.status == "valid"
    assert result.url == official_url
    assert payload["investigation_status"] == "validado"
    assert payload["aggregator_url"] == aggregator_url
    assert payload["edital_url"] == edital_url
    assert payload["official_url"] == official_url
    assert calls == [aggregator_url, edital_url, official_url]


def test_source_validation_asks_user_for_credentials_when_official_leiloeiro_blocks_access() -> None:
    aggregator_url = "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-pinheiros-2803839"
    edital_url = "https://suporteleiloes.com.br/editais/2803839-edital.pdf"
    official_url = "https://www.webleiloes.com.br/lote/12345"

    def fetcher(url: str, timeout: float) -> _Response:
        if url == aggregator_url:
            return _Response(200, f'<a href="{edital_url}">Edital</a>', url)
        if url == edital_url:
            return _Response(200, f"Edital do lote. Leiloeiro oficial: {official_url}", url)
        if url == official_url:
            return _Response(403, "Cadastro necessario para continuar.", url)
        raise AssertionError(f"unexpected url: {url}")

    result = validate_real_estate_source_url(aggregator_url, fetcher=fetcher)
    payload = result.as_payload()

    assert result.status == "access_required"
    assert payload["investigation_status"] == "bloqueado_por_acesso"
    assert payload["requires_user_action"] is True
    assert "cadastro/login" in str(payload["user_action"])
    assert payload["credential_file_hint"] == "data/secure/real_estate_sources/www.webleiloes.com.br.credentials.json"
    assert payload["aggregator_url"] == aggregator_url
    assert payload["edital_url"] == edital_url
    assert payload["official_url"] == official_url


def test_default_fetcher_uses_browser_headers_for_auction_sites(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url: str, **kwargs: object) -> _Response:
        captured["url"] = url
        captured.update(kwargs)
        return _Response(
            200,
            "Area privativa 33m2. Matricula 123. Lance minimo R$ 100.000,00.",
            url,
        )

    monkeypatch.setattr(source_validation.httpx, "get", fake_get)

    result = validate_real_estate_source_url("https://www.webleiloes.com.br/lote/12345")

    headers = captured["headers"]
    assert result.status == "valid"
    assert isinstance(headers, dict)
    assert "Mozilla/5.0" in headers["User-Agent"]
    assert headers["Accept-Language"].startswith("pt-BR")
