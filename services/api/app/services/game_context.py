from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TypedDict
from urllib.request import Request, urlopen


class GameContextImage(TypedDict):
    url: str
    caption: str
    source_url: str


class GameHistoricalContext(TypedDict):
    reference_date: str
    event_year: int | None
    event_title: str
    event_summary: str
    source_name: str
    source_url: str | None
    images: list[GameContextImage]


class _ContextCandidate(TypedDict):
    year: int | None
    text: str
    source_url: str | None
    image_candidates: list[GameContextImage]
    score: float


_CACHE: dict[str, GameHistoricalContext] = {}


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _safe_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _request_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "AI-Investment-Advisor-MVP/0.1"})
    with urlopen(request, timeout=15) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def _event_score(text: str, has_image: bool, instrument: str | None) -> float:
    lowered = text.lower()
    score = 0.0
    keywords_high = [
        "brasil",
        "brazil",
        "guerra",
        "war",
        "crise",
        "crisis",
        "election",
        "elei",
        "pandem",
        "econom",
        "mercado",
        "market",
        "stock",
        "bolsa",
        "bank",
        "banco",
        "oil",
        "petrole",
        "inflation",
        "infla",
        "tecnolog",
        "internet",
        "ai",
    ]
    for keyword in keywords_high:
        if keyword in lowered:
            score += 2.3
    if has_image:
        score += 2.5
    if len(text) >= 80:
        score += 1.2
    if instrument is not None and instrument.lower()[:4] in lowered:
        score += 1.0
    return score


def _context_images_from_pages(pages: list[object], max_images: int = 3) -> list[GameContextImage]:
    images: list[GameContextImage] = []
    seen: set[str] = set()
    for item in pages:
        page = _safe_dict(item)
        page_title = _safe_str(page.get("title")) or _safe_str(page.get("displaytitle"))
        thumbnail = _safe_dict(page.get("thumbnail"))
        original_image = _safe_dict(page.get("originalimage"))
        content_urls = _safe_dict(page.get("content_urls"))
        desktop_urls = _safe_dict(content_urls.get("desktop"))
        source_url = _safe_str(desktop_urls.get("page")) or None
        image_url = _safe_str(thumbnail.get("source")) or _safe_str(original_image.get("source"))
        if not image_url or image_url in seen:
            continue
        seen.add(image_url)
        images.append(
            {
                "url": image_url,
                "caption": page_title or "Imagem relacionada ao evento",
                "source_url": source_url or "https://wikipedia.org/",
            }
        )
        if len(images) >= max_images:
            break
    return images


def _candidate_from_event(event: dict[str, object], instrument: str | None) -> _ContextCandidate:
    pages = _safe_list(event.get("pages"))
    text = _safe_str(event.get("text"))
    year_value = event.get("year")
    year = int(year_value) if isinstance(year_value, int) else None
    images = _context_images_from_pages(pages)
    source_url = None
    if pages:
        first_page = _safe_dict(pages[0])
        content_urls = _safe_dict(first_page.get("content_urls"))
        desktop_urls = _safe_dict(content_urls.get("desktop"))
        source_url = _safe_str(desktop_urls.get("page")) or None
    return {
        "year": year,
        "text": text,
        "source_url": source_url,
        "image_candidates": images,
        "score": _event_score(text, bool(images), instrument),
    }


def _events_for_day(month: int, day: int, language: str) -> list[_ContextCandidate]:
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/{language}/onthisday/events/{month}/{day}"
    payload = _request_json(url)
    events = _safe_list(payload.get("events"))
    return [_candidate_from_event(_safe_dict(item), None) for item in events]


def context_for_reference_time(
    reference_time: str,
    instrument: str | None = None,
) -> GameHistoricalContext:
    reference_date = _parse_iso_datetime(reference_time).date()
    cache_key = f"{reference_date.isoformat()}::{(instrument or '').upper()}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    candidates: list[_ContextCandidate] = []
    try:
        month = reference_date.month
        day = reference_date.day
        for language in ("pt", "en"):
            for candidate in _events_for_day(month, day, language):
                boosted = candidate.copy()
                boosted["score"] = _event_score(
                    boosted["text"],
                    bool(boosted["image_candidates"]),
                    instrument,
                )
                candidates.append(boosted)
    except Exception:
        candidates = []

    if not candidates:
        fallback: GameHistoricalContext = {
            "reference_date": reference_date.isoformat(),
            "event_year": None,
            "event_title": "Contexto historico indisponivel",
            "event_summary": (
                "Nao foi possivel recuperar evento externo no momento. "
                "A rodada segue com dados de tese e resultado historico local."
            ),
            "source_name": "fallback-local",
            "source_url": None,
            "images": [],
        }
        _CACHE[cache_key] = fallback
        return fallback

    selected = sorted(candidates, key=lambda item: item["score"], reverse=True)[0]
    event_year = selected["year"]
    year_prefix = f"{event_year}: " if event_year is not None else ""
    context: GameHistoricalContext = {
        "reference_date": reference_date.isoformat(),
        "event_year": event_year,
        "event_title": f"{year_prefix}{selected['text']}",
        "event_summary": (
            "Evento historico do dia para contextualizar o ambiente macro "
            "da tese simulada."
        ),
        "source_name": "Wikipedia On This Day",
        "source_url": selected["source_url"],
        "images": selected["image_candidates"][:3],
    }
    _CACHE[cache_key] = context
    return context
