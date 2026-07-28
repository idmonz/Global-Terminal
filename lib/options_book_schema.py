from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE

@dataclass(frozen=True)
class OptionBookPosition:
    position_id: str
    underlying: str
    option_type: str
    expiry: str
    strike: float
    quantity: float
    position: str
    premium: float
    mark: float
    implied_volatility: float
    underlying_price: float
    contract_multiplier: float = 100.0
    source: str = "user_supplied_local_position"
    timestamp: str = ""
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None
    rho: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

OPTION_BOOK_NOTICE = GOAL12B_RESEARCH_ONLY_NOTICE
