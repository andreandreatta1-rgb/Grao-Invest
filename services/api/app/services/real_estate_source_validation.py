from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import re
import unicodedata
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class SourceValidationResult:
    url: str
    status: str
    reason: str
    checked_at: str
    http_status: int | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "url": self.url,
            "status": self.status,
            "reason": self.reason,
            "checked_at": self.checked_at,
            "http_status": self.http_status,
        }


Fetcher = Callable[[str, float], object]


EXPIRED_MARKERS = [
    "anuncio nao esta mais publicado",
    "anuncio nao encontrado",
    "anuncio indisponivel",
    "imovel nao esta mais disponivel",
    "imovel indisponivel",
    "lote retirado",
    "lote encerrado",
    "encerrado leilao",
    "leilao encerrado",
    "venda encerrada",
]

INDIVIDUAL_PATH_PATTERNS = [
    re.compile(r"/auction/lotdetails/\d+", re.IGNORECASE),
    re.compile(r"/lote[s]?/[^/]+", re.IGNORECASE),
    re.compile(r"/propriedades/[^/]+", re.IGNORECASE),
    re.compile(r"/property/[^/]+", re.IGNORECASE),
    re.compile(r"/imovel/[^/]+", re.IGNORECASE),
    re.compile(r"/imoveis/.+-[jx]\d{5,7}", re.IGNORECASE),
]

GENERIC_SEARCH_PATH_MARKERS = [
    "apartamentos-venda",
    "casas-venda",
    "imoveis-venda",
    "aluguel",
    "busca",
    "search",
    "comprar",
]

INDIVIDUAL_TEXT_MARKERS = [
    "area privativa",
    "area util",
    "matricula",
    "inscricao prefeitura",
    "iptu",
    "lance minimo",
    "codigo do imovel",
    "imovel ocupado",
    "condicoes de pagamento",
]


def _checked_at() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _default_fetcher(url: str, timeout: float) -> httpx.Response:
    return httpx.get(
        url,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; GraoInvestSourceValidator/1.0; "
                "+https://grao-invest.vercel.app)"
            )
        },
        timeout=timeout,
    )


def _result(
    *,
    url: str,
    status: str,
    reason: str,
    checked_at: str,
    http_status: int | None = None,
) -> SourceValidationResult:
    return SourceValidationResult(
        url=url,
        status=status,
        reason=reason,
        checked_at=checked_at,
        http_status=http_status,
    )


def _looks_like_generic_search_page(url: str) -> bool:
    parsed = urlparse(url)
    path = _normalize_text(parsed.path)
    host = _normalize_text(parsed.netloc)
    if "frazaoleiloes.com.br" in host and re.search(r"/auction/index/\d+", path):
        return True
    if any(pattern.search(path) for pattern in INDIVIDUAL_PATH_PATTERNS):
        return False
    return any(marker in path for marker in GENERIC_SEARCH_PATH_MARKERS)


def _looks_like_individual_source(url: str, text: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path
    normalized_text = _normalize_text(text)
    if any(pattern.search(path) for pattern in INDIVIDUAL_PATH_PATTERNS):
        return True
    marker_count = sum(1 for marker in INDIVIDUAL_TEXT_MARKERS if marker in normalized_text)
    return marker_count >= 3


def validate_real_estate_source_url(
    source_url: str | None,
    *,
    fetcher: Fetcher | None = None,
    timeout: float = 8.0,
) -> SourceValidationResult:
    checked_at = _checked_at()
    url = str(source_url or "").strip()
    if not url:
        return _result(
            url="",
            status="unchecked",
            reason="Fonte ausente.",
            checked_at=checked_at,
        )

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return _result(
            url=url,
            status="ambiguous",
            reason="URL da fonte nao e HTTP/HTTPS valida.",
            checked_at=checked_at,
        )

    if _looks_like_generic_search_page(url):
        return _result(
            url=url,
            status="ambiguous",
            reason="Fonte parece ser busca/listagem generica, nao um lote ou anuncio individual.",
            checked_at=checked_at,
        )

    try:
        response = (fetcher or _default_fetcher)(url, timeout)
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return _result(
            url=url,
            status="ambiguous",
            reason=f"Fonte exigiu validacao manual: {exc.__class__.__name__}.",
            checked_at=checked_at,
        )

    http_status = int(getattr(response, "status_code", 0) or 0)
    final_url = str(getattr(response, "url", url) or url)
    text = str(getattr(response, "text", "") or "")
    normalized_text = _normalize_text(text)

    if http_status in {404, 410}:
        return _result(
            url=final_url,
            status="unavailable",
            reason=f"Fonte retornou HTTP {http_status}.",
            checked_at=checked_at,
            http_status=http_status,
        )
    if http_status in {401, 403, 429}:
        return _result(
            url=final_url,
            status="ambiguous",
            reason=f"Fonte bloqueou validacao automatica com HTTP {http_status}.",
            checked_at=checked_at,
            http_status=http_status,
        )
    if http_status >= 500:
        return _result(
            url=final_url,
            status="ambiguous",
            reason=f"Fonte instavel retornou HTTP {http_status}.",
            checked_at=checked_at,
            http_status=http_status,
        )

    for marker in EXPIRED_MARKERS:
        if marker in normalized_text:
            return _result(
                url=final_url,
                status="expired",
                reason=f"Fonte indica que o anuncio/lote expirou: {marker}.",
                checked_at=checked_at,
                http_status=http_status,
            )

    if _looks_like_generic_search_page(final_url):
        return _result(
            url=final_url,
            status="ambiguous",
            reason="Fonte parece ser busca/listagem generica, nao um lote ou anuncio individual.",
            checked_at=checked_at,
            http_status=http_status,
        )

    if not _looks_like_individual_source(final_url, text):
        return _result(
            url=final_url,
            status="ambiguous",
            reason="Fonte nao trouxe sinais suficientes de anuncio/lote individual.",
            checked_at=checked_at,
            http_status=http_status,
        )

    return _result(
        url=final_url,
        status="valid",
        reason="Fonte individual validada.",
        checked_at=checked_at,
        http_status=http_status,
    )
