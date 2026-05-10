from __future__ import annotations

CRYPTO_UNIVERSE = (
    {"instrument": "BTCUSDT", "symbol": "BTC", "name": "Bitcoin"},
    {"instrument": "ETHUSDT", "symbol": "ETH", "name": "Ethereum"},
    {"instrument": "SOLUSDT", "symbol": "SOL", "name": "Solana"},
    {"instrument": "BNBUSDT", "symbol": "BNB", "name": "BNB"},
    {"instrument": "XRPUSDT", "symbol": "XRP", "name": "XRP"},
    {"instrument": "ADAUSDT", "symbol": "ADA", "name": "Cardano"},
    {"instrument": "DOGEUSDT", "symbol": "DOGE", "name": "Dogecoin"},
    {"instrument": "AVAXUSDT", "symbol": "AVAX", "name": "Avalanche"},
    {"instrument": "LINKUSDT", "symbol": "LINK", "name": "Chainlink"},
    {"instrument": "LTCUSDT", "symbol": "LTC", "name": "Litecoin"},
)


def default_crypto_instruments(*, limit: int | None = None) -> list[str]:
    instruments = [str(item["instrument"]).upper() for item in CRYPTO_UNIVERSE]
    if limit is None or limit <= 0:
        return instruments
    return instruments[:limit]


def default_crypto_instruments_csv(*, limit: int | None = None) -> str:
    return ",".join(default_crypto_instruments(limit=limit))
