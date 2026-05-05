from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, tzinfo
from email.utils import parsedate_to_datetime
from typing import TypedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from app.models import NewsArticle
from app.schemas import NewsIngestRequest
from app.services.audit import record_audit_event
from app.services.news import ingest_news
from app.services.utils import isoformat
from sqlalchemy import select
from sqlalchemy.orm import Session

GOOGLE_NEWS_SOURCE = "Google News RSS"
DEFAULT_MAX_ARTICLES_PER_INSTRUMENT = 80
DEFAULT_MAX_INSTRUMENTS = 60

INSTRUMENT_QUERY_HINTS = {
    "PETR4": "Petrobras PETR4",
    "VALE3": "Vale VALE3 minerio",
    "ITUB4": "Itau ITUB4 banco",
    "BBDC4": "Bradesco BBDC4 banco",
    "BBAS3": "Banco do Brasil BBAS3",
    "ABEV3": "Ambev ABEV3",
    "WEGE3": "WEG WEGE3",
    "B3SA3": "B3 B3SA3 bolsa",
    "RENT3": "Localiza RENT3",
    "SUZB3": "Suzano SUZB3",
}


class ExternalNewsSyncResult(TypedDict):
    source: str
    start_date: str
    end_date: str
    instruments: list[str]
    fetched: int
    inserted: int
    duplicates_ignored: int
    failed: int
    by_instrument: dict[str, int]
    sample_headlines: list[str]


class _ExternalNewsItem(TypedDict):
    instrument: str
    headline: str
    source_name: str
    source_type: str
    published_at: datetime
    source_url: str | None
    language: str


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _instrument_query(instrument: str) -> str:
    upper = instrument.upper()
    hint = INSTRUMENT_QUERY_HINTS.get(upper, upper)
    return f'"{hint}" OR "{upper}"'


def _google_news_rss_url(
    *,
    query: str,
    start_date: date,
    end_date: date,
    language: str,
) -> str:
    end_plus_one = (end_date + timedelta(days=1)).isoformat()
    base_query = f"{query} after:{start_date.isoformat()} before:{end_plus_one}"
    hl = "pt-BR" if language.lower().startswith("pt") else "en-US"
    gl = "BR" if language.lower().startswith("pt") else "US"
    ceid = "BR:pt-419" if language.lower().startswith("pt") else "US:en"
    params = urlencode({"q": base_query, "hl": hl, "gl": gl, "ceid": ceid})
    return f"https://news.google.com/rss/search?{params}"


def _infer_source_name(title: str, fallback: str) -> str:
    if " - " in title:
        suffix = title.rsplit(" - ", 1)[1].strip()
        if suffix:
            return suffix
    return fallback


def _infer_source_type(source_name: str) -> str:
    lowered = source_name.lower()
    if "cvm" in lowered or "b3" in lowered:
        return "official"
    if "valor" in lowered or "bloomberg" in lowered or "reuters" in lowered:
        return "regulated_media"
    return "financial_media"


def _safe_source_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > 400:
        return None
    return normalized


def _parse_pubdate(value: str, fallback_tz: tzinfo) -> datetime | None:
    if not value.strip():
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=fallback_tz)
    return parsed.astimezone(UTC)


def _fetch_google_news_items(
    *,
    instrument: str,
    start_date: date,
    end_date: date,
    max_items: int,
    language: str,
) -> list[_ExternalNewsItem]:
    url = _google_news_rss_url(
        query=_instrument_query(instrument),
        start_date=start_date,
        end_date=end_date,
        language=language,
    )
    request = Request(url, headers={"User-Agent": "AI-Investment-Advisor-MVP/0.1"})
    with urlopen(request, timeout=25) as response:
        xml_payload = response.read()

    root = ElementTree.fromstring(xml_payload)
    items = root.findall(".//item")
    parsed_items: list[_ExternalNewsItem] = []
    start_dt = datetime.combine(start_date, time.min).replace(tzinfo=UTC)
    end_dt = datetime.combine(end_date, time.max).replace(tzinfo=UTC)
    for raw_item in items:
        title = (raw_item.findtext("title") or "").strip()
        if not title:
            continue
        pub_date = _parse_pubdate(raw_item.findtext("pubDate") or "", UTC)
        if pub_date is None or pub_date < start_dt or pub_date > end_dt:
            continue
        link = (raw_item.findtext("link") or "").strip()
        source_name = _infer_source_name(title, GOOGLE_NEWS_SOURCE)
        parsed_items.append(
            {
                "instrument": instrument.upper(),
                "headline": title,
                "source_name": source_name,
                "source_type": _infer_source_type(source_name),
                "published_at": pub_date,
                "source_url": link or None,
                "language": language,
            }
        )
        if len(parsed_items) >= max_items:
            break
    return parsed_items


def sync_external_news_period(
    db: Session,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
    instruments: list[str],
    max_articles_per_instrument: int = DEFAULT_MAX_ARTICLES_PER_INSTRUMENT,
    language: str = "pt-BR",
) -> ExternalNewsSyncResult:
    if start_date > end_date:
        raise ValueError("start_date nao pode ser maior que end_date.")
    if (end_date - start_date).days > 3660:
        raise ValueError("Faixa de datas limitada a 10 anos por execucao.")
    unique_instruments = list(dict.fromkeys(item.upper() for item in instruments if item.strip()))
    if not unique_instruments:
        raise ValueError("Informe ao menos um instrumento para sincronizacao de noticias.")
    if len(unique_instruments) > DEFAULT_MAX_INSTRUMENTS:
        raise ValueError(
            f"Sincronizacao de noticias limitada a {DEFAULT_MAX_INSTRUMENTS} instrumentos."
        )
    per_instrument_limit = _clamp(max_articles_per_instrument, 1, 500)

    fetched = 0
    inserted = 0
    duplicates_ignored = 0
    failed = 0
    by_instrument = {instrument: 0 for instrument in unique_instruments}
    sample_headlines: list[str] = []

    for instrument in unique_instruments:
        try:
            external_items = _fetch_google_news_items(
                instrument=instrument,
                start_date=start_date,
                end_date=end_date,
                max_items=per_instrument_limit,
                language=language,
            )
        except Exception:
            failed += 1
            continue

        fetched += len(external_items)
        for item in external_items:
            existing = db.scalar(
                select(NewsArticle)
                .where(NewsArticle.instrument == item["instrument"])
                .where(NewsArticle.headline == item["headline"])
                .where(NewsArticle.source_name == item["source_name"])
                .where(NewsArticle.published_at == isoformat(item["published_at"]))
                .order_by(NewsArticle.id.desc())
                .limit(1)
            )
            if existing is not None:
                duplicates_ignored += 1
                continue
            try:
                ingest_news(
                    db,
                    NewsIngestRequest(
                        instrument=item["instrument"],
                        headline=item["headline"],
                        source_name=item["source_name"],
                        source_type=item["source_type"],
                        published_at=item["published_at"],
                        source_url=_safe_source_url(item["source_url"]),
                        language=item["language"],
                    ),
                )
            except Exception:
                failed += 1
                continue

            inserted += 1
            by_instrument[instrument] += 1
            if len(sample_headlines) < 10:
                sample_headlines.append(item["headline"])

    payload: ExternalNewsSyncResult = {
        "source": GOOGLE_NEWS_SOURCE,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "instruments": unique_instruments,
        "fetched": fetched,
        "inserted": inserted,
        "duplicates_ignored": duplicates_ignored,
        "failed": failed,
        "by_instrument": by_instrument,
        "sample_headlines": sample_headlines,
    }
    record_audit_event(
        db,
        "news.external.sync_period_completed",
        dict(payload),
        user_id,
    )
    return payload
