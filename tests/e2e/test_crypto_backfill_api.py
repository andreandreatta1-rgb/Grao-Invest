from __future__ import annotations

from app.services.crypto_history_provider import CryptoHistoryProviderError


def test_crypto_backfill_returns_structured_data_gate_when_provider_is_blocked(
    client,
    monkeypatch,
) -> None:
    from app import main as main_module

    def blocked_fetch(*args: object, **kwargs: object) -> list[object]:
        raise CryptoHistoryProviderError(
            "Binance bloqueou a consulta historica para esta regiao.",
            code="provider_region_blocked",
            provider_name="binance",
            user_message=(
                "Fonte historica cripto indisponivel por restricao regional. "
                "Nenhuma nova operacao deve ser avaliada ate haver dados suficientes."
            ),
            retryable=True,
            safe_to_continue=False,
        )

    monkeypatch.setattr(main_module, "fetch_historical_crypto_candles", blocked_fetch)

    response = client.post(
        "/api/market/crypto/backfill",
        json={
            "user_id": 1,
            "provider_name": "binance",
            "instruments": ["BTCUSDT", "ETHUSDT"],
            "interval": "5m",
            "lookback_hours": 24,
            "max_candles_per_instrument": 100,
        },
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "provider_region_blocked"
    assert detail["provider_name"] == "binance"
    assert detail["retryable"] is True
    assert detail["safe_to_continue"] is False
    assert "Nenhuma nova operacao" in detail["user_message"]
