from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

GOAL12B_RESEARCH_ONLY_NOTICE = "Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions."

REQUIRED_CANONICAL_COLUMNS = [
    "underlying", "expiry", "strike", "option_type", "bid", "ask", "underlying_price", "timestamp", "source"
]
OPTIONAL_CANONICAL_COLUMNS = [
    "symbol", "root", "last", "mark", "mid", "volume", "open_interest", "implied_volatility", "delta", "gamma", "vega", "theta", "rho", "contract_multiplier", "exchange", "currency", "provider", "time_to_expiry_years", "asset_class", "model", "futures_price", "domestic_rate", "foreign_rate", "risk_free_rate", "dividend_yield"
]

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": ("symbol", "contract", "option_symbol"),
    "underlying": ("underlying", "root", "ticker", "asset"),
    "root": ("root", "underlying_root"),
    "expiry": ("expiry", "expiration", "expiration_date", "maturity"),
    "strike": ("strike", "strike_price", "k"),
    "option_type": ("option_type", "right", "type", "call_put", "cp"),
    "bid": ("bid", "bid_price"),
    "ask": ("ask", "ask_price", "offer"),
    "last": ("last", "last_price"),
    "mark": ("mark", "mark_price"),
    "mid": ("mid", "mid_price"),
    "underlying_price": ("underlying_price", "spot", "forward", "futures_price", "index_price"),
    "timestamp": ("timestamp", "asof", "as_of", "snapshot_time", "datetime", "date_time"),
    "source": ("source", "data_source"),
    "provider": ("provider", "vendor"),
    "time_to_expiry_years": ("time_to_expiry_years", "tte", "years_to_expiry"),
    "asset_class": ("asset_class", "instrument_type", "underlying_type"),
    "model": ("model", "pricing_model"),
    "futures_price": ("futures_price", "future_price", "forward"),
    "domestic_rate": ("domestic_rate", "rd"),
    "foreign_rate": ("foreign_rate", "rf"),
    "risk_free_rate": ("risk_free_rate", "rate", "r"),
    "dividend_yield": ("dividend_yield", "q"),
    "volume": ("volume", "vol"),
    "open_interest": ("open_interest", "oi"),
    "implied_volatility": ("implied_volatility", "iv", "mark_iv"),
    "delta": ("delta",),
    "gamma": ("gamma",),
    "vega": ("vega",),
    "theta": ("theta",),
    "rho": ("rho",),
    "contract_multiplier": ("contract_multiplier", "multiplier", "contract_size"),
    "exchange": ("exchange", "venue"),
    "currency": ("currency", "ccy"),
}

@dataclass(frozen=True)
class OptionChainRow:
    underlying: str
    expiry: str
    strike: float
    option_type: str
    bid: float
    ask: float
    underlying_price: float
    timestamp: str
    source: str = "user_supplied_unknown_source"
    symbol: str = ""
    root: str = ""
    last: float | None = None
    mark: float | None = None
    mid: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None
    rho: float | None = None
    contract_multiplier: float = 100.0
    exchange: str = ""
    currency: str = ""
    provider: str = ""
    row_number: int = 0
    quality_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_column_aliases() -> dict[str, tuple[str, ...]]:
    return dict(COLUMN_ALIASES)
