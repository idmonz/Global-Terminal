from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .openbb_fundamental_factor import build_fundamental_factor_scores
from .openbb_options_factor import build_options_factor_scores
from .openbb_rates_factor import build_rates_macro_factor_scores
from .openbb_technical_backend import get_technical_factor_bundle


def build_symbol_factor_backend(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    technical = get_technical_factor_bundle(symbol, source_mode=source_mode)
    fundamental = build_fundamental_factor_scores(symbol, source_mode=source_mode)
    options = build_options_factor_scores(symbol, source_mode=source_mode)
    rates = build_rates_macro_factor_scores(source_mode=source_mode)
    technical_ok = sum(1 for result in technical.values() if result.ok)
    total = len(technical) + 3
    ok_count = technical_ok + int(bool(fundamental["data_quality_score"])) + int(bool(options["source_confidence"])) + int(bool(rates["source_confidence"]))
    return {
        "symbol": symbol.upper(),
        "technical": technical,
        "fundamental": fundamental,
        "options": options,
        "rates_macro": rates,
        "factor_coverage_pct": round(ok_count / max(1, total) * 100, 1),
        "source_confidence": round((fundamental["data_quality_score"] + options["source_confidence"] + rates["source_confidence"]) / 3, 1),
        "data_gaps": list(fundamental["data_gaps"]) + list(options["data_gaps"]) + list(rates["data_gaps"]) + [gap for result in technical.values() for gap in result.data_gaps],
        "caveat": "Unified factor backend keeps OpenBB optional and labels proxy/estimated fields.",
    }


def build_factor_backend_table(symbols: list[str], *, source_mode: str = "auto"):
    rows = []
    payloads = {}
    for symbol in symbols:
        payload = build_symbol_factor_backend(symbol, source_mode=source_mode)
        payloads[symbol.upper()] = payload
        rows.append(
            {
                "symbol": symbol.upper(),
                "factor_coverage_pct": payload["factor_coverage_pct"],
                "source_confidence": payload["source_confidence"],
                "value_score": payload["fundamental"]["value_score"],
                "quality_score": payload["fundamental"]["quality_score"],
                "growth_score": payload["fundamental"]["growth_score"],
                "profitability_score": payload["fundamental"]["profitability_score"],
                "options_activity_score": payload["options"]["options_activity_score"],
                "rates_macro_score": payload["rates_macro"]["score"],
                "data_gap_count": len(payload["data_gaps"]),
            }
        )
    table = pd.DataFrame(rows) if pd is not None else rows
    return {"table": table, "payloads": payloads, "caveat": "Factor table is for research comparison only."}
