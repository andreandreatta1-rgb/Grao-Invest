from __future__ import annotations

import httpx
import pytest
from app.db import Base
from app.services.notifications import (
    WhatsAppClient,
    WhatsAppClientError,
    normalize_phone_number,
    queue_whatsapp_notification,
    upsert_whatsapp_settings,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


def test_normalize_phone_number_uses_e164_digits() -> None:
    assert normalize_phone_number("+55 11 97106-2620") == "+5511971062620"


def test_whatsapp_client_sends_template(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return httpx.Response(
            200,
            json={
                "messaging_product": "whatsapp",
                "messages": [{"id": "wamid.test"}],
            },
        )

    monkeypatch.setattr("app.services.notifications.httpx.post", fake_post)

    client = WhatsAppClient(access_token="token", phone_number_id="123")
    result = client.send_template(
        to_phone_number="+5511971062620",
        template_name="grao_stock_alert",
        title="Teste",
        body="Mensagem de teste",
    )

    assert result["messages"] == [{"id": "wamid.test"}]
    assert "graph.facebook.com" in str(captured["url"])
    request_payload = captured["kwargs"]["json"]  # type: ignore[index]
    assert request_payload["to"] == "5511971062620"
    assert request_payload["type"] == "template"


def test_whatsapp_client_requires_environment(monkeypatch) -> None:
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    with pytest.raises(WhatsAppClientError):
        WhatsAppClient.from_env()


def test_queue_notification_deduplicates_event_key(db_session: Session, monkeypatch) -> None:
    sent: list[str] = []

    class FakeClient:
        def send_template(self, **kwargs: object) -> dict[str, object]:
            sent.append(str(kwargs["template_name"]))
            return {
                "messaging_product": "whatsapp",
                "messages": [{"id": "wamid.dedupe"}],
            }

    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setattr(
        "app.services.notifications.DELIVERY_COOLDOWN_MINUTES",
        0,
    )
    upsert_whatsapp_settings(
        db_session,
        user_id=1,
        phone_number="+5511971062620",
        display_name="Andre",
        opt_in=True,
        categories={
            "thesis_new": True,
            "thesis_update": True,
            "stock_alert": True,
            "daily_digest": True,
        },
        thresholds={},
    )

    first = queue_whatsapp_notification(
        db_session,
        user_id=1,
        category="stock.alert",
        event_key="stock.alert:1:PETR4:test",
        title="PETR4",
        body="Teste",
        instrument="PETR4",
        client=FakeClient(),  # type: ignore[arg-type]
    )
    second = queue_whatsapp_notification(
        db_session,
        user_id=1,
        category="stock.alert",
        event_key="stock.alert:1:PETR4:test",
        title="PETR4",
        body="Teste",
        instrument="PETR4",
        client=FakeClient(),  # type: ignore[arg-type]
    )

    assert first.id == second.id
    assert first.status == "sent"
    assert sent == ["grao_stock_alert"]
