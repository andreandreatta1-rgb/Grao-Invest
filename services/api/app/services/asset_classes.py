from __future__ import annotations

import re
from typing import Literal

AssetClass = Literal["stock", "fii", "etf", "bdr", "fx", "cash", "unknown"]

STOCK_EXAMPLES = ("PETR4", "VALE3", "ITUB4", "WEGE3", "B3SA3")
FII_EXAMPLES = ("KNRI11", "HGLG11", "MXRF11", "VISC11")
ETF_EXAMPLES = ("BOVA11", "SMAL11", "IVVB11", "HASH11")
BDR_EXAMPLES = ("AAPL34", "MSFT34", "GOGL34", "AMZO34")
FX_EXAMPLES = ("USD-BRL", "EUR-BRL")
DEFAULT_MULTI_ASSET_UNIVERSE = (
    *STOCK_EXAMPLES,
    *FII_EXAMPLES,
    *ETF_EXAMPLES,
    *BDR_EXAMPLES,
)

ETF_SYMBOLS = frozenset(
    {
        "BOVA11",
        "BOVB11",
        "BOVV11",
        "BRAX11",
        "DIVO11",
        "ECOO11",
        "FIND11",
        "GOLD11",
        "HASH11",
        "IVVB11",
        "MATB11",
        "NASD11",
        "PIBB11",
        "QBTC11",
        "SMAL11",
        "SPXI11",
        "XFIX11",
    }
)
FII_SYMBOLS = frozenset(
    {
        "BCFF11",
        "BTLG11",
        "HFOF11",
        "HGBS11",
        "HGLG11",
        "HGRE11",
        "IRDM11",
        "KNCR11",
        "KNRI11",
        "MALL11",
        "MXRF11",
        "RBRF11",
        "RECR11",
        "VILG11",
        "VISC11",
        "XPML11",
        "XPLG11",
    }
)
UNIT_SYMBOLS = frozenset(
    {
        "ALUP11",
        "BPAC11",
        "ENGI11",
        "KLBN11",
        "PPLA11",
        "RNEW11",
        "SANB11",
        "SAPR11",
        "TAEE11",
    }
)
PORTFOLIO_ASSET_CLASSES = frozenset({"stock", "fii", "etf", "bdr"})


def normalize_instrument(instrument: str) -> str:
    return re.sub(r"\s+", "", instrument.strip().upper()).replace("/", "-")


def classify_instrument(instrument: str) -> AssetClass:
    symbol = normalize_instrument(instrument)
    compact_symbol = symbol.replace("-", "")
    if not symbol:
        return "unknown"
    if symbol == "CASH-BRL" or compact_symbol in {"CASHBRL", "BRL"}:
        return "cash"
    if _looks_like_fx(symbol, compact_symbol):
        return "fx"
    if symbol in ETF_SYMBOLS:
        return "etf"
    if symbol in FII_SYMBOLS:
        return "fii"
    if symbol in UNIT_SYMBOLS:
        return "stock"
    if re.fullmatch(r"[A-Z]{4}3[1-9]", symbol):
        return "bdr"
    if re.fullmatch(r"[A-Z]{4}11", symbol):
        return "fii"
    if re.fullmatch(r"[A-Z0-9]{4}[3-6]", symbol):
        return "stock"
    return "unknown"


def asset_class_label(asset_class: str) -> str:
    labels = {
        "stock": "Acao BR",
        "fii": "FII",
        "etf": "ETF",
        "bdr": "BDR",
        "fx": "Cambio",
        "cash": "Caixa",
        "unknown": "Outro",
    }
    return labels.get(asset_class, "Outro")


def is_portfolio_asset_class(asset_class: str) -> bool:
    return asset_class in PORTFOLIO_ASSET_CLASSES


def _looks_like_fx(symbol: str, compact_symbol: str) -> bool:
    if compact_symbol in {"USDBRL", "EURBRL", "GBPBRL", "BRLUSD", "BRLEUR"}:
        return True
    if re.fullmatch(r"(USD|EUR|GBP|JPY|ARS|CAD|AUD|CHF|CNY)-?BRL", symbol):
        return True
    if re.fullmatch(r"BRL-?(USD|EUR|GBP|JPY|ARS|CAD|AUD|CHF|CNY)", symbol):
        return True
    return bool(re.fullmatch(r"(DOL|WDO)[A-Z]?\d{0,2}", symbol))
