from __future__ import annotations

from typing import Any

from .data_status import failure, success
from .technical_analysis import compute_atr, compute_regime_label, compute_support_resistance

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


SCENARIOS = [
    "Continuation / upside squeeze",
    "Range / mean reversion",
    "Downside deleveraging",
    "Volatility shock / liquidation cascade",
]


def compute_crypto_market_regime(klines) -> str:
    if pd is None or klines is None or getattr(klines, "empty", True) or "close" not in klines.columns:
        return "mixed evidence"
    return compute_regime_label(klines["close"])


def compute_derivatives_pressure(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    snapshot = snapshot or {}
    funding = snapshot.get("funding_rate")
    taker = snapshot.get("taker_buy_sell_ratio")
    global_ratio = snapshot.get("global_long_short_ratio")
    top_position = snapshot.get("top_trader_position_ratio")
    pressure = 50.0
    notes = []
    if funding is not None:
        pressure += min(15.0, abs(float(funding)) * 100000)
        notes.append("funding contributes to crowding context")
    if taker is not None:
        pressure += min(10.0, abs(float(taker) - 1.0) * 12)
        notes.append("taker flow imbalance observed")
    if global_ratio is not None and top_position is not None:
        pressure += min(10.0, abs(float(global_ratio) - float(top_position)) * 6)
        notes.append("crowd and top-trader positioning diverge")
    return {
        "pressure_score": max(0.0, min(100.0, pressure)),
        "summary": "; ".join(notes) if notes else "derivatives evidence is limited",
    }


def _round_levels(price: float, atr: float) -> list[float]:
    step = max(1.0, round(atr / 2, -1) if atr >= 10 else round(atr / 2, 2))
    levels = []
    for multiplier in range(-6, 7):
        levels.append(price + multiplier * step)
    magnitude = 10 ** max(0, len(str(int(abs(price)))) - 2)
    rounded = round(price / magnitude) * magnitude
    levels.extend([rounded - magnitude, rounded, rounded + magnitude])
    return [level for level in levels if level > 0]


def estimate_liquidation_pressure_map(
    klines=None,
    oi_history=None,
    snapshot: dict[str, Any] | None = None,
    *,
    current_price: float | None = None,
):
    if pd is None:
        return [], failure(source="local estimate", provider="crypto scenarios", error="pandas is not installed", is_estimated=True)
    snapshot = snapshot or {}
    if current_price is None:
        current_price = snapshot.get("mark_price") or snapshot.get("current_price")
    if current_price is None and klines is not None and not getattr(klines, "empty", True) and "close" in klines.columns:
        current_price = float(klines["close"].dropna().iloc[-1])
    if not current_price:
        frame = pd.DataFrame(columns=["level", "side", "leverage_band", "pressure_score", "distance_pct", "basis", "confidence", "caveat"])
        return frame, failure(source="Estimated liquidation pressure map", provider="crypto scenarios", error="Current price unavailable.", coverage="missing price", is_estimated=True)

    atr_value = None
    swing_levels: list[float] = []
    if klines is not None and not getattr(klines, "empty", True) and {"high", "low", "close"}.issubset(klines.columns):
        atr = compute_atr(klines["high"], klines["low"], klines["close"])
        if atr is not None and not atr.dropna().empty:
            atr_value = float(atr.dropna().iloc[-1])
        recent = klines.tail(min(80, len(klines)))
        swing_levels.extend([float(recent["high"].max()), float(recent["low"].min())])
        support_resistance = compute_support_resistance(klines["close"])
        swing_levels.extend([value for value in support_resistance.values() if value])
    atr_value = atr_value or max(current_price * 0.015, 1.0)

    oi_change = 0.0
    if oi_history is not None and not getattr(oi_history, "empty", True) and "sum_open_interest" in oi_history.columns:
        series = oi_history["sum_open_interest"].dropna()
        if len(series) > 3 and series.iloc[0]:
            oi_change = float((series.iloc[-1] / series.iloc[0] - 1.0) * 100.0)

    volume_bias = 0.0
    if klines is not None and not getattr(klines, "empty", True) and "volume" in klines.columns:
        vols = klines["volume"].dropna()
        if len(vols) > 20 and vols.tail(20).mean():
            volume_bias = float((vols.tail(5).mean() / vols.tail(20).mean() - 1.0) * 10.0)

    funding = snapshot.get("funding_rate") or 0.0
    levels = set(round(level, 2) for level in _round_levels(current_price, atr_value) + swing_levels)
    rows = []
    leverage_bands = [5, 10, 20, 50, 100]
    for leverage in leverage_bands:
        up = current_price * (1 + 1 / leverage)
        down = current_price * (1 - 1 / leverage)
        levels.add(round(up, 2))
        levels.add(round(down, 2))

    for level in sorted(levels):
        distance_pct = (level / current_price - 1.0) * 100.0
        if abs(distance_pct) < 0.05:
            continue
        side = "upside short-pressure zone" if level > current_price else "downside long-pressure zone"
        nearest_lev = min(leverage_bands, key=lambda lev: abs(abs(distance_pct) - (100 / lev)))
        swing_score = min(30.0, min(abs(level - swing) for swing in swing_levels) / atr_value * -10 + 30) if swing_levels else 10.0
        round_score = 20.0 if abs(level - round(level, -max(0, len(str(int(level))) - 2))) <= atr_value * 0.35 else 8.0
        distance_score = max(0.0, 25.0 - abs(distance_pct) * 1.7)
        oi_score = min(15.0, max(0.0, oi_change))
        funding_score = min(10.0, abs(float(funding)) * 80000)
        score = max(0.0, min(100.0, swing_score + round_score + distance_score + oi_score + funding_score + volume_bias))
        confidence = "medium" if oi_history is not None and not getattr(oi_history, "empty", True) else "low"
        rows.append(
            {
                "level": level,
                "side": side,
                "leverage_band": f"{nearest_lev}x",
                "pressure_score": round(score, 2),
                "distance_pct": round(distance_pct, 2),
                "basis": "ATR, pivots, OI change, volume proxy, funding context",
                "confidence": confidence,
                "caveat": "Estimated, not official exchange liquidation data.",
            }
        )
    frame = pd.DataFrame(rows, columns=["level", "side", "leverage_band", "pressure_score", "distance_pct", "basis", "confidence", "caveat"])
    frame = frame.sort_values("pressure_score", ascending=False).reset_index(drop=True)
    return frame, success(frame, source="Estimated liquidation pressure map", provider="crypto scenarios", is_estimated=True, coverage="estimated liquidation pressure", warning="Estimated, not official exchange liquidation data.")


def crypto_scenario_matrix(
    symbol: str = "BTCUSDT",
    klines=None,
    oi_history=None,
    snapshot: dict[str, Any] | None = None,
    pressure_map=None,
):
    snapshot = snapshot or {}
    regime = compute_crypto_market_regime(klines)
    pressure = compute_derivatives_pressure(snapshot)
    data_gaps = snapshot.get("data_gaps") or "none"
    price = snapshot.get("mark_price") or snapshot.get("current_price")
    support = resistance = None
    if pd is not None and klines is not None and not getattr(klines, "empty", True) and "close" in klines.columns:
        sr = compute_support_resistance(klines["close"])
        support = sr.get("support")
        resistance = sr.get("resistance")
    rows = [
        {
            "scenario": SCENARIOS[0],
            "evidence_weight": round(55 + (10 if regime == "risk-on" else 0) + min(10, pressure["pressure_score"] / 10), 1),
            "evidence_summary": "Momentum and derivatives pressure are monitored for squeeze risk.",
            "supporting_data": f"regime={regime}; pressure={pressure['summary']}",
            "invalidation_level": f"Below {support:.2f}" if support else "Support level unavailable",
            "watch_points": "Funding acceleration, OI expansion, taker flow imbalance",
            "catalysts": "Macro liquidity, ETF flow headlines, exchange flow changes",
            "data_gaps": data_gaps,
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
        {
            "scenario": SCENARIOS[1],
            "evidence_weight": round(55 if regime == "mixed" or regime == "mixed evidence" else 45, 1),
            "evidence_summary": "Mixed trend and moderate derivatives evidence can support range behavior.",
            "supporting_data": f"current_price={price}; regime={regime}",
            "invalidation_level": f"Outside {support:.2f}-{resistance:.2f}" if support and resistance else "Range boundaries unavailable",
            "watch_points": "Volume fade, funding normalization, failed breakout attempts",
            "catalysts": "Calendar events, stablecoin liquidity, risk-asset correlation",
            "data_gaps": data_gaps,
            "confidence_caveat": "Range evidence can change quickly during volatility expansion.",
        },
        {
            "scenario": SCENARIOS[2],
            "evidence_weight": round(55 + (10 if regime in {"stress", "defensive"} else 0) + max(0, pressure["pressure_score"] - 60) / 4, 1),
            "evidence_summary": "Downside deleveraging risk rises when price weakens while leverage evidence stays elevated.",
            "supporting_data": f"regime={regime}; derivatives_pressure={pressure['pressure_score']:.1f}",
            "invalidation_level": f"Recovery above {resistance:.2f}" if resistance else "Resistance level unavailable",
            "watch_points": "OI expansion on weakness, negative taker imbalance, elevated funding reversal",
            "catalysts": "Exchange liquidation events, macro risk-off, stablecoin contraction",
            "data_gaps": data_gaps,
            "confidence_caveat": "This is scenario context, not certainty.",
        },
        {
            "scenario": SCENARIOS[3],
            "evidence_weight": round(min(90, pressure["pressure_score"]), 1),
            "evidence_summary": "Liquidation cascade risk is framed from estimated pressure zones and derivatives crowding.",
            "supporting_data": "Estimated pressure map; websocket live liquidation stream deferred",
            "invalidation_level": "Volatility compression with falling OI",
            "watch_points": "Rapid basis shifts, funding dislocation, cascading volume spikes",
            "catalysts": "Exchange outages, sharp macro surprise, forced deleveraging prints",
            "data_gaps": f"{data_gaps}; official liquidation heatmap unavailable in free mode",
            "confidence_caveat": "Estimated zones are not official exchange liquidation levels.",
        },
    ]
    if pd is None:
        return rows
    return pd.DataFrame(rows)


def compute_crypto_scenario_matrix(symbol: str = "BTCUSDT", horizon: str = "1w", evidence: dict[str, Any] | None = None):
    evidence = evidence or {}
    frame = crypto_scenario_matrix(
        symbol=symbol,
        klines=evidence.get("klines"),
        oi_history=evidence.get("oi_history"),
        snapshot=evidence.get("snapshot"),
        pressure_map=evidence.get("pressure_map"),
    )
    if pd is not None and hasattr(frame, "copy"):
        frame = frame.copy()
        frame["asset_type"] = "crypto"
        frame["asset"] = symbol
        frame["horizon"] = horizon
        frame["source_status"] = "phase4 crypto scenario engine"
    return frame, success(frame, source="phase4 crypto scenario engine", provider="crypto_scenarios", is_estimated=True, coverage=f"{len(frame)} scenarios" if hasattr(frame, "__len__") else "scenario rows")
