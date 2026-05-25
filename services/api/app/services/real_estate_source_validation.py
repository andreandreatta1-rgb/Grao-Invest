from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
import re
import unicodedata
from urllib.parse import urljoin, urlparse

import httpx


@dataclass(frozen=True)
class SourceValidationResult:
    url: str
    status: str
    reason: str
    checked_at: str
    http_status: int | None = None
    aggregator_url: str | None = None
    official_url: str | None = None
    edital_url: str | None = None
    access_status: str | None = None
    requires_user_action: bool = False
    user_action: str | None = None
    credential_file_hint: str | None = None

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "url": self.url,
            "status": self.status,
            "reason": self.reason,
            "checked_at": self.checked_at,
            "http_status": self.http_status,
            "investigation_policy": "investigador_implacavel",
            "investigation_status": _investigation_status(self.status),
        }
        if self.aggregator_url:
            payload["aggregator_url"] = self.aggregator_url
        if self.official_url:
            payload["official_url"] = self.official_url
        if self.edital_url:
            payload["edital_url"] = self.edital_url
        if self.access_status:
            payload["access_status"] = self.access_status
        if self.requires_user_action:
            payload["requires_user_action"] = True
        if self.user_action:
            payload["user_action"] = self.user_action
        if self.credential_file_hint:
            payload["credential_file_hint"] = self.credential_file_hint
        return payload


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
    re.compile(r"/oferta/leilao/.+", re.IGNORECASE),
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

ACCESS_TEXT_MARKERS = [
    "login",
    "cadastro",
    "cadastre-se",
    "captcha",
    "recaptcha",
    "acesso restrito",
    "area restrita",
    "faca seu cadastro",
    "entre para continuar",
]

URL_PATTERN = re.compile(r"https?://[^\s\"'<>),;]+", re.IGNORECASE)

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


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = next((value for key, value in attrs if key.lower() == "href" and value), None)
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return
        self.links.append((self._current_href, " ".join(self._current_text)))
        self._current_href = None
        self._current_text = []


def _extract_links(base_url: str, html: str) -> list[tuple[str, str]]:
    parser = _LinkParser()
    parser.feed(html or "")
    links = [(urljoin(base_url, href), text) for href, text in parser.links]
    links.extend((match.group(0).rstrip("."), "") for match in URL_PATTERN.finditer(html or ""))
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for href, label in links:
        if href in seen:
            continue
        seen.add(href)
        unique.append((href, label))
    return unique


def _investigation_status(status: str) -> str:
    normalized = _normalize_text(status)
    if normalized == "valid":
        return "validado"
    if normalized == "access_required":
        return "bloqueado_por_acesso"
    if normalized in {"expired", "unavailable"}:
        return "nao_encontrado_apos_busca"
    if normalized in {"unchecked", ""}:
        return "ambiguo"
    return "ambiguo"


def _default_fetcher(url: str, timeout: float) -> httpx.Response:
    return httpx.get(
        url,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
    aggregator_url: str | None = None,
    official_url: str | None = None,
    edital_url: str | None = None,
    access_status: str | None = None,
    requires_user_action: bool = False,
    user_action: str | None = None,
    credential_file_hint: str | None = None,
) -> SourceValidationResult:
    return SourceValidationResult(
        url=url,
        status=status,
        reason=reason,
        checked_at=checked_at,
        http_status=http_status,
        aggregator_url=aggregator_url,
        official_url=official_url,
        edital_url=edital_url,
        access_status=access_status,
        requires_user_action=requires_user_action,
        user_action=user_action,
        credential_file_hint=credential_file_hint,
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


def _credential_file_hint(url: str) -> str:
    host = _normalize_text(urlparse(url).netloc)
    safe_host = re.sub(r"[^a-z0-9.-]+", "-", host).strip("-") or "leiloeiro"
    return f"data/secure/real_estate_sources/{safe_host}.credentials.json"


def _is_access_blocked_text(text: str) -> bool:
    normalized_text = _normalize_text(text)
    return any(marker in normalized_text for marker in ACCESS_TEXT_MARKERS)


def _is_official_leiloeiro_url(url: str) -> bool:
    host = _normalize_text(urlparse(url).netloc)
    if "leilaoimovel.com.br" in host or "suporteleiloes.com.br" in host:
        return False
    return any(
        marker in host
        for marker in (
            "webleiloes",
            "megaleiloes",
            "frazaoleiloes",
            "sold",
            "lanceja",
            "hastavip",
            "freitasleiloeiro",
            "vipleiloes",
            "zuk",
        )
    )


def _leilaoimovel_evidence(
    url: str,
    text: str,
    *,
    fetcher: Fetcher | None,
    timeout: float,
) -> dict[str, str]:
    links = _extract_links(url, text)
    official_url = ""
    edital_url = ""
    for href, label in links:
        parsed = urlparse(href)
        host = _normalize_text(parsed.netloc)
        normalized_href = _normalize_text(href)
        normalized_label = _normalize_text(label)
        if not edital_url and (
            (normalized_href.endswith(".pdf") and "edital" in normalized_href)
            or "edital" in normalized_label
            or "suporteleiloes.com.br" in host
        ):
            edital_url = href
        if not official_url and (
            _is_official_leiloeiro_url(href)
            or "ver anuncio no leiloeiro" in normalized_label
            or "ver anuncio no leiloeiro" in normalized_href
        ):
            official_url = href

    if edital_url and not official_url:
        try:
            edital_response = (fetcher or _default_fetcher)(edital_url, timeout)
            edital_text = str(getattr(edital_response, "text", "") or "")
        except (httpx.HTTPError, OSError, ValueError):
            edital_text = ""
        for href, _label in _extract_links(edital_url, edital_text):
            if _is_official_leiloeiro_url(href):
                official_url = href
                break

    return {"official_url": official_url, "edital_url": edital_url}


def _with_source_chain(
    result: SourceValidationResult,
    *,
    aggregator_url: str,
    official_url: str,
    edital_url: str | None,
    reason: str,
) -> SourceValidationResult:
    return _result(
        url=result.url,
        status=result.status,
        reason=reason,
        checked_at=result.checked_at,
        http_status=result.http_status,
        aggregator_url=aggregator_url,
        official_url=official_url,
        edital_url=edital_url,
        access_status=result.access_status,
        requires_user_action=result.requires_user_action,
        user_action=result.user_action,
        credential_file_hint=result.credential_file_hint,
    )


def validate_real_estate_source_url(
    source_url: str | None,
    *,
    fetcher: Fetcher | None = None,
    timeout: float = 8.0,
    _depth: int = 0,
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
            status="access_required",
            reason=(
                f"Fonte bloqueou validacao automatica com HTTP {http_status}; "
                "tentar via navegador, cadastro/login ou credenciais do leiloeiro."
            ),
            checked_at=checked_at,
            http_status=http_status,
            access_status="blocked_by_site",
            requires_user_action=True,
            user_action=(
                "Criar cadastro/login no leiloeiro quando necessario e anexar credenciais "
                "para a app continuar a diligencia."
            ),
            credential_file_hint=_credential_file_hint(final_url),
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

    if _is_access_blocked_text(text):
        return _result(
            url=final_url,
            status="access_required",
            reason="Fonte exige cadastro/login para continuar a validacao.",
            checked_at=checked_at,
            http_status=http_status,
            access_status="login_or_cadastro_required",
            requires_user_action=True,
            user_action=(
                "Criar cadastro/login no leiloeiro quando necessario e anexar credenciais "
                "para a app continuar a diligencia."
            ),
            credential_file_hint=_credential_file_hint(final_url),
        )

    final_host = _normalize_text(urlparse(final_url).netloc)
    if "leilaoimovel.com.br" in final_host:
        evidence = _leilaoimovel_evidence(
            final_url,
            text,
            fetcher=fetcher,
            timeout=timeout,
        )
        official_url = evidence.get("official_url", "")
        edital_url = evidence.get("edital_url", "")
        if official_url and _depth < 3:
            official = validate_real_estate_source_url(
                official_url,
                fetcher=fetcher,
                timeout=timeout,
                _depth=_depth + 1,
            )
            reason = (
                "Fonte oficial localizada a partir do agregador e do edital."
                if official.status == "valid"
                else f"Fonte oficial localizada, mas ainda exige validacao: {official.reason}"
            )
            return _with_source_chain(
                official,
                aggregator_url=final_url,
                official_url=official_url,
                edital_url=edital_url or None,
                reason=reason,
            )
        return _result(
            url=final_url,
            status="ambiguous",
            reason=(
                "Fonte do Leilao Imovel e agregador; a app nao comprovou a ponte "
                "edital -> leiloeiro oficial."
            ),
            checked_at=checked_at,
            http_status=http_status,
            aggregator_url=final_url,
            edital_url=edital_url or None,
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
