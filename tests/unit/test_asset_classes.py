from __future__ import annotations

from app.services.asset_classes import (
    asset_class_label,
    classify_instrument,
    is_portfolio_asset_class,
)


def test_classify_brazilian_multiasset_tickers() -> None:
    assert classify_instrument("PETR4") == "stock"
    assert classify_instrument("B3SA3") == "stock"
    assert classify_instrument("BPAC11") == "stock"
    assert classify_instrument("KNRI11") == "fii"
    assert classify_instrument("BOVA11") == "etf"
    assert classify_instrument("AAPL34") == "bdr"
    assert classify_instrument("USD/BRL") == "fx"
    assert classify_instrument("CASH-BRL") == "cash"


def test_portfolio_asset_classes_exclude_context_assets() -> None:
    assert is_portfolio_asset_class("stock") is True
    assert is_portfolio_asset_class("fii") is True
    assert is_portfolio_asset_class("etf") is True
    assert is_portfolio_asset_class("bdr") is True
    assert is_portfolio_asset_class("fx") is False
    assert is_portfolio_asset_class("cash") is False
    assert asset_class_label("fx") == "Cambio"
