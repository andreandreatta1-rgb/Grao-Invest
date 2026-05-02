from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import cast

import httpx
from app.models import (
    AlertEvent,
    MarketTick,
    Signal,
    WhatsAppNotificationDelivery,
    WhatsAppNotificationSetting,
)
from app.services.asset_classes import asset_class_label, classify_instrument
from app.services.audit import record_audit_event
from app.services.utils import isoformat, to_json, utc_now
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

SHORT_DISCLAIMER = "Conteudo educacional. Nao e recomendacao de investimento."

DEFAULT_CATEGORIES: dict[str, bool] = {
    "thesis.new": True,
    "thesis.update": True,
    "stock.alert": True,
    "daily.digest": True,
}
DEFAULT_THRESHOLDS: dict[str, float] = {
    "thesis_confidence_pct": 55.0,
    "thesis_expected_pct": 0.0,
    "thesis_progress_delta_pct": 20.0,
    "stock_price_move_pct": 3.0,
    "news_magnitude": 0.75,
    "signal_confidence": 0.6,
}
CATEGORY_API_KEYS: dict[str, str] = {
    "thesis.new": "thesis_new",
    "thesis.update": "thesis_update",
    "stock.alert": "stock_alert",
    "daily.digest": "daily_digest",
}
API_CATEGORY_KEYS: dict[str, str] = {value: key for key, value in CATEGORY_API_KEYS.items()}
COMMAND_PAUSE = {"pausar", "parar", "stop", "cancelar"}
COMMAND_RESUME = {"ativar", "retomar", "start", "resume"}
COMMAND_DIGEST = {"resumo", "digest"}
DELIVERY_COOLDOWN_MINUTES = int(os.getenv("WHATSAPP_DELIVERY_COOLDOWN_MINUTES", "5"))


class WhatsAppClientError(RuntimeError):
    pass


class WhatsAppClient:
    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        api_version: str = "v25.0",
        language_code: str = "pt_BR",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.language_code = language_code
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> WhatsAppClient:
        access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
        if not access_token or not phone_number_id:
            raise WhatsAppClientError(
                "WhatsApp nao configurado. Defina WHATSAPP_ACCESS_TOKEN e "
                "WHATSAPP_PHONE_NUMBER_ID."
            )
        return cls(
            access_token=access_token,
            phone_number_id=phone_number_id,
            api_version=os.getenv("WHATSAPP_API_VERSION", "v25.0").strip() or "v25.0",
            language_code=os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "pt_BR").strip()
            or "pt_BR",
            timeout_seconds=float(os.getenv("WHATSAPP_TIMEOUT_SECONDS", "10")),
        )

    def send_template(
        self,
        *,
        to_phone_number: str,
        template_name: str,
        title: str,
        body: str,
    ) -> dict[str, object]:
        url = (
            f"https://graph.facebook.com/{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )
        payload: dict[str, object] = {
            "messaging_product": "whatsapp",
            "to": normalize_phone_number(to_phone_number).removeprefix("+"),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": self.language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": _safe_whatsapp_text(title, 120)},
                            {"type": "text", "text": _safe_whatsapp_text(body, 900)},
                            {"type": "text", "text": SHORT_DISCLAIMER},
                        ],
                    }
                ],
            },
        }
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise WhatsAppClientError(f"Falha HTTP ao enviar WhatsApp: {exc}") from exc

        if response.status_code >= 400:
            raise WhatsAppClientError(
                f"Meta Cloud API retornou {response.status_code}: {response.text[:500]}"
            )
        try:
            parsed = cast(dict[str, object], response.json())
        except ValueError as exc:
            raise WhatsAppClientError("Resposta invalida da Meta Cloud API.") from exc
        return parsed


def normalize_phone_number(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10 or len(digits) > 19 or digits.startswith("0"):
        raise ValueError("Telefone WhatsApp deve estar em formato internacional E.164.")
    return f"+{digits}"


def category_to_api_key(category: str) -> str:
    return CATEGORY_API_KEYS.get(category, category.replace(".", "_"))


def api_key_to_category(key: str) -> str:
    return API_CATEGORY_KEYS.get(key, key.replace("_", "."))


def categories_for_setting(setting: WhatsAppNotificationSetting | None) -> dict[str, bool]:
    categories = DEFAULT_CATEGORIES.copy()
    if setting is None:
        return categories
    for key, value in _load_json_dict(setting.categories_json).items():
        category = api_key_to_category(key)
        if category in DEFAULT_CATEGORIES and isinstance(value, bool):
            categories[category] = value
    return categories


def thresholds_for_setting(setting: WhatsAppNotificationSetting | None) -> dict[str, float]:
    thresholds = DEFAULT_THRESHOLDS.copy()
    if setting is None:
        return thresholds
    for key, value in _load_json_dict(setting.thresholds_json).items():
        if key in DEFAULT_THRESHOLDS and isinstance(value, int | float):
            thresholds[key] = float(value)
    return thresholds


def get_whatsapp_settings_payload(
    db: Session,
    *,
    user_id: int,
    include_deliveries: bool = True,
) -> dict[str, object]:
    setting = _setting_for_user(db, user_id)
    deliveries: list[dict[str, object]] = []
    if include_deliveries:
        rows = list(
            db.scalars(
                select(WhatsAppNotificationDelivery)
                .where(WhatsAppNotificationDelivery.user_id == user_id)
                .order_by(desc(WhatsAppNotificationDelivery.id))
                .limit(12)
            )
        )
        deliveries = [_delivery_to_payload(row) for row in rows]
    return {
        "user_id": user_id,
        "phone_number": setting.phone_number if setting else "",
        "display_name": setting.display_name if setting else None,
        "opt_in": bool(setting.opt_in) if setting else False,
        "paused": bool(setting.paused) if setting else False,
        "categories": _categories_to_api_payload(categories_for_setting(setting)),
        "thresholds": thresholds_for_setting(setting),
        "last_test_at": setting.last_test_at if setting else None,
        "last_command_at": setting.last_command_at if setting else None,
        "recent_deliveries": deliveries,
    }


def upsert_whatsapp_settings(
    db: Session,
    *,
    user_id: int,
    phone_number: str,
    display_name: str | None,
    opt_in: bool,
    categories: dict[str, bool],
    thresholds: dict[str, float],
) -> WhatsAppNotificationSetting:
    normalized_phone = normalize_phone_number(phone_number)
    now = isoformat(utc_now())
    setting = _setting_for_user(db, user_id)
    if setting is None:
        setting = WhatsAppNotificationSetting(
            user_id=user_id,
            phone_number=normalized_phone,
            display_name=display_name,
            opt_in=opt_in,
            paused=not opt_in,
            categories_json="{}",
            thresholds_json="{}",
            created_at=now,
            updated_at=now,
        )
        db.add(setting)
    setting.phone_number = normalized_phone
    setting.display_name = display_name
    setting.opt_in = opt_in
    setting.paused = not opt_in
    setting.categories_json = to_json(
        {
            category_to_api_key(api_key_to_category(key)): bool(value)
            for key, value in categories.items()
            if api_key_to_category(key) in DEFAULT_CATEGORIES
        }
    )
    setting.thresholds_json = to_json(
        {
            key: float(value)
            for key, value in thresholds.items()
            if key in DEFAULT_THRESHOLDS
        }
    )
    setting.updated_at = now
    db.commit()
    db.refresh(setting)
    record_audit_event(
        db,
        "notifications.whatsapp.settings.updated",
        {"phone_number": _mask_phone(setting.phone_number), "opt_in": setting.opt_in},
        user_id,
    )
    return setting


def queue_whatsapp_notification(
    db: Session,
    *,
    user_id: int,
    category: str,
    event_key: str,
    title: str,
    body: str,
    instrument: str | None = None,
    force: bool = False,
    client: WhatsAppClient | None = None,
) -> WhatsAppNotificationDelivery:
    existing = db.scalar(
        select(WhatsAppNotificationDelivery)
        .where(WhatsAppNotificationDelivery.event_key == event_key)
        .limit(1)
    )
    if existing is not None:
        return existing

    setting = _setting_for_user(db, user_id)
    categories = categories_for_setting(setting)
    template_name = _template_for_category(category)
    now = isoformat(utc_now())
    delivery = WhatsAppNotificationDelivery(
        user_id=user_id,
        channel="whatsapp",
        category=category,
        event_key=event_key,
        instrument=instrument.upper() if instrument else None,
        title=_safe_whatsapp_text(title, 180),
        message_body=_safe_whatsapp_text(body, 1200),
        template_name=template_name,
        template_payload="{}",
        status="queued",
        provider_message_id=None,
        failure_reason=None,
        created_at=now,
        sent_at=None,
        updated_at=now,
    )

    skip_reason = _skip_reason(setting, categories, category)
    if skip_reason is None and not force:
        skip_reason = _cooldown_skip_reason(db, user_id, category, instrument)
    if skip_reason is not None:
        delivery.status = "skipped"
        delivery.failure_reason = skip_reason
        db.add(delivery)
        _commit_delivery(db, delivery)
        return delivery

    db.add(delivery)
    _commit_delivery(db, delivery)
    try:
        whatsapp_client = client or WhatsAppClient.from_env()
        result = whatsapp_client.send_template(
            to_phone_number=setting.phone_number if setting else "",
            template_name=template_name,
            title=delivery.title,
            body=delivery.message_body,
        )
    except WhatsAppClientError as exc:
        delivery.status = "failed"
        delivery.failure_reason = str(exc)[:1000]
    else:
        delivery.status = "sent"
        delivery.sent_at = isoformat(utc_now())
        delivery.provider_message_id = _provider_message_id(result)
        delivery.template_payload = to_json(_template_result_summary(result))
    delivery.updated_at = isoformat(utc_now())
    db.commit()
    db.refresh(delivery)
    record_audit_event(
        db,
        "notifications.whatsapp.delivery.updated",
        {
            "delivery_id": delivery.id,
            "category": delivery.category,
            "status": delivery.status,
            "instrument": delivery.instrument,
        },
        user_id,
    )
    return delivery


def send_test_whatsapp_notification(
    db: Session,
    *,
    user_id: int,
    client: WhatsAppClient | None = None,
) -> WhatsAppNotificationDelivery:
    event_key = f"whatsapp.test:{user_id}:{int(utc_now().timestamp())}"
    delivery = queue_whatsapp_notification(
        db,
        user_id=user_id,
        category="stock.alert",
        event_key=event_key,
        title="Teste WhatsApp Grao Invest",
        body="Canal conectado. Voce recebera teses, evolucoes e alertas configurados.",
        instrument=None,
        force=True,
        client=client,
    )
    setting = _setting_for_user(db, user_id)
    if setting is not None:
        setting.last_test_at = isoformat(utc_now())
        setting.updated_at = isoformat(utc_now())
        db.commit()
    return delivery


def notify_alert_events(
    db: Session,
    events: list[AlertEvent],
) -> list[WhatsAppNotificationDelivery]:
    deliveries: list[WhatsAppNotificationDelivery] = []
    for event in events:
        payload = _load_json_dict(event.payload)
        title = _alert_title(event)
        body = _alert_body(event, payload)
        event_key = f"stock.alert:{event.user_id}:alert_event:{event.id}"
        deliveries.append(
            queue_whatsapp_notification(
                db,
                user_id=event.user_id,
                category="stock.alert",
                event_key=event_key,
                title=title,
                body=body,
                instrument=event.instrument,
            )
        )
    return deliveries


def notify_market_price_move(
    db: Session,
    tick: MarketTick,
) -> list[WhatsAppNotificationDelivery]:
    previous = db.scalar(
        select(MarketTick)
        .where(MarketTick.instrument == tick.instrument)
        .where(MarketTick.id < tick.id)
        .order_by(desc(MarketTick.id))
        .limit(1)
    )
    if previous is None or previous.price <= 0:
        return []

    move_pct = ((tick.price - previous.price) / previous.price) * 100
    settings = _eligible_settings(db, "stock.alert")
    deliveries: list[WhatsAppNotificationDelivery] = []
    for setting in settings:
        thresholds = thresholds_for_setting(setting)
        if abs(move_pct) < thresholds["stock_price_move_pct"]:
            continue
        direction = "alta" if move_pct > 0 else "queda"
        deliveries.append(
            queue_whatsapp_notification(
                db,
                user_id=setting.user_id,
                category="stock.alert",
                event_key=f"stock.alert:{setting.user_id}:{tick.instrument}:move:{tick.id}",
                title=f"Movimento relevante em {tick.instrument}",
                body=(
                    f"{tick.instrument} registrou {direction} de {move_pct:.2f}% "
                    f"entre os dois ultimos ticks. Preco atual: R$ {tick.price:.2f}."
                ),
                instrument=tick.instrument,
            )
        )
    return deliveries


def notify_current_thesis_monitor(
    db: Session,
    payload: Mapping[str, object],
) -> list[WhatsAppNotificationDelivery]:
    user_id = _int_value(payload.get("user_id"))
    setting = _setting_for_user(db, user_id)
    if setting is None:
        return []
    categories = categories_for_setting(setting)
    thresholds = thresholds_for_setting(setting)
    theses_raw = payload.get("theses")
    if not isinstance(theses_raw, list):
        return []

    deliveries: list[WhatsAppNotificationDelivery] = []
    for raw in theses_raw:
        if not isinstance(raw, dict):
            continue
        thesis = {str(key): value for key, value in raw.items()}
        instrument = str(thesis.get("instrument") or "").upper()
        thesis_id = str(thesis.get("thesis_id") or "")
        confidence = _float_value(thesis.get("confidence_tese_pct"))
        expected = _float_value(thesis.get("expected_financial_pct"))
        if (
            categories.get("thesis.new", False)
            and confidence >= thresholds["thesis_confidence_pct"]
            and expected >= thresholds["thesis_expected_pct"]
        ):
            deliveries.append(
                queue_whatsapp_notification(
                    db,
                    user_id=user_id,
                    category="thesis.new",
                    event_key=f"thesis.new:{user_id}:{thesis_id}",
                    title=f"Nova tese monitorada: {instrument}",
                    body=_thesis_new_body(thesis),
                    instrument=instrument,
                )
            )

        update_key = _thesis_update_key(user_id, thesis, thresholds)
        if categories.get("thesis.update", False) and update_key:
            deliveries.append(
                queue_whatsapp_notification(
                    db,
                    user_id=user_id,
                    category="thesis.update",
                    event_key=update_key,
                    title=f"Evolucao da tese: {instrument}",
                    body=_thesis_update_body(thesis),
                    instrument=instrument,
                )
            )
    return deliveries


def send_daily_digest(
    db: Session,
    *,
    user_id: int,
    event_suffix: str | None = None,
    force: bool = False,
) -> WhatsAppNotificationDelivery:
    today = utc_now().date().isoformat()
    suffix = event_suffix or today
    window_start = isoformat(utc_now() - timedelta(hours=24))
    recent_alerts = list(
        db.scalars(
            select(AlertEvent)
            .where(AlertEvent.user_id == user_id)
            .where(AlertEvent.created_at >= window_start)
            .order_by(desc(AlertEvent.id))
            .limit(50)
        )
    )
    recent_deliveries = list(
        db.scalars(
            select(WhatsAppNotificationDelivery)
            .where(WhatsAppNotificationDelivery.user_id == user_id)
            .where(WhatsAppNotificationDelivery.created_at >= window_start)
            .order_by(desc(WhatsAppNotificationDelivery.id))
            .limit(50)
        )
    )
    recent_signals = list(
        db.scalars(
            select(Signal)
            .where(Signal.user_id == user_id)
            .where(Signal.availability_time >= window_start)
            .order_by(desc(Signal.id))
            .limit(20)
        )
    )
    instruments = sorted(
        {
            str(instrument)
            for instrument in [
                *(item.instrument for item in recent_alerts),
                *(item.instrument for item in recent_deliveries),
                *(item.instrument for item in recent_signals),
            ]
            if instrument
        }
    )
    thesis_count = sum(
        1
        for item in recent_deliveries
        if item.category in {"thesis.new", "thesis.update"} and item.status == "sent"
    )
    body = (
        f"Resumo 24h: {len(recent_alerts)} alertas, {thesis_count} atualizacoes de "
        f"teses e {len(recent_signals)} sinais. "
        f"Ativos: {', '.join(instruments[:6]) if instruments else 'sem eventos criticos'}."
    )
    return queue_whatsapp_notification(
        db,
        user_id=user_id,
        category="daily.digest",
        event_key=f"daily.digest:{user_id}:{suffix}",
        title="Resumo diario Grao Invest",
        body=body,
        force=force,
    )


def send_daily_digest_for_all(db: Session) -> dict[str, object]:
    settings = _eligible_settings(db, "daily.digest")
    deliveries = [
        send_daily_digest(db, user_id=setting.user_id)
        for setting in settings
    ]
    return {
        "attempted": len(deliveries),
        "sent": sum(1 for item in deliveries if item.status == "sent"),
        "failed": sum(1 for item in deliveries if item.status == "failed"),
        "skipped": sum(1 for item in deliveries if item.status == "skipped"),
    }


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    digest = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)


def process_whatsapp_webhook_payload(db: Session, payload: dict[str, object]) -> dict[str, object]:
    status_count = _process_provider_statuses(db, payload)
    command_results = _process_inbound_messages(db, payload)
    return {
        "status_updates": status_count,
        "commands": command_results,
    }


def process_inbound_command(db: Session, *, from_phone: str, text: str) -> dict[str, object]:
    setting = _setting_for_phone(db, from_phone)
    command = _normalize_command(text)
    if setting is None:
        record_audit_event(
            db,
            "notifications.whatsapp.command.unknown_contact",
            {"from_phone": _mask_phone(from_phone), "command": command},
        )
        return {"action": "unknown_contact", "command": command}

    now = isoformat(utc_now())
    if command in COMMAND_PAUSE:
        setting.opt_in = False
        setting.paused = True
        action = "paused"
    elif command in COMMAND_RESUME:
        setting.opt_in = True
        setting.paused = False
        action = "resumed"
    elif command in COMMAND_DIGEST:
        action = "digest_sent"
        send_daily_digest(
            db,
            user_id=setting.user_id,
            event_suffix=f"command:{int(utc_now().timestamp())}",
            force=True,
        )
    else:
        action = "ignored"

    setting.last_command_at = now
    setting.updated_at = now
    db.commit()
    record_audit_event(
        db,
        "notifications.whatsapp.command.processed",
        {"command": command, "action": action},
        setting.user_id,
    )
    return {"action": action, "command": command, "user_id": setting.user_id}


def update_delivery_status_from_provider(
    db: Session,
    *,
    provider_message_id: str,
    provider_status: str,
    failure_reason: str | None = None,
) -> bool:
    delivery = db.scalar(
        select(WhatsAppNotificationDelivery)
        .where(WhatsAppNotificationDelivery.provider_message_id == provider_message_id)
        .limit(1)
    )
    if delivery is None:
        return False
    delivery.status = "failed" if provider_status == "failed" else provider_status
    if failure_reason:
        delivery.failure_reason = failure_reason
    delivery.updated_at = isoformat(utc_now())
    db.commit()
    return True


def _setting_for_user(
    db: Session,
    user_id: int,
) -> WhatsAppNotificationSetting | None:
    return db.scalar(
        select(WhatsAppNotificationSetting)
        .where(WhatsAppNotificationSetting.user_id == user_id)
        .limit(1)
    )


def _eligible_settings(db: Session, category: str) -> list[WhatsAppNotificationSetting]:
    settings = list(
        db.scalars(
            select(WhatsAppNotificationSetting)
            .where(WhatsAppNotificationSetting.opt_in.is_(True))
            .where(WhatsAppNotificationSetting.paused.is_(False))
            .order_by(WhatsAppNotificationSetting.user_id.asc())
        )
    )
    return [
        setting
        for setting in settings
        if categories_for_setting(setting).get(category, False)
        and bool(setting.phone_number)
    ]


def _setting_for_phone(
    db: Session,
    from_phone: str,
) -> WhatsAppNotificationSetting | None:
    normalized = normalize_phone_number(from_phone)
    digits = normalized.removeprefix("+")
    settings = list(db.scalars(select(WhatsAppNotificationSetting)))
    for setting in settings:
        if re.sub(r"\D", "", setting.phone_number) == digits:
            return setting
    return None


def _commit_delivery(db: Session, delivery: WhatsAppNotificationDelivery) -> None:
    try:
        db.commit()
        db.refresh(delivery)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(WhatsAppNotificationDelivery)
            .where(WhatsAppNotificationDelivery.event_key == delivery.event_key)
            .limit(1)
        )
        if existing is not None:
            delivery.id = existing.id
            delivery.status = existing.status
            delivery.failure_reason = existing.failure_reason
            return
        raise


def _load_json_dict(raw: str | None) -> dict[str, object]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): value for key, value in parsed.items()}


def _delivery_to_payload(delivery: WhatsAppNotificationDelivery) -> dict[str, object]:
    instrument = delivery.instrument
    asset_class = classify_instrument(instrument) if instrument else None
    return {
        "delivery_id": delivery.id,
        "category": delivery.category,
        "event_key": delivery.event_key,
        "instrument": instrument,
        "asset_class": asset_class,
        "asset_class_label": asset_class_label(asset_class) if asset_class else None,
        "title": delivery.title,
        "status": delivery.status,
        "failure_reason": delivery.failure_reason,
        "provider_message_id": delivery.provider_message_id,
        "created_at": delivery.created_at,
        "sent_at": delivery.sent_at,
        "updated_at": delivery.updated_at,
    }


def _categories_to_api_payload(categories: dict[str, bool]) -> dict[str, bool]:
    return {
        category_to_api_key(category): enabled
        for category, enabled in categories.items()
    }


def _skip_reason(
    setting: WhatsAppNotificationSetting | None,
    categories: dict[str, bool],
    category: str,
) -> str | None:
    if setting is None:
        return "whatsapp_settings_missing"
    if not setting.phone_number:
        return "whatsapp_phone_missing"
    if not setting.opt_in:
        return "whatsapp_opt_in_required"
    if setting.paused:
        return "whatsapp_paused"
    if not categories.get(category, False):
        return "category_disabled"
    return None


def _cooldown_skip_reason(
    db: Session,
    user_id: int,
    category: str,
    instrument: str | None,
) -> str | None:
    if DELIVERY_COOLDOWN_MINUTES <= 0:
        return None
    statement = (
        select(WhatsAppNotificationDelivery)
        .where(WhatsAppNotificationDelivery.user_id == user_id)
        .where(WhatsAppNotificationDelivery.category == category)
        .where(WhatsAppNotificationDelivery.status.in_(["queued", "sent"]))
    )
    if instrument:
        statement = statement.where(WhatsAppNotificationDelivery.instrument == instrument.upper())
    latest = db.scalar(statement.order_by(desc(WhatsAppNotificationDelivery.id)).limit(1))
    if latest is None:
        return None
    try:
        created_at = datetime.fromisoformat(latest.created_at)
    except ValueError:
        return None
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if created_at >= utc_now() - timedelta(minutes=DELIVERY_COOLDOWN_MINUTES):
        return "delivery_cooldown"
    return None


def _template_for_category(category: str) -> str:
    env_by_category = {
        "thesis.new": "WHATSAPP_TEMPLATE_THESIS_NEW",
        "thesis.update": "WHATSAPP_TEMPLATE_THESIS_UPDATE",
        "stock.alert": "WHATSAPP_TEMPLATE_STOCK_ALERT",
        "daily.digest": "WHATSAPP_TEMPLATE_DAILY_DIGEST",
    }
    defaults = {
        "thesis.new": "grao_thesis_new",
        "thesis.update": "grao_thesis_update",
        "stock.alert": "grao_stock_alert",
        "daily.digest": "grao_daily_digest",
    }
    env_name = env_by_category.get(category)
    if env_name:
        configured = os.getenv(env_name, "").strip()
        if configured:
            return configured
    return defaults.get(category, "grao_stock_alert")


def _provider_message_id(result: dict[str, object]) -> str | None:
    messages = result.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            raw_id = first.get("id")
            if isinstance(raw_id, str):
                return raw_id
    return None


def _template_result_summary(result: dict[str, object]) -> dict[str, object]:
    return {
        "messaging_product": result.get("messaging_product"),
        "messages": result.get("messages"),
    }


def _safe_whatsapp_text(value: str, max_length: int) -> str:
    text = " ".join(str(value).split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "."


def _mask_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) <= 4:
        return "****"
    return f"+{'*' * max(0, len(digits) - 4)}{digits[-4:]}"


def _float_value(value: object, default: float = 0.0) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _int_value(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _alert_title(event: AlertEvent) -> str:
    labels = {
        "news_magnitude": "Noticia relevante",
        "signal_confidence": "Sinal com alta confianca",
        "anti_hype": "Alerta anti-hype",
        "circuit_breaker": "Circuit breaker",
    }
    label = labels.get(event.event_type, "Alerta de mercado")
    if event.instrument:
        return f"{label}: {event.instrument}"
    return label


def _alert_body(event: AlertEvent, payload: dict[str, object]) -> str:
    if event.event_type == "news_magnitude":
        headline = str(payload.get("headline") or "Noticia relevante capturada.")
        magnitude = _float_value(payload.get("magnitude_score"))
        return f"{headline} Magnitude: {magnitude:.2f}."
    if event.event_type == "signal_confidence":
        confidence = _float_value(payload.get("confidence"))
        return f"Sinal descritivo atingiu confianca de {confidence:.2f}."
    if event.event_type == "anti_hype":
        score = _float_value(payload.get("anti_hype_score"))
        return f"Score anti-hype em zona de atencao: {score:.2f}."
    if event.event_type == "circuit_breaker":
        reason = str(payload.get("reason") or "Regra de risco acionada.")
        return f"Circuit breaker atualizado. Motivo: {reason}."
    return f"Evento {event.event_type} registrado no monitor."


def _thesis_new_body(thesis: dict[str, object]) -> str:
    instrument = str(thesis.get("instrument") or "")
    direction = str(thesis.get("direction") or "")
    confidence = _float_value(thesis.get("confidence_tese_pct"))
    expected = _float_value(thesis.get("expected_financial_pct"))
    entry = _float_value(thesis.get("entry_price"))
    target = _float_value(thesis.get("target_price"))
    stop = _float_value(thesis.get("stop_price"))
    return (
        f"{instrument} com tese {direction}. Confianca {confidence:.1f}%, "
        f"esperado {expected:.2f}%. Entrada R$ {entry:.2f}, alvo R$ {target:.2f}, "
        f"stop R$ {stop:.2f}."
    )


def _thesis_update_body(thesis: dict[str, object]) -> str:
    status = str(thesis.get("monitor_status") or "monitoring")
    action = str(thesis.get("suggested_action") or "manter_monitoramento")
    latest = _float_value(thesis.get("latest_price"))
    unrealized = _float_value(thesis.get("unrealized_financial_pct"))
    progress = _float_value(thesis.get("progress_to_target_pct"))
    return (
        f"Status {status}. Acao sugerida do monitor: {action}. "
        f"Preco atual R$ {latest:.2f}; resultado simulado {unrealized:.2f}%; "
        f"progresso ao alvo {progress:.1f}%."
    )


def _thesis_update_key(
    user_id: int,
    thesis: dict[str, object],
    thresholds: dict[str, float],
) -> str | None:
    thesis_id = str(thesis.get("thesis_id") or "")
    status = str(thesis.get("monitor_status") or "monitoring")
    if status in {"target_hit", "stop_alert"}:
        return f"thesis.update:{user_id}:{thesis_id}:{status}"
    progress = _float_value(thesis.get("progress_to_target_pct"))
    threshold = max(thresholds["thesis_progress_delta_pct"], 1.0)
    if abs(progress) >= threshold:
        bucket = int(progress / threshold)
        return f"thesis.update:{user_id}:{thesis_id}:progress:{bucket}"
    return None


def _process_provider_statuses(db: Session, payload: dict[str, object]) -> int:
    status_count = 0
    for status_payload in _webhook_items(payload, "statuses"):
        message_id = status_payload.get("id")
        provider_status = status_payload.get("status")
        if not isinstance(message_id, str) or not isinstance(provider_status, str):
            continue
        errors = status_payload.get("errors")
        failure_reason = json.dumps(errors, ensure_ascii=True)[:500] if errors else None
        if update_delivery_status_from_provider(
            db,
            provider_message_id=message_id,
            provider_status=provider_status,
            failure_reason=failure_reason,
        ):
            status_count += 1
    return status_count


def _process_inbound_messages(
    db: Session,
    payload: dict[str, object],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for message in _webhook_items(payload, "messages"):
        from_phone = message.get("from")
        text_payload = message.get("text")
        if not isinstance(from_phone, str) or not isinstance(text_payload, dict):
            continue
        body = text_payload.get("body")
        if not isinstance(body, str):
            continue
        results.append(process_inbound_command(db, from_phone=from_phone, text=body))
    return results


def _webhook_items(payload: dict[str, object], item_key: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return items
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            raw_items = value.get(item_key)
            if not isinstance(raw_items, list):
                continue
            items.extend(
                {str(key): cast(object, value) for key, value in raw.items()}
                for raw in raw_items
                if isinstance(raw, dict)
            )
    return items


def _normalize_command(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
