from __future__ import annotations

import json
import html as html_lib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.real_estate_radar import build_candidate_analysis  # noqa: E402
from app.services.real_estate_source_validation import validate_real_estate_source_url  # noqa: E402


REPORTS_DIR = ROOT / "data" / "reports"
MEGA_BASE = "https://www.megaleiloes.com.br"
CHAVES_BASE = "https://www.chavesnamao.com.br"
WIN_FETCH_PS1 = ROOT / "scripts" / "win_fetch_url.ps1"

SCOPE = {
    "cities": ["Sao Paulo", "Campinas"],
    "focus": "confiabilidade > quantidade",
}

MEGA_INDEXES_BY_CITY: dict[str, list[str]] = {
    "Campinas": [
        f"{MEGA_BASE}/imoveis/apartamentos/sp/campinas/",
        f"{MEGA_BASE}/imoveis/casas/sp/campinas/",
        f"{MEGA_BASE}/imoveis/imoveis-comerciais/sp/campinas/",
    ],
    "Sao Paulo": [
        f"{MEGA_BASE}/imoveis/apartamentos/sp/sao-paulo/",
        f"{MEGA_BASE}/imoveis/casas/sp/sao-paulo/",
        f"{MEGA_BASE}/imoveis/imoveis-comerciais/sp/sao-paulo/",
    ],
}

DEFAULT_NEXT_TARGETS = [
    "Capturar datas do leilao (1o/2o leilao) quando disponiveis no HTML.",
    "OCR opcional/flag para PDFs de matricula escaneados (onus/ocupacao/dividas).",
]

HELP_TEXT = """Radar Imobiliário — Maturação

Uso:
  python scripts/run_real_estate_radar_maturation_cycle.py

Observações:
  - Este script roda um ciclo completo (1 candidato Campinas + 1 candidato São Paulo),
    valida fontes e gera relatórios em data/reports/.
  - Este script não aceita argumentos (apenas -h/--help).

Env vars úteis:
  - RADAR_MATURATION_PIN_CAMPINAS_URL: fixa a URL do candidato de Campinas
  - RADAR_MATURATION_PIN_SAO_PAULO_URL: fixa a URL do candidato de São Paulo
  - RADAR_MATURATION_REUSE_COOLDOWN_HOURS: cooldown de reuso (default=12)
  - RADAR_MATURATION_CLOSEOUT_JSON: JSON com listas para closeout (fragilities/fixes/tests/next_targets)
"""

CHAVES_INDEX_BY_CITY: dict[str, str] = {
    "Campinas": f"{CHAVES_BASE}/apartamentos-a-venda/sp-campinas/",
    "Sao Paulo": f"{CHAVES_BASE}/apartamentos-a-venda/sp-sao-paulo/",
}

CHAVES_SALE_INDEX_BY_CITY_AND_KIND: dict[str, dict[str, str]] = {
    "Campinas": {
        "residential": f"{CHAVES_BASE}/apartamentos-a-venda/sp-campinas/",
        "commercial": f"{CHAVES_BASE}/imoveis-comerciais-a-venda/sp-campinas/",
    },
    "Sao Paulo": {
        "residential": f"{CHAVES_BASE}/apartamentos-a-venda/sp-sao-paulo/",
        "commercial": f"{CHAVES_BASE}/imoveis-comerciais-a-venda/sp-sao-paulo/",
    },
}


def _guess_chaves_kind(property_type: str) -> str:
    kind = (property_type or "").strip().lower()
    if "comercial" in kind or "galp" in kind or "loja" in kind or "sala" in kind:
        return "commercial"
    return "residential"


def _now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _slug(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _money_to_float(raw: str) -> float:
    text = (raw or "").strip()
    if not text:
        return 0.0
    text = text.replace("R$", "").replace("\xa0", " ").strip()
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _format_brl(value: float) -> str:
    if value == 0:
        return "R$ 0,00"
    abs_value = abs(value)
    rendered = f"{abs_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    prefix = "-R$ " if value < 0 else "R$ "
    return prefix + rendered


def _http_client(timeout_s: float) -> httpx.Client:
    if os.name == "nt" and WIN_FETCH_PS1.exists() and shutil.which("powershell"):
        return _WinInetClient(timeout_s=timeout_s)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    return httpx.Client(timeout=timeout_s, follow_redirects=True, headers=headers)


def _get_with_retries(client: httpx.Client, url: str, *, retries: int = 3) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(1, max(1, int(retries)) + 1):
        try:
            return client.get(url)
        except Exception as exc:
            if type(exc).__name__ not in {
                "ReadTimeout",
                "ConnectTimeout",
                "ConnectError",
                "ReadError",
                "RemoteProtocolError",
            }:
                raise
            last_exc = exc
            if attempt >= retries:
                raise
            time.sleep(0.9 * (2 ** (attempt - 1)))
    raise last_exc or RuntimeError("Unexpected retry loop termination.")


def _response_text_utf8(response: httpx.Response) -> str:
    text = response.text
    if not text:
        return text
    if ("Ã" not in text and "Â" not in text) or not getattr(response, "content", b""):
        return text
    try:
        repaired = response.content.decode("utf-8")
    except Exception:
        return text
    bad_before = text.count("Ã") + text.count("Â")
    bad_after = repaired.count("Ã") + repaired.count("Â")
    return repaired if bad_after < bad_before else text


class ConnectTimeout(Exception):
    pass


class ConnectError(Exception):
    pass


@dataclass(frozen=True)
class _WinFetchPayload:
    ok: bool
    status: int
    final_url: str
    content_type: str
    error: str


class _WinResponse:
    def __init__(self, *, status_code: int, url: str, content: bytes, text: str) -> None:
        self.status_code = status_code
        self.url = url
        self.content = content
        self.text = text

    def iter_bytes(self) -> bytes:
        chunk = 64 * 1024
        for idx in range(0, len(self.content), chunk):
            yield self.content[idx : idx + chunk]

    def __enter__(self) -> "_WinResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class _WinInetClient:
    def __init__(self, *, timeout_s: float) -> None:
        self._timeout_s = float(timeout_s or 18.0)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def __enter__(self) -> "_WinInetClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def stream(self, method: str, url: str) -> _WinResponse:
        _ = method
        return self.get(url)

    def fetcher(self, url: str, timeout: float) -> _WinResponse:
        return self.get(url, timeout_s=timeout)

    def get(self, url: str, *, timeout_s: float | None = None) -> _WinResponse:
        timeout = float(timeout_s) if timeout_s is not None else self._timeout_s
        payload, content = _powershell_fetch_bytes(
            url,
            timeout_s=timeout,
            user_agent=str(self.headers.get("User-Agent") or ""),
            accept_language=str(self.headers.get("Accept-Language") or ""),
        )
        if not payload.ok and payload.status <= 0:
            message = (payload.error or "").strip()
            lower = message.lower()
            if "tempo limite" in lower or "timed out" in lower or "timeout" in lower:
                raise ConnectTimeout(message or "timed out")
            raise ConnectError(message or "connect_failed")

        text = _decode_best_effort_text(content, hint=payload.content_type)
        text = _repair_mojibake_text(text)
        return _WinResponse(status_code=int(payload.status or 0), url=payload.final_url or url, content=content, text=text)


def _decode_best_effort_text(raw: bytes, *, hint: str = "") -> str:
    if not raw:
        return ""
    hint_lower = (hint or "").lower()
    if "charset=" in hint_lower:
        charset = hint_lower.split("charset=", 1)[1].split(";", 1)[0].strip().strip('"').strip("'")
        if charset:
            try:
                return raw.decode(charset, errors="replace")
            except Exception:
                pass
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc, errors="replace")
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _powershell_fetch_bytes(
    url: str,
    *,
    timeout_s: float,
    user_agent: str,
    accept_language: str,
    max_bytes: int = 18_000_000,
) -> tuple[_WinFetchPayload, bytes]:
    target = (url or "").strip()
    if not target:
        return _WinFetchPayload(False, 0, "", "", "missing_url"), b""

    if os.name != "nt" or not WIN_FETCH_PS1.exists() or not shutil.which("powershell"):
        return _WinFetchPayload(False, 0, target, "", "powershell_fetch_unavailable"), b""

    out_dir = Path(tempfile.mkdtemp(prefix="grao_win_fetch_"))
    out_file = out_dir / "payload.bin"
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WIN_FETCH_PS1),
            "-Url",
            target,
            "-OutFile",
            str(out_file),
            "-TimeoutSec",
            str(max(3, int(timeout_s))),
            "-UserAgent",
            user_agent or "",
            "-AcceptLanguage",
            accept_language or "",
        ]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(10, int(timeout_s) + 12),
            check=False,
        )
        raw_stdout = (completed.stdout or "").strip()
        payload_dict: dict[str, Any] = {}
        if raw_stdout:
            try:
                payload_dict = json.loads(raw_stdout)
            except json.JSONDecodeError:
                payload_dict = {"ok": False, "status": 0, "final_url": target, "error": f"bad_ps_json: {raw_stdout[:220]}"}
        else:
            payload_dict = {
                "ok": False,
                "status": 0,
                "final_url": target,
                "error": (completed.stderr or "").strip() or f"ps_rc={completed.returncode}",
            }

        payload = _WinFetchPayload(
            ok=bool(payload_dict.get("ok")),
            status=int(payload_dict.get("status") or 0),
            final_url=str(payload_dict.get("final_url") or target),
            content_type=str(payload_dict.get("content_type") or ""),
            error=str(payload_dict.get("error") or ""),
        )
        if out_file.exists():
            if out_file.stat().st_size > max_bytes:
                return _WinFetchPayload(False, payload.status, payload.final_url, payload.content_type, "too_large"), b""
            content = out_file.read_bytes()
        else:
            content = b""
        return payload, content
    finally:
        try:
            if out_file.exists():
                out_file.unlink()
        except Exception:
            pass
        try:
            out_dir.rmdir()
        except Exception:
            pass

def _repair_mojibake_text(value: str) -> str:
    raw = value or ""
    if not raw:
        return raw
    if "Ã" not in raw and "Â" not in raw:
        return raw
    try:
        repaired = raw.encode("latin-1").decode("utf-8")
    except Exception:
        try:
            repaired = raw.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            return raw
    bad_before = raw.count("Ã") + raw.count("Â")
    bad_after = repaired.count("Ã") + repaired.count("Â")
    return repaired if repaired and bad_after < bad_before else raw


def _searchable_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def _extract_html_title(html: str) -> str:
    raw = html or ""
    match = re.search(r"<title[^>]*>(?P<title>.*?)</title>", raw, flags=re.I | re.S)
    if not match:
        return ""
    title = html_lib.unescape(match.group("title") or "")
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _focus_pdf_text_for_extracted_location(*, raw: str, extracted: dict[str, Any]) -> str:
    hay = _searchable_text(raw or "")
    if not hay:
        return ""
    location = extracted.get("location") if isinstance(extracted.get("location"), dict) else {}
    street = str(location.get("street") or "").strip()
    if not street:
        return hay
    base = street.split(",", 1)[0].strip()
    base = re.sub(r"^(rua|avenida|alameda|travessa|estrada)\s+", "", base, flags=re.I).strip()
    if len(base) < 8:
        return hay
    needle = _searchable_text(base)
    idx = hay.find(needle)
    if idx < 0:
        return hay
    lot_markers = list(re.finditer(r"\blote\s+\d{1,3}\b", hay, flags=re.I))
    prev_lot = None
    next_lot = None
    for marker in lot_markers:
        if marker.start() < idx:
            prev_lot = marker
            continue
        if marker.start() > idx:
            next_lot = marker
            break
    if prev_lot:
        start = prev_lot.start()
        end = next_lot.start() if next_lot else len(hay)
        return hay[start:end]
    radius = 1800
    return hay[max(0, idx - radius) : idx + radius]


def _extract_occupancy_status_from_signals_text(text: str) -> str:
    lower = _searchable_text(text or "")
    if not lower:
        return ""
    if (
        re.search(r"\bdesocupad[oa]s?\b", lower)
        or "imovel vago" in lower
        or "sem ocupantes" in lower
        or "sem ocupacao" in lower
    ):
        return "desocupado"
    if re.search(r"\bocupad[oa]s?\b", lower) or "locatar" in lower or "sem visitacao" in lower:
        return "ocupado"
    return ""


def _first_money_after(pattern: str, text: str) -> float:
    if not text:
        return 0.0
    match = re.search(
        rf"(?:{pattern}).{{0,140}}?R\$\s*([0-9\.,]+)",
        text,
        flags=re.I,
    )
    if not match:
        return 0.0
    return _money_to_float(match.group(1))


def _extract_appraisal_value_from_pdf_text(text: str) -> float:
    if not text:
        return 0.0
    normalized = _searchable_text(text)
    patterns = (
        r"valor\s+da\s+avaliac[aã]o(?:\s+do\s+im[oó]vel)?",
        r"valor\s+de\s+avaliac[aã]o(?:\s+do\s+im[oó]vel)?",
        r"avaliac[aã]o\s+do\s+im[oó]vel",
    )
    for pattern in patterns:
        value = _first_money_after(pattern, normalized) or _first_money_after(pattern, text)
        if value > 0:
            return value
    return 0.0


def _extract_pdf_text(
    *,
    url: str,
    client: httpx.Client,
    max_bytes: int = 18_000_000,
    max_pages: int = 6,
) -> tuple[str, str]:
    """
    Best-effort PDF text extraction.

    Returns: (text, status) where status is one of:
      - ok
      - empty_text
      - dependency_missing
      - http_error:<status>
      - error:<exception>
    """
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except Exception:
        return "", "dependency_missing"

    target = (url or "").strip()
    if not target:
        return "", "error:missing_url"

    try:
        with client.stream("GET", target) as response:
            status = int(response.status_code or 0)
            if status >= 400:
                return "", f"http_error:{status}"
            buffer = bytearray()
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                buffer.extend(chunk)
                if len(buffer) > max_bytes:
                    return "", "error:too_large"
    except Exception as exc:
        return "", f"error:{type(exc).__name__}"

    try:
        reader = PdfReader(io.BytesIO(bytes(buffer)))
        parts: list[str] = []
        for page in list(reader.pages)[: max(1, int(max_pages))]:
            extracted = page.extract_text() or ""
            if extracted.strip():
                parts.append(extracted)
        text = "\n".join(parts).strip()
    except Exception as exc:
        if type(exc).__name__ == "DependencyError":
            return "", "dependency_missing"
        return "", f"error:{type(exc).__name__}"

    text = _repair_mojibake_text(text)

    if len(_searchable_text(text)) < 80:
        return text, "empty_text"
    return text, "ok"


def _area_token_to_m2(token: str) -> float:
    value = (token or "").strip()
    if not value:
        return 0.0
    value = value.replace(".", "").replace(",", ".")
    try:
        parsed = float(value)
    except ValueError:
        return 0.0
    return parsed if parsed > 0 else 0.0


def _extract_private_area_m2_from_pdf_text(text: str) -> float:
    if not text:
        return 0.0
    normalized = _searchable_text(text)
    match = re.search(
        r"area\s+(?:real\s+)?privativa\s+(?:de\s+)?([0-9]+(?:[.,][0-9]+)?)\s*m",
        normalized,
        flags=re.I,
    )
    if match:
        return _area_token_to_m2(match.group(1))
    match = re.search(
        r"area\s+util(?:\s+ou\s+privativa)?\s+(?:de\s+)?([0-9]+(?:[.,][0-9]+)?)\s*m",
        normalized,
        flags=re.I,
    )
    if match:
        return _area_token_to_m2(match.group(1))
    return 0.0


def _enrich_mega_extracted_with_pdf_signals(*, extracted: dict[str, Any], client: httpx.Client) -> None:
    attachments = extracted.get("attachments") if isinstance(extracted.get("attachments"), dict) else {}
    edital_url = str(attachments.get("edital") or "").strip()
    matricula_url = str(attachments.get("matricula") or "").strip()
    laudo_url = str(attachments.get("laudo") or "").strip()

    evidence: dict[str, Any] = {}
    texts: dict[str, str] = {}
    for kind, url in (("edital", edital_url), ("matricula", matricula_url), ("laudo", laudo_url)):
        if not url:
            continue
        max_pages = 20 if kind == "edital" else 8
        text, status = _extract_pdf_text(url=url, client=client, max_pages=max_pages)
        if not text and status.startswith("http_error"):
            continue
        texts[kind] = text
        evidence[kind] = {
            "url": url,
            "text_status": status,
            "text_excerpt": text[:1600],
        }

    if evidence:
        extracted["pdf_evidence"] = evidence

    edital_text = texts.get("edital") or texts.get("laudo") or ""
    if not edital_text:
        return

    focused = _focus_pdf_text_for_extracted_location(raw=edital_text, extracted=extracted)
    focused_or_all = focused or edital_text

    appraisal_pdf = _extract_appraisal_value_from_pdf_text(edital_text)
    if appraisal_pdf > 0:
        auction = extracted.get("auction") if isinstance(extracted.get("auction"), dict) else {}
        auction_dict = dict(auction)
        current_appraisal = float(auction_dict.get("appraisal_value") or 0.0)
        if current_appraisal <= 0 or appraisal_pdf > current_appraisal * 1.01:
            auction_dict["appraisal_value"] = round(appraisal_pdf, 2)
            extracted["auction"] = auction_dict

    if "occupancy_status" not in extracted:
        laudo_text = texts.get("laudo") or ""
        if laudo_text:
            status = _extract_occupancy_status_from_signals_text(laudo_text)
            if status:
                extracted["occupancy_status"] = status

    if "occupancy_status" not in extracted:
        status = _extract_occupancy_status_from_signals_text(focused_or_all)
        if status:
            extracted["occupancy_status"] = status

    private_area_pdf = _extract_private_area_m2_from_pdf_text(focused_or_all)
    if private_area_pdf > 0:
        current_private = float(extracted.get("area_private_m2") or 0.0)
        current_total = float(extracted.get("area_total_m2") or 0.0)
        current_basis = str(extracted.get("area_basis") or "").strip().lower()
        should_override = (
            current_private <= 0
            or current_basis in {"title", "url", "url_overrode_html", "url_overrode_noisy_html"}
            or (current_total > 0 and abs(current_total - private_area_pdf) <= max(0.5, current_total * 0.02))
            or private_area_pdf > current_private * 1.02
        )
        if should_override:
            extracted["area_private_m2"] = round(private_area_pdf, 2)
            if current_total <= 0:
                extracted["area_total_m2"] = round(private_area_pdf, 2)
            extracted["area_basis"] = "pdf_privativa"

    debts = extracted.get("debts")
    debts_dict = debts if isinstance(debts, dict) else {}

    condo = _first_money_after(
        r"d[eé]bitos?\s+(?:de\s+)?condom[ií]nio|d[eé]bito\s+(?:de\s+)?condom[ií]nio",
        edital_text,
    )
    iptu = _first_money_after(
        r"d[eé]bitos?\s+(?:de\s+)?iptu|d[eé]bito\s+(?:de\s+)?iptu|\biptu\s*[:=]",
        edital_text,
    )
    active_debt = _first_money_after(r"d[ií]vida\s+ativa|divida\s+ativa", edital_text)
    tributary = _first_money_after(r"d[eé]bitos?\s+tribut[aá]rios|d[eé]bito\s+tribut[aá]rio", edital_text)

    searchable = _searchable_text(edital_text)
    condo = _first_money_after(r"debitos?\s+de\s+condominio|debito\s+de\s+condominio|condominio\s*[:=]", searchable) or condo
    iptu = _first_money_after(r"debitos?\s+de\s+iptu|debito\s+de\s+iptu|\biptu\s*[:=]", searchable) or iptu
    active_debt = _first_money_after(r"divida\s+ativa", searchable) or active_debt
    tributary = _first_money_after(r"debitos?\s+tributarios|debito\s+tributario", searchable) or tributary

    if appraisal_pdf > 0 and iptu > 0 and abs(iptu - appraisal_pdf) <= max(1.0, appraisal_pdf * 0.012):
        iptu = 0.0

    if re.search(r"nao\s+ha\s+debitos?\s+(?:de\s+)?iptu", searchable):
        iptu = 0.0
        debts_dict["iptu_confirmed_clear"] = True

    if re.search(r"nao\s+ha\s+debitos?\s+inscritos?\s+na\s+divida\s+ativa", searchable):
        active_debt = 0.0
        debts_dict["active_debt_confirmed_clear"] = True

    if condo > 0:
        debts_dict["condo_amount"] = round(condo, 2)
    if iptu > 0:
        debts_dict["iptu_amount"] = round(iptu, 2)
    if active_debt > 0:
        debts_dict["active_debt_amount"] = round(active_debt, 2)
    if tributary > 0:
        debts_dict["tributary_amount"] = round(tributary, 2)

    if debts_dict:
        extracted["debts"] = debts_dict


def _extract_mega_listing_urls(index_html: str) -> list[str]:
    urls: list[str] = []
    patterns = (
        r'href="(?P<href>/imoveis/[^"]+-(?:j|x)\d+[^"]*)"',
        r'href="(?P<href>https?://(?:www\.)?megaleiloes\.com\.br/imoveis/[^"]+-(?:j|x)\d+[^"]*)"',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, index_html, flags=re.I):
            href = match.group("href").strip()
            href = href.split("?", 1)[0]
            url = urljoin(MEGA_BASE, href)
            if url not in urls:
                urls.append(url)
    return urls


def _parse_datetime_utc(raw: str) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _used_source_last_seen(limit_reports: int = 80) -> dict[str, datetime]:
    last_seen: dict[str, datetime] = {}
    if not REPORTS_DIR.exists():
        return last_seen
    reports = sorted(REPORTS_DIR.glob("radar_imobiliario_maturacao_*.json"), reverse=True)[:limit_reports]
    for path in reports:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        generated_at = _parse_datetime_utc(str(payload.get("generated_at") or ""))
        if not generated_at:
            try:
                generated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            except Exception:
                continue
        for cand in payload.get("candidates") or []:
            if not isinstance(cand, dict):
                continue
            url = str(cand.get("source_url") or "").strip()
            if not url:
                continue
            normalized = url.rstrip("/")
            for key in (normalized, normalized + "/"):
                prev = last_seen.get(key)
                if prev is None or generated_at > prev:
                    last_seen[key] = generated_at
    return last_seen


def _extract_jsonld_objects(html: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for match in re.finditer(
        r'<script[^>]+type="application/ld\+json"[^>]*>(?P<body>.*?)</script>',
        html,
        flags=re.I | re.S,
    ):
        body = match.group("body").strip()
        if not body:
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            objects.append(payload)
        elif isinstance(payload, list):
            objects.extend(item for item in payload if isinstance(item, dict))
    return objects


def _find_mega_attachments(html: str) -> dict[str, str]:
    attachments: dict[str, str] = {}
    for kind in ("edital", "matricula", "laudo"):
        pattern = (
            rf"https?://cdn1\.megaleiloes\.com\.br/(?:batches|documents|auctions)/\d+/"
            rf"megaleiloes_{kind}_[^\"']+\.pdf"
        )
        for match in re.finditer(pattern, html, flags=re.I):
            url = match.group(0).strip()
            if url:
                attachments[kind] = url
                break
    return attachments


def _find_location_from_jsonld(objects: list[dict[str, Any]]) -> tuple[str, str, str]:
    street = ""
    neighborhood = ""
    city = ""
    for obj in objects:
        address = obj.get("address")
        if not isinstance(address, dict):
            continue
        street = str(address.get("streetAddress") or "").strip()
        city = str(address.get("addressLocality") or "").strip()
        neighborhood = str(address.get("addressRegion") or "").strip()
        if street or city:
            break
    return _repair_mojibake_text(street), _repair_mojibake_text(neighborhood), _repair_mojibake_text(city)


def _find_location_from_html(html: str) -> tuple[str, str, str]:
    """
    Fallback for Mega listing pages when JSON-LD is incomplete.

    Example value:
      "Rua Ministro Gabriel de Rezende Passos, 555, Moema, São Paulo, SP"
    """
    if not html:
        return "", "", ""
    m = re.search(
        r'<div class="locality item">.*?<div class="header">Localiza[^<]*</div>.*?<div class="value">(?P<value>[^<]+)</div>',
        html,
        flags=re.I | re.S,
    )
    if not m:
        return "", "", ""
    raw = re.sub(r"\s+", " ", m.group("value") or "").strip()
    raw = _repair_mojibake_text(raw)
    if not raw:
        return "", "", ""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    street = parts[0] if parts else ""
    neighborhood = parts[2] if len(parts) >= 3 else ""
    city = parts[3] if len(parts) >= 4 else ""
    return street, neighborhood, city


def _find_mega_area(html: str) -> tuple[float, float, str]:
    compact = re.sub(r"\s+", " ", html)
    private = 0.0
    total = 0.0
    private_match = re.search(
        r"[áa]rea\s+privativa[^0-9]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*m",
        compact,
        flags=re.I,
    )
    if private_match:
        private = float(private_match.group(1).replace(",", "."))
    total_match = re.search(
        r"[áa]rea\s+total[^0-9]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*m",
        compact,
        flags=re.I,
    )
    if total_match:
        total = float(total_match.group(1).replace(",", "."))
    if private > 0:
        return private, max(total, private), "privativa"
    if total > 0:
        return total, total, "total"
    return 0.0, 0.0, ""


def _extract_mega_og_title(html: str) -> str:
    match = re.search(r'property="og:title"[^>]+content="(?P<title>[^"]+)"', html, flags=re.I)
    if match:
        return match.group("title").strip()
    match = re.search(r"<title>(?P<title>.*?)</title>", html, flags=re.I | re.S)
    return (match.group("title") if match else "").strip()


def _find_mega_area_from_title(title: str) -> tuple[float, float, str]:
    raw = (title or "").strip()
    if not raw:
        return 0.0, 0.0, ""
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*m(?:2|²|�)", raw, flags=re.I)
    if not m:
        return 0.0, 0.0, ""
    try:
        area = float(m.group(1).replace(",", "."))
    except ValueError:
        return 0.0, 0.0, ""
    normalized = _searchable_text(raw)
    if "area privativa" in normalized:
        return area, area, "title_privativa"
    if "area total" in normalized:
        return 0.0, area, "title_total"
    return 0.0, area, "title"


def _find_mega_area_v2(html: str) -> tuple[float, float, str]:
    compact = re.sub(r"\s+", " ", html)
    title = _extract_mega_og_title(compact)
    title_private, title_total, title_basis = _find_mega_area_from_title(title)

    private = 0.0
    total = 0.0
    private_match = re.search(
        r"[Ã¡a]rea\s+privativa[^0-9]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*m",
        compact,
        flags=re.I,
    )
    if private_match:
        private = float(private_match.group(1).replace(",", "."))
    total_match = re.search(
        r"[Ã¡a]rea\s+total[^0-9]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*m",
        compact,
        flags=re.I,
    )
    if total_match:
        total = float(total_match.group(1).replace(",", "."))

    reference = title_total or title_private
    if reference and (private or total):
        candidates = [v for v in (private, total) if v > 0]
        if candidates and max(candidates) > reference * 1.35:
            if title_private > 0:
                return title_private, title_private, title_basis
            if title_total > 0:
                return 0.0, title_total, title_basis

    if private > 0:
        return private, max(total, private), "privativa"
    if total > 0:
        return total, total, "total"
    if title_private > 0:
        return title_private, title_private, title_basis
    if title_total > 0:
        return 0.0, title_total, title_basis
    return 0.0, 0.0, ""


def _find_mega_minimum_bid(html: str) -> float:
    patterns = (
        r"lance\s+m.{0,6}nimo[^0-9]{0,60}r\$\s*([0-9\.,]+)",
        r"valor\s+m.{0,6}nimo[^0-9]{0,60}r\$\s*([0-9\.,]+)",
    )
    for pattern in patterns:
        for m in re.finditer(pattern, html, flags=re.I):
            value = _money_to_float(m.group(1))
            if value >= 50_000:
                return value

    # Some Mega pages show prices only inside the primary "card instance" blocks
    # (e.g., 1ª/2ª praça) without an explicit "lance mínimo" label. In those cases,
    # the first two values usually correspond to the current lot.
    card_values: list[float] = []
    for m in re.finditer(r"card-instance-value[^R]{0,140}R\$\s*([0-9\.,]+)", html, flags=re.I):
        value = _money_to_float(m.group(1))
        if value > 0:
            card_values.append(value)
        if len(card_values) >= 3:
            break
    card_values = [v for v in card_values if v >= 50_000]
    if card_values:
        return min(card_values)

    values = [_money_to_float(m.group(1)) for m in re.finditer(r"R\$\s*([0-9\.,]+)", html)]
    values = [v for v in values if v >= 50_000]
    return min(values) if values else 0.0


def _find_mega_appraisal(html: str) -> float:
    m = re.search(r"Avalia(?:ç|c)[aã]o[^R]{0,80}R\$\s*([0-9\.,]+)", html, flags=re.I)
    return _money_to_float(m.group(1)) if m else 0.0


def _extract_mega_code(url: str) -> str:
    m = re.search(r"[-/](?P<code>[jx]\d{4,})", url, flags=re.I)
    return str(m.group("code")).upper() if m else ""


def _mega_city_slug_from_url(url: str) -> str:
    url_lower = (url or "").lower()
    if "/sao-paulo/" in url_lower:
        return "sao-paulo"
    if "/campinas/" in url_lower:
        return "campinas"
    return ""


def _mega_neighborhood_from_url(url: str) -> str:
    slug = str(url or "").rstrip("/").split("/")[-1]
    city_slug = _mega_city_slug_from_url(url)
    if not city_slug or not slug:
        return ""
    m = re.search(rf"-(?P<hood>[a-z0-9-]+)-{re.escape(city_slug)}-sp-[jx]\d+$", slug, flags=re.I)
    if not m:
        return ""
    hood_slug = m.group("hood").strip("-").lower()
    # Drop descriptive prefixes like "apartamento-76-m2-02-vagas-" and keep the neighborhood tail.
    for token in ("-vagas-", "-vaga-"):
        if token in hood_slug:
            hood_slug = hood_slug.split(token, 1)[-1]
    hood_slug = re.sub(
        r"^(?:direitos-sobre-)?(?:apartamento|casa|studio|cobertura|kitnet|flat)-",
        "",
        hood_slug,
    )
    hood_slug = re.sub(r"^\d+(?:[.,]\d+)?-m2-", "", hood_slug)
    hood_slug = re.sub(r"^(?:area-(?:total|privativa|construida))-", "", hood_slug)
    hood_slug = re.sub(r"^(?:e-)?\d{1,2}-deposito-", "", hood_slug)
    hood_slug = re.sub(r"^(?:e-)?\d{1,2}-dep[oó]sito-", "", hood_slug)
    hood_slug = re.sub(r"^(?:e-)?box-(?:duplo|simples)-", "", hood_slug)
    hood_slug = hood_slug.strip("-")
    hood = hood_slug.replace("-", " ").strip()
    return hood.title()


def _mega_property_type_from_url(url: str) -> str:
    url_lower = (url or "").lower()
    if "/imoveis/casas/" in url_lower:
        return "Casa"
    if "/imoveis/imoveis-comerciais/" in url_lower or "/imoveis/galpoes/" in url_lower:
        return "Comercial"
    if "/imoveis/terrenos" in url_lower or "/imoveis/terrenos-e-lotes/" in url_lower:
        return "Lote"
    return "Apartamento"


def _extract_mega_candidate_listing(url: str, client: httpx.Client) -> dict[str, Any]:
    response = _get_with_retries(client, url, retries=3)
    html = _response_text_utf8(response)
    jsonld = _extract_jsonld_objects(html)
    listing_title = _extract_html_title(html)
    street, neighborhood, city_jsonld = _find_location_from_jsonld(jsonld)
    if not (street and neighborhood and city_jsonld):
        street2, neighborhood2, city2 = _find_location_from_html(html)
        street = street or street2
        neighborhood = neighborhood or neighborhood2
        city_jsonld = city_jsonld or city2
    private_area, total_area, basis = _find_mega_area_v2(html)
    url_area_value = 0.0
    url_area = re.search(r"-(?P<area>[0-9]+(?:[.,][0-9]+)?)-m2", url, flags=re.I)
    if url_area:
        url_area_value = float(url_area.group("area").replace(",", "."))
    if url_area_value > 0:
        if private_area <= 0 and total_area <= 0:
            total_area = url_area_value
            private_area = url_area_value
            basis = "url"
        elif total_area > 0 and url_area_value > total_area * 1.35:
            # Some pages expose a smaller "area" snippet (e.g., fração ideal) while the URL
            # encodes the intended total/privative area. Prefer the URL when HTML looks inconsistent.
            total_area = url_area_value
            private_area = url_area_value
            basis = "url_overrode_html"
        elif "area-total" in (url or "").lower() and private_area > url_area_value * 1.35:
            total_area = url_area_value
            private_area = url_area_value
            basis = "url_overrode_noisy_html"
    minimum_bid = _find_mega_minimum_bid(html)
    appraisal = _find_mega_appraisal(html)
    attachments = _find_mega_attachments(html)
    process_number = ""
    proc = re.search(r"([0-9]{6,7}-[0-9]{2}\\.[0-9]{4}\\.[0-9]\\.[0-9]{2}\\.[0-9]{4})", html)
    if proc:
        process_number = proc.group(1)
    if not neighborhood:
        neighborhood = _mega_neighborhood_from_url(url)
    return {
        "final_url": str(response.url),
        "http_status": int(response.status_code or 0),
        "listing_title": listing_title,
        "auction_code": _extract_mega_code(url),
        "process_number": process_number,
        "location": {
            "street": street,
            "neighborhood": neighborhood,
            "city": city_jsonld,
            "raw": " ".join(part for part in (street, neighborhood, city_jsonld) if part),
        },
        "area_private_m2": round(private_area, 2) if private_area > 0 else 0.0,
        "area_total_m2": round(total_area, 2) if total_area > 0 else 0.0,
        "area_basis": basis,
        "attachments": attachments,
        "auction": {"minimum_bid": round(minimum_bid, 2), "appraisal_value": round(appraisal, 2)},
        "debts": {
            "condo_amount": 0.0,
            "iptu_amount": 0.0,
            "active_debt_amount": 0.0,
            "tributary_amount": 0.0,
        },
    }


@dataclass(frozen=True)
class Candidate:
    id: str
    city: str
    title: str
    source_url: str
    extracted: dict[str, Any]
    raw_comparables: list[dict[str, Any]]
    analysis: dict[str, Any]
    decision: str


def _used_source_urls(limit_reports: int = 40) -> set[str]:
    used: set[str] = set()
    if not REPORTS_DIR.exists():
        return used
    reports = sorted(REPORTS_DIR.glob("radar_imobiliario_maturacao_*.json"), reverse=True)[:limit_reports]
    for path in reports:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for cand in payload.get("candidates") or []:
            if not isinstance(cand, dict):
                continue
            url = str(cand.get("source_url") or "").strip()
            if not url:
                continue
            used.add(url.rstrip("/"))
            used.add(url.rstrip("/") + "/")
    return used


def _discover_one_mega_candidate(city: str, used_urls: set[str], client: httpx.Client) -> tuple[str, dict[str, Any]] | None:
    reuse_cooldown_h = int(str(os.getenv("RADAR_MATURATION_REUSE_COOLDOWN_HOURS") or "12").strip() or "12")
    reuse_after_s = max(0, reuse_cooldown_h) * 3600
    last_seen = _used_source_last_seen()
    index_urls = MEGA_INDEXES_BY_CITY.get(city) or []
    for index_url in index_urls:
        urls: list[str] = []
        seen: set[str] = set()
        base = index_url.rstrip("/")
        max_pages = 8 if city == "Campinas" else 5
        for page in range(1, max_pages + 1):
            page_url = base if page == 1 else f"{base}?pagina={page}"
            try:
                index_html = _response_text_utf8(_get_with_retries(client, page_url, retries=3))
            except Exception:
                continue
            page_urls = _extract_mega_listing_urls(index_html)
            new_count = 0
            for item in page_urls:
                if item in seen:
                    continue
                seen.add(item)
                urls.append(item)
                new_count += 1
            if page > 1 and new_count == 0:
                break

        reuse_pool: list[tuple[datetime, str]] = []
        cooldown_pool: list[tuple[datetime, str]] = []
        for url in urls[:90]:
            normalized = url.rstrip("/")
            if normalized in used_urls or (normalized + "/") in used_urls:
                seen_at = last_seen.get(normalized) or last_seen.get(normalized + "/")
                if seen_at:
                    age_s = (datetime.now(UTC) - seen_at).total_seconds()
                    if age_s >= reuse_after_s:
                        reuse_pool.append((seen_at, url))
                    else:
                        cooldown_pool.append((seen_at, url))
                continue
            validation = validate_real_estate_source_url(url, fetcher=getattr(client, "fetcher", None))
            if validation.status != "valid":
                continue
            extracted = _extract_mega_candidate_listing(url, client)
            extracted["source_validation"] = validation.as_payload()
            min_bid = float((extracted.get("auction") or {}).get("minimum_bid") or 0.0)
            if min_bid <= 0:
                continue
            return url, extracted

        if reuse_pool:
            reuse_pool.sort(key=lambda item: item[0])
            seen_at, url = reuse_pool[0]
            validation = validate_real_estate_source_url(url, fetcher=getattr(client, "fetcher", None))
            if validation.status != "valid":
                continue
            extracted = _extract_mega_candidate_listing(url, client)
            extracted["source_validation"] = validation.as_payload()
            extracted["radar_maturation_reused"] = True
            extracted["radar_maturation_last_seen_at"] = seen_at.replace(microsecond=0).isoformat()
            min_bid = float((extracted.get("auction") or {}).get("minimum_bid") or 0.0)
            if min_bid <= 0:
                continue
            return url, extracted

        if cooldown_pool:
            cooldown_pool.sort(key=lambda item: item[0])
            seen_at, url = cooldown_pool[0]
            validation = validate_real_estate_source_url(url, fetcher=getattr(client, "fetcher", None))
            if validation.status != "valid":
                continue
            extracted = _extract_mega_candidate_listing(url, client)
            extracted["source_validation"] = validation.as_payload()
            extracted["radar_maturation_reused"] = True
            extracted["radar_maturation_reused_force"] = True
            extracted["radar_maturation_reuse_reason"] = "cooldown_force"
            extracted["radar_maturation_last_seen_at"] = seen_at.replace(microsecond=0).isoformat()
            min_bid = float((extracted.get("auction") or {}).get("minimum_bid") or 0.0)
            if min_bid <= 0:
                continue
            return url, extracted
    return None


def _parse_chaves_price_area_from_url(url: str) -> tuple[float, float]:
    # Example: ...-68m2-RS2732000/id-...
    area = 0.0
    price = 0.0
    m_area = re.search(r"-([0-9]+(?:[.,][0-9]+)?)m2-", url, flags=re.I)
    if m_area:
        area = float(m_area.group(1).replace(",", "."))
    m_price = re.search(r"-RS([0-9]{4,})", url, flags=re.I)
    if m_price:
        try:
            price = float(m_price.group(1))
        except ValueError:
            price = 0.0
    return price, area


def _chaves_neighborhood_from_url(url: str, *, city: str) -> str:
    url_lower = (url or "").lower()
    if city.lower().startswith("sao"):
        marker = "-sp-sao-paulo-"
    else:
        marker = "-sp-campinas-"
    if marker not in url_lower:
        return ""
    tail = url_lower.split(marker, 1)[1]
    # Tail example: "centro-44m2-rs593600/id-..."
    tail = tail.split("/id-", 1)[0]
    m = re.search(r"^(?P<hood>[a-z0-9-]+?)-[0-9]", tail)
    if not m:
        return ""
    hood = m.group("hood").replace("-", " ").strip()
    return hood.title()


def _discover_one_chaves_candidate(
    *,
    city: str,
    used_urls: set[str],
    client: httpx.Client,
) -> tuple[str, dict[str, Any]] | None:
    index_url = CHAVES_INDEX_BY_CITY.get(city)
    if not index_url:
        return None
    try:
        html = _get_with_retries(client, index_url, retries=3).text
    except Exception:
        return None
    urls: list[str] = []
    for match in re.finditer(r'href="(?P<href>/imovel/[^"]+/id-[0-9]+/?)"', html, flags=re.I):
        full = urljoin(CHAVES_BASE, match.group("href"))
        full = full.split("?", 1)[0]
        if full not in urls:
            urls.append(full)
    for url in urls[:80]:
        normalized = url.rstrip("/")
        if normalized in used_urls or (normalized + "/") in used_urls:
            continue
        validation = validate_real_estate_source_url(url, fetcher=getattr(client, "fetcher", None))
        if validation.status != "valid":
            continue
        extracted = _extract_chaves_candidate_listing(url, city=city)
        extracted["source_validation"] = validation.as_payload()
        asking_price = float((extracted.get("auction") or {}).get("minimum_bid") or 0.0)
        private_area = float(extracted.get("area_private_m2") or 0.0)
        if asking_price <= 0 or private_area <= 0:
            continue
        return url, extracted
    return None


def _extract_chaves_candidate_listing(url: str, *, city: str) -> dict[str, Any]:
    price, area = _parse_chaves_price_area_from_url(url)
    neighborhood = _chaves_neighborhood_from_url(url, city=city)
    return {
        "final_url": url,
        "http_status": 200,
        "auction_code": "",
        "process_number": "",
        "location": {
            "street": "",
            "neighborhood": neighborhood,
            "city": city,
            "raw": " ".join(part for part in (neighborhood, city) if part),
        },
        "area_private_m2": round(area, 2) if area > 0 else 0.0,
        "area_total_m2": round(area, 2) if area > 0 else 0.0,
        "area_basis": "url",
        "attachments": {},
        "auction": {"minimum_bid": round(price, 2), "appraisal_value": 0.0},
        "debts": {
            "condo_amount": 0.0,
            "iptu_amount": 0.0,
            "active_debt_amount": 0.0,
            "tributary_amount": 0.0,
        },
    }


def _discover_chaves_sale_comparables(
    *,
    city: str,
    neighborhood: str,
    property_type: str,
    target_area_m2: float,
    exclude_url: str,
    desired: int,
    client: httpx.Client,
) -> list[dict[str, Any]]:
    city_slug = "sp-sao-paulo" if city.lower().startswith("sao") else "sp-campinas"
    neighborhood_slug = _slug(neighborhood) or "centro"
    kind = _guess_chaves_kind(property_type)
    if kind == "commercial":
        category = "imoveis-comerciais-a-venda"
    elif property_type.lower().startswith("casa"):
        category = "casas-a-venda"
    else:
        category = "apartamentos-a-venda"

    def _collect_listing_urls(url: str) -> list[str]:
        try:
            html = _response_text_utf8(_get_with_retries(client, url, retries=3))
        except Exception:
            return []
        found: list[str] = []
        for match in re.finditer(r'href="(?P<href>/imovel/[^"]+/id-[0-9]+/?)"', html, flags=re.I):
            full = urljoin(CHAVES_BASE, match.group("href")).split("?", 1)[0]
            if full not in found:
                found.append(full)
        return found

    urls = _collect_listing_urls(f"{CHAVES_BASE}/{category}/{city_slug}/{neighborhood_slug}/")
    if not urls and neighborhood:
        # Neighborhood slug may not exist; fallback to city-wide search by query hint.
        query = neighborhood.replace(" ", "+")
        urls = _collect_listing_urls(f"{CHAVES_BASE}/{category}/{city_slug}/?q={query}")

    exclude_norm = (exclude_url or "").rstrip("/")

    target_norm = _slug(neighborhood)
    candidates: list[tuple[bool, float, float, str, str]] = []
    for url in urls[: max(80, desired * 30)]:
        if not url:
            continue
        if url.rstrip("/") == exclude_norm:
            continue
        price, area = _parse_chaves_price_area_from_url(url)
        if price <= 0 or area <= 0:
            continue
        found_neighborhood = _chaves_neighborhood_from_url(url, city=city)
        found_norm = _slug(found_neighborhood)
        same_neighborhood = bool(target_norm and found_norm and target_norm == found_norm)
        candidates.append((same_neighborhood, area, price, url, found_neighborhood))

    if target_area_m2 > 0:
        tight = [c for c in candidates if target_area_m2 * 0.6 <= c[1] <= target_area_m2 * 1.6]
        if len(tight) >= desired:
            candidates = tight
        else:
            wide = [c for c in candidates if target_area_m2 * 0.45 <= c[1] <= target_area_m2 * 2.2]
            candidates = wide or candidates

    candidates.sort(
        key=lambda item: (
            not item[0],
            abs(item[1] - target_area_m2) if target_area_m2 > 0 else item[1],
        )
    )
    comparables: list[dict[str, Any]] = []
    for same_neighborhood, area, price, url, found_neighborhood in candidates[:desired]:
        comparables.append(
            {
                "source": "ChavesNaMao",
                "source_url": url,
                "price": round(price, 2),
                "area_m2": round(area, 2),
                "neighborhood": found_neighborhood,
                "same_neighborhood": same_neighborhood,
                "evidence_type": "same_neighborhood_listing" if same_neighborhood else "asking_listing",
                "note": f"{city}/{neighborhood}",
            }
        )
    return comparables


def _candidate_payload_from_mega(
    *,
    city: str,
    title: str,
    source_url: str,
    extracted: dict[str, Any],
    sale_comparables: list[dict[str, Any]],
) -> dict[str, Any]:
    property_type = _mega_property_type_from_url(source_url)
    auction = extracted.get("auction") if isinstance(extracted.get("auction"), dict) else {}
    min_bid = float(auction.get("minimum_bid") or 0.0)
    appraisal = float(auction.get("appraisal_value") or 0.0)
    listing_title = str(extracted.get("listing_title") or "").strip()
    location = extracted.get("location") if isinstance(extracted.get("location"), dict) else {}
    neighborhood = str(location.get("neighborhood") or "").strip()
    street = str(location.get("street") or "").strip()
    private_area = float(extracted.get("area_private_m2") or 0.0) or float(extracted.get("area_total_m2") or 0.0)
    attachments = extracted.get("attachments") if isinstance(extracted.get("attachments"), dict) else {}
    debts = extracted.get("debts") if isinstance(extracted.get("debts"), dict) else {}
    source_validation = (
        extracted.get("source_validation") if isinstance(extracted.get("source_validation"), dict) else {}
    )
    occupancy_status = str(extracted.get("occupancy_status") or "").strip() or "desconhecido"
    pdf_evidence = extracted.get("pdf_evidence") if isinstance(extracted.get("pdf_evidence"), dict) else {}
    matricula_evidence = pdf_evidence.get("matricula") if isinstance(pdf_evidence.get("matricula"), dict) else {}
    registration_text_status = (
        str(matricula_evidence.get("text_status") or "").strip().lower() or "unknown"
    )
    edital_excerpt = str((pdf_evidence.get("edital") or {}).get("text_excerpt") or "").strip()
    condo_amount = float(debts.get("condo_amount") or 0.0)
    iptu_amount = float(debts.get("iptu_amount") or 0.0)
    iptu_confirmed_clear = bool(debts.get("iptu_confirmed_clear"))
    known_debts = (
        float(debts.get("condo_amount") or 0.0)
        + float(debts.get("iptu_amount") or 0.0)
        + float(debts.get("active_debt_amount") or 0.0)
        + float(debts.get("tributary_amount") or 0.0)
    )
    return {
        "title": title,
        "origin": "Mega Leiloes",
        "strategy": "Leilao judicial + diligencia",
        "listing_description": listing_title,
        "source_url": source_url,
        "source_validation": source_validation,
        "source_validation_status": str(source_validation.get("status") or "").strip(),
        "source_validation_reason": str(source_validation.get("reason") or "").strip(),
        "source_checked_at": str(source_validation.get("checked_at") or "").strip(),
        "auction_modality": "judicial",
        "asking_price": min_bid,
        "market_value_estimate": appraisal,
        "city": city,
        "neighborhood": neighborhood,
        "street": street,
        "property_type": property_type,
        "private_area_m2": private_area,
        "area_basis": str(extracted.get("area_basis") or ""),
        "area_total_m2": float(extracted.get("area_total_m2") or 0.0),
        "area_private_m2": float(extracted.get("area_private_m2") or 0.0),
        "occupancy_status": occupancy_status,
        "has_edital": bool(attachments.get("edital")),
        "edital_url": str(attachments.get("edital") or ""),
        "has_registration": bool(attachments.get("matricula")),
        "registration_text_status": registration_text_status,
        "condo_debt_known": condo_amount > 0,
        "condo_debt_amount_brl": round(condo_amount, 2),
        "iptu_debt_known": iptu_confirmed_clear or iptu_amount > 0,
        "iptu_debt_amount_brl": round(iptu_amount, 2),
        "known_debt_costs_brl": round(known_debts, 2),
        "auction_description": edital_excerpt,
        "renovation_type": "leve",
        "renovation_budget": 35000.0,
        "carrying_months": 8,
        "monthly_carrying_cost": 3000.0,
        "acquisition_costs": round(min_bid * 0.08, 2) if min_bid > 0 else 0.0,
        "selling_commission_pct": 6.0,
        "cash_needed": 0.0,
        "sale_comparables": sale_comparables,
        "sale_comparables_count": len(sale_comparables),
        "rent_comparables_count": 0,
        "plan_b": "Locacao se revenda atrasar.",
    }


def _candidate_payload_from_chaves(
    *,
    city: str,
    title: str,
    source_url: str,
    extracted: dict[str, Any],
    sale_comparables: list[dict[str, Any]],
) -> dict[str, Any]:
    auction = extracted.get("auction") if isinstance(extracted.get("auction"), dict) else {}
    asking_price = float(auction.get("minimum_bid") or 0.0)
    location = extracted.get("location") if isinstance(extracted.get("location"), dict) else {}
    neighborhood = str(location.get("neighborhood") or "").strip()
    private_area = float(extracted.get("area_private_m2") or 0.0) or float(extracted.get("area_total_m2") or 0.0)
    source_validation = (
        extracted.get("source_validation") if isinstance(extracted.get("source_validation"), dict) else {}
    )
    return {
        "title": title,
        "origin": "ChavesNaMao",
        "strategy": "Compra mercado + comparaveis",
        "source_url": source_url,
        "source_validation": source_validation,
        "source_validation_status": str(source_validation.get("status") or "").strip(),
        "source_validation_reason": str(source_validation.get("reason") or "").strip(),
        "source_checked_at": str(source_validation.get("checked_at") or "").strip(),
        "auction_modality": "mercado",
        "asking_price": asking_price,
        "market_value_estimate": 0.0,
        "city": city,
        "neighborhood": neighborhood,
        "street": "",
        "property_type": "Apartamento",
        "private_area_m2": private_area,
        "area_basis": str(extracted.get("area_basis") or ""),
        "area_total_m2": float(extracted.get("area_total_m2") or 0.0),
        "area_private_m2": float(extracted.get("area_private_m2") or 0.0),
        "occupancy_status": "desconhecido",
        "has_edital": False,
        "has_registration": False,
        "registration_text_status": "unknown",
        "condo_debt_known": False,
        "iptu_debt_known": False,
        "known_debt_costs_brl": 0.0,
        "renovation_type": "leve",
        "renovation_budget": 25000.0,
        "carrying_months": 6,
        "monthly_carrying_cost": 2000.0,
        "acquisition_costs": round(asking_price * 0.05, 2) if asking_price > 0 else 0.0,
        "selling_commission_pct": 6.0,
        "cash_needed": 0.0,
        "sale_comparables": sale_comparables,
        "sale_comparables_count": len(sale_comparables),
        "rent_comparables_count": 0,
        "plan_b": "Locacao se revenda atrasar.",
    }


def _decision_from_analysis(analysis: dict[str, Any]) -> str:
    status = str(analysis.get("suggested_status") or "").strip().lower()
    scenarios = analysis.get("scenarios") if isinstance(analysis.get("scenarios"), dict) else {}
    base = scenarios.get("base") if isinstance(scenarios.get("base"), dict) else {}
    base_roi_pct = float(base.get("roi_pct") or 0.0)
    pending_items = analysis.get("pending_items") if isinstance(analysis.get("pending_items"), list) else []
    has_rights_over = any(
        isinstance(item, dict) and str(item.get("key") or "").strip().lower() == "rights_over_asset"
        for item in pending_items
    )
    if "descart" in status:
        if has_rights_over and base_roi_pct >= 35.0:
            return "travado"
        if "trava" in status or "rever" in status or " ou " in status:
            return "travado"
        return "sai"
    if "continua" in status:
        return "continua"
    return "travado"


def _auto_tests_closeout() -> list[str]:
    args = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/test_real_estate_radar.py",
        "tests/unit/test_real_estate_source_validation.py",
        "-q",
    ]
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=240, check=False)
    except Exception as exc:
        return [f"{' '.join(args)} (error: {type(exc).__name__}: {exc})"]
    summary = ""
    combined = (completed.stdout or "").splitlines() + (completed.stderr or "").splitlines()
    for line in reversed(combined):
        if "passed" in line or "failed" in line or "error" in line:
            summary = line.strip()
            break
    status = "pass" if completed.returncode == 0 else f"FAIL rc={completed.returncode}"
    return [f"{' '.join(args)} -> {status}{('; ' + summary) if summary else ''}"]


def _auto_http_validation_closeout(candidates: list[Candidate]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        url = (raw or "").strip()
        if not url.startswith(("http://", "https://")):
            return
        url = url.rstrip("/")
        if url in seen:
            return
        seen.add(url)
        urls.append(url)

    for cand in candidates:
        _add(cand.source_url)
        attachments = cand.extracted.get("attachments") if isinstance(cand.extracted.get("attachments"), dict) else {}
        for kind in ("edital", "matricula", "laudo"):
            _add(str(attachments.get(kind) or ""))
        evidence = cand.analysis.get("valuation_evidence") if isinstance(cand.analysis.get("valuation_evidence"), dict) else {}
        for comp in evidence.get("selected_comparables") or []:
            if isinstance(comp, dict):
                _add(str(comp.get("source_url") or ""))

    if not urls:
        return []

    ok = 0
    with _http_client(timeout_s=12.0) as client:
        for url in urls[:80]:
            try:
                with client.stream("GET", url) as r:
                    status = int(r.status_code or 0)
                    if 200 <= status < 400:
                        ok += 1
            except Exception:
                continue
    return [f"HTTP: {ok}/{min(len(urls),80)} URLs OK (timeout=12s)"]


def _render_markdown(run_date: str, json_path: Path, candidates: list[Candidate], closeout: dict[str, list[str]]) -> str:
    lines: list[str] = []
    lines.append(f"# Radar Imobiliário — Maturação ({run_date})")
    lines.append("")
    lines.append(f"Fonte do ciclo (JSON completo): `{json_path.as_posix()}`")
    lines.append("")
    lines.append("Escopo: candidatos reais apenas em **São Paulo (capital)** e **Campinas**, com foco em confiabilidade.")
    lines.append("")
    lines.append("## Candidatos avaliados")
    lines.append("")

    for idx, cand in enumerate(candidates, start=1):
        extracted = cand.extracted
        analysis = cand.analysis
        location = extracted.get("location") if isinstance(extracted.get("location"), dict) else {}
        neighborhood = str(location.get("neighborhood") or "").strip() or "bairro a confirmar"
        area = float(extracted.get("area_private_m2") or 0.0) or float(extracted.get("area_total_m2") or 0.0)
        min_bid = float((extracted.get("auction") or {}).get("minimum_bid") or 0.0)
        attachments = extracted.get("attachments") if isinstance(extracted.get("attachments"), dict) else {}
        scenarios = analysis.get("scenarios") if isinstance(analysis.get("scenarios"), dict) else {}
        base = scenarios.get("base") if isinstance(scenarios.get("base"), dict) else {}
        pending = analysis.get("pending_items") if isinstance(analysis.get("pending_items"), list) else []
        pending_labels = [
            f"{item.get('priority')}: {item.get('title')}"
            for item in pending
            if isinstance(item, dict) and str(item.get("title") or "").strip()
        ]
        evidence = analysis.get("valuation_evidence") if isinstance(analysis.get("valuation_evidence"), dict) else {}
        selected = evidence.get("selected_comparables") if isinstance(evidence.get("selected_comparables"), list) else []
        collected = evidence.get("comparables") if isinstance(evidence.get("comparables"), list) else []
        selected_urls = {str(item.get("source_url") or "") for item in selected if isinstance(item, dict)}

        lines.append(f"### {idx}) {cand.city} - {neighborhood} - {cand.title}")
        lines.append("")
        lines.append(f"- ID (app): `{cand.id}`")
        if extracted.get("radar_maturation_reused_force"):
            last_seen_at = str(extracted.get("radar_maturation_last_seen_at") or "").strip()
            lines.append(f"- Reuso (ciclo): `forcado` (last_seen={last_seen_at or 'n/a'})")
        elif extracted.get("radar_maturation_reused"):
            last_seen_at = str(extracted.get("radar_maturation_last_seen_at") or "").strip()
            lines.append(f"- Reuso (ciclo): `sim` (last_seen={last_seen_at or 'n/a'})")
        lines.append(f"- Fonte (imóvel/lote individual): {cand.source_url}")
        if attachments.get("edital"):
            lines.append(f"- Edital (PDF): {attachments.get('edital')}")
        if attachments.get("matricula"):
            lines.append(f"- Matrícula (PDF): {attachments.get('matricula')}")
        if attachments.get("laudo"):
            lines.append(f"- Laudo (PDF): {attachments.get('laudo')}")
        lines.append(f"- Área (na fonte): `~{area:.2f}m²` (basis={extracted.get('area_basis') or 'n/a'})")
        lines.append(f"- Preço: valor mínimo `{_format_brl(min_bid)}`")
        occupancy = str(extracted.get("occupancy_status") or "").strip()
        if occupancy and occupancy != "desconhecido":
            lines.append(f"- Ocupação (na fonte): `{occupancy}`")
        debts = extracted.get("debts") if isinstance(extracted.get("debts"), dict) else {}
        condo_amount = float(debts.get("condo_amount") or 0.0)
        iptu_amount = float(debts.get("iptu_amount") or 0.0)
        active_debt_amount = float(debts.get("active_debt_amount") or 0.0)
        tributary_amount = float(debts.get("tributary_amount") or 0.0)
        if any(v > 0 for v in (condo_amount, iptu_amount, active_debt_amount, tributary_amount)):
            lines.append(
                "- Dívidas (na fonte): condomínio `{}` · IPTU `{}` · dívida ativa `{}` · tributária `{}`".format(
                    _format_brl(condo_amount),
                    _format_brl(iptu_amount),
                    _format_brl(active_debt_amount),
                    _format_brl(tributary_amount),
                )
            )
        pdf_evidence = extracted.get("pdf_evidence") if isinstance(extracted.get("pdf_evidence"), dict) else {}
        if pdf_evidence:
            status_bits: list[str] = []
            for key in ("edital", "matricula", "laudo"):
                entry = pdf_evidence.get(key) if isinstance(pdf_evidence.get(key), dict) else {}
                status = str(entry.get("text_status") or "").strip()
                if status:
                    status_bits.append(f"{key}={status}")
            if status_bits:
                lines.append(f"- PDFs (texto): `{', '.join(status_bits)}`")
        if selected:
            comps = ", ".join(
                f"{c.get('source_url')} ({float(c.get('area_m2') or 0.0):.1f}m² / {_format_brl(float(c.get('price') or 0.0))})"
                for c in selected
                if isinstance(c, dict)
            )
            lines.append(f"- Comparáveis usados (valuation): {comps}")
        if collected and len(collected) > len(selected):
            extra = [c for c in collected if isinstance(c, dict) and str(c.get("source_url") or "") not in selected_urls]
            extra_lines = ", ".join(
                f"{c.get('source_url')} ({float(c.get('area_m2') or 0.0):.1f}m² / {_format_brl(float(c.get('price') or 0.0))})"
                for c in extra[:3]
            )
            if extra_lines:
                lines.append(f"- Comparáveis coletados (não usados no valuation): {extra_lines}")
        if scenarios:
            def _sp(key: str) -> float:
                entry = scenarios.get(key) if isinstance(scenarios.get(key), dict) else {}
                return float(entry.get("sale_price") or 0.0)

            lines.append(
                "- Cenários (saída): conservador `{}` · base `{}` · otimista `{}`".format(
                    _format_brl(_sp("conservative")),
                    _format_brl(_sp("base")),
                    _format_brl(_sp("optimistic")),
                )
            )
        if base:
            roi = float(base.get("roi_pct") or 0.0)
            profit = float(base.get("net_profit") or 0.0)
            lines.append(f"- Financeiro (base): ROI `{roi:.1f}%` · lucro líquido `{_format_brl(profit)}`")
        lines.append(f"- Score/Confiança (app): `{analysis.get('score')}` / `{analysis.get('confidence')}`")
        if pending_labels:
            validation_notes: list[str] = []
            for item in pending[:3]:
                if not isinstance(item, dict):
                    continue
                route = item.get("validation_route") if isinstance(item.get("validation_route"), list) else []
                exit_criteria = str(item.get("validation_exit_criteria") or "").strip()
                first_step = str(route[0] if route else item.get("action") or "").strip()
                if first_step:
                    validation_notes.append(f"Como validar `{item.get('title')}`: {first_step}")
                if exit_criteria:
                    validation_notes.append(f"Criterio de fechamento `{item.get('title')}`: {exit_criteria}")
            for note in validation_notes:
                lines.append(f"  - {note}")
            lines.append("- Pendências (app): " + "; ".join(pending_labels[:10]))
        lines.append(f"- Próxima ação (app): {analysis.get('next_action')}")
        lines.append(f"- Decisão: **{cand.decision}**")
        lines.append("")

    lines.append("## Decisoes")
    lines.append("")
    for cand in candidates:
        base_roi = float(((cand.analysis.get("scenarios") or {}).get("base") or {}).get("roi_pct") or 0.0)
        lines.append(f"- `{cand.id}`: **{cand.decision}** — {cand.analysis.get('next_action')} (ROI base {base_roi:.1f}%)")
    totals = {d: sum(1 for c in candidates if c.decision == d) for d in ("continua", "travado", "sai")}
    lines.append(f"- Totais: continua={totals['continua']}, sai={totals['sai']}, travado={totals['travado']}")
    lines.append("")

    def _section(title: str, key: str) -> None:
        lines.append(f"## {title}")
        lines.append("")
        items = closeout.get(key) or []
        if not items:
            lines.append("- Nenhuma registrada neste ciclo.")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")

    _section("Fragilidades encontradas", "fragilities")
    _section("Correcoes feitas", "fixes")
    _section("Testes executados", "tests")

    lines.append("## Proximos alvos")
    lines.append("")
    for item in closeout.get("next_targets") or DEFAULT_NEXT_TARGETS:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = sys.argv[1:]
    if any(a in {"-h", "--help"} for a in args):
        print(HELP_TEXT)
        return
    if args:
        print(f"Unexpected args: {' '.join(args)}\n\n{HELP_TEXT}", file=sys.stderr)
        raise SystemExit(2)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    used = _used_source_urls()
    run_date = datetime.now().date().isoformat()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    closeout: dict[str, list[str]] = {
        "fragilities": [],
        "fixes": [],
        "tests": [],
        "next_targets": list(DEFAULT_NEXT_TARGETS),
    }

    manual = str(os.getenv("RADAR_MATURATION_CLOSEOUT_JSON") or "").strip()
    if manual:
        try:
            payload = json.loads(manual)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            for key in ("fragilities", "fixes", "tests", "next_targets"):
                if isinstance(payload.get(key), list):
                    closeout[key] = [str(x).strip() for x in payload[key] if str(x).strip()]

    candidates: list[Candidate] = []
    with _http_client(timeout_s=18.0) as client:
        for city in ("Campinas", "Sao Paulo"):
            source_url = ""
            extracted: dict[str, Any] = {}
            origin = "Mega"
            pin_key = (
                "RADAR_MATURATION_PIN_CAMPINAS_URL"
                if city == "Campinas"
                else "RADAR_MATURATION_PIN_SAO_PAULO_URL"
            )
            pinned_url = str(os.getenv(pin_key) or "").strip()
            if pinned_url:
                source_url = pinned_url
                origin = "Mega" if "megaleiloes.com.br" in pinned_url.lower() else "ChavesNaMao"
                validation = validate_real_estate_source_url(source_url, fetcher=getattr(client, "fetcher", None))
                if validation.status != "valid":
                    closeout["fragilities"].append(
                        f"PIN {city}: URL invalida ({validation.status}): {validation.reason}"
                    )
                    source_url = ""
                elif origin == "Mega":
                    extracted = _extract_mega_candidate_listing(source_url, client)
                    extracted["source_validation"] = validation.as_payload()
                else:
                    extracted = _extract_chaves_candidate_listing(source_url, city=city)
                    extracted["source_validation"] = validation.as_payload()
            else:
                found = _discover_one_mega_candidate(city, used, client)
                if found:
                    source_url, extracted = found
                elif city == "Campinas":
                    origin = "ChavesNaMao"
                    found_chaves = _discover_one_chaves_candidate(city=city, used_urls=used, client=client)
                    if found_chaves:
                        source_url, extracted = found_chaves

            if not source_url:
                closeout["fragilities"].append(f"Falha ao descobrir candidato para {city}.")
                continue

            if origin == "Mega":
                _enrich_mega_extracted_with_pdf_signals(extracted=extracted, client=client)

            location = extracted.get("location") if isinstance(extracted.get("location"), dict) else {}
            neighborhood = str(location.get("neighborhood") or "").strip() or "Centro"
            property_type = _mega_property_type_from_url(source_url) if origin == "Mega" else "Apartamento"
            target_area = float(extracted.get("area_private_m2") or 0.0) or float(extracted.get("area_total_m2") or 0.0)
            sale_comps = _discover_chaves_sale_comparables(
                city=city,
                neighborhood=neighborhood,
                property_type=property_type,
                target_area_m2=target_area,
                exclude_url=source_url,
                desired=3,
                client=client,
            )
            code = str(extracted.get("auction_code") or "").strip()
            if origin == "Mega":
                title = f"{city} - Mega Leiloes {code} ({neighborhood})".strip()
                payload = _candidate_payload_from_mega(
                    city=city,
                    title=title,
                    source_url=source_url,
                    extracted=extracted,
                    sale_comparables=sale_comps,
                )
                candidate_id = f"{_slug(city).replace('-', '_')}_{(code or _slug(neighborhood) or 'mega')}"
            else:
                title = f"{city} - ChavesNaMao ({neighborhood})".strip()
                payload = _candidate_payload_from_chaves(
                    city=city,
                    title=title,
                    source_url=source_url,
                    extracted=extracted,
                    sale_comparables=sale_comps,
                )
                candidate_id = f"{_slug(city).replace('-', '_')}_chaves_{_slug(neighborhood) or 'centro'}"

            analysis = build_candidate_analysis(payload)
            decision = _decision_from_analysis(analysis)
            candidates.append(
                Candidate(
                    id=candidate_id,
                    city=city,
                    title=title,
                    source_url=source_url,
                    extracted=extracted,
                    raw_comparables=sale_comps,
                    analysis=analysis,
                    decision=decision,
                )
            )
            used.add(source_url.rstrip("/"))

    closeout["tests"].extend(_auto_tests_closeout())
    closeout["tests"].extend(_auto_http_validation_closeout(candidates))

    json_path = REPORTS_DIR / f"radar_imobiliario_maturacao_{stamp}.json"
    md_path = REPORTS_DIR / f"radar_imobiliario_maturacao_{stamp}.md"

    payload = {
        "generated_at": _now_utc(),
        "run_date": run_date,
        "scope": SCOPE,
        "json_path": str(json_path),
        "candidates": [
            {
                "id": c.id,
                "title": c.title,
                "source_url": c.source_url,
                "city": c.city,
                "extracted": c.extracted,
                "raw_comparables": c.raw_comparables,
                "analysis": c.analysis,
                "decision": c.decision,
            }
            for c in candidates
        ],
        "closeout": closeout,
        "fragilities": closeout.get("fragilities") or [],
        "fixes": closeout.get("fixes") or [],
        "tests": closeout.get("tests") or [],
        "next_targets": closeout.get("next_targets") or [],
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(run_date, json_path, candidates, closeout), encoding="utf-8-sig")

    print(json.dumps({"json": str(json_path), "md": str(md_path), "candidate_count": len(candidates)}))


if __name__ == "__main__":
    main()
