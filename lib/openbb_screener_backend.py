from __future__ import annotations

from typing import Any

import pandas as pd

from .data_status import DataResult, combine_results, ok_result
from .openbb_bridge import OPENBB_CAVEAT, is_openbb_installed, openbb_available_result
from .openbb_provider_adapter import (
    get_openbb_equity_active,
    get_openbb_equity_gainers,
    get_openbb_equity_losers,
    get_openbb_equity_screener,
    get_openbb_etf_active,
    get_openbb_etf_country_exposure,
    get_openbb_etf_gainers,
    get_openbb_etf_losers,
    get_openbb_etf_sector_exposure,
)


SCREENER_FIELDS = [
    "ticker",
    "name",
    "price",
    "market_cap",
    "sector",
    "industry",
    "country",
    "return_1d_pct",
    "return_1w_pct",
    "return_1m_pct",
    "return_ytd_pct",
    "realized_volatility_pct",
    "drawdown_pct",
    "rsi",
    "trend_state",
    "pe",
    "ps",
    "pb",
    "ev_ebitda",
    "roe",
    "roa",
    "gross_margin",
    "operating_margin",
    "debt_equity",
    "revenue_growth",
    "earnings_growth",
    "short_interest",
    "insider_activity",
    "institutional_ownership",
    "analyst_estimate",
    "etf_holdings_count",
    "etf_top_holding_concentration",
    "etf_sector_exposure",
    "etf_country_exposure",
    "options_unusual_activity",
    "news_impact_score",
    "data_quality_score",
]


def _normalize_frame(data: Any) -> pd.DataFrame:
    frame = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if frame.empty:
        return frame
    frame.columns = [str(col).strip().lower().replace(" ", "_").replace("/", "_") for col in frame.columns]
    rename = {"symbol": "ticker", "marketcap": "market_cap", "pe_ratio": "pe", "price_to_sales": "ps", "price_to_book": "pb"}
    frame = frame.rename(columns={src: dst for src, dst in rename.items() if src in frame.columns})
    if "ticker" in frame.columns:
        frame["ticker"] = frame["ticker"].astype(str).str.upper()
    for field in SCREENER_FIELDS:
        if field not in frame.columns:
            frame[field] = None
    frame["source_status"] = "openbb_optional"
    frame["source_caveat"] = OPENBB_CAVEAT
    return frame


def _result_frame(result: DataResult) -> pd.DataFrame:
    return _normalize_frame(result.data) if result.ok else pd.DataFrame(columns=SCREENER_FIELDS + ["source_status", "source_caveat"])


def get_openbb_stock_screener_candidates(filters: dict[str, Any] | None = None) -> tuple[pd.DataFrame, DataResult]:
    result = get_openbb_equity_screener(filters=filters)
    return _result_frame(result), result


def get_openbb_etf_screener_candidates(filters: dict[str, Any] | None = None) -> tuple[pd.DataFrame, DataResult]:
    movers, status = get_openbb_market_movers(asset_type="etf")
    return movers, status


def get_openbb_market_movers(asset_type: str = "equity") -> tuple[pd.DataFrame, DataResult]:
    if asset_type.lower() == "etf":
        results = [get_openbb_etf_gainers(), get_openbb_etf_losers(), get_openbb_etf_active()]
    else:
        results = [get_openbb_equity_gainers(), get_openbb_equity_losers(), get_openbb_equity_active()]
    frames = []
    labels = ["gainer", "loser", "active"]
    for result, label in zip(results, labels):
        frame = _result_frame(result)
        if not frame.empty:
            frame["mover_bucket"] = label
            frames.append(frame)
    status = combine_results(results, provider="openbb_screener", source=f"OpenBB {asset_type} market movers")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SCREENER_FIELDS), status


def get_openbb_gainers_losers_active() -> tuple[pd.DataFrame, DataResult]:
    return get_openbb_market_movers("equity")


def get_openbb_etf_exposure_snapshot(symbol: str) -> tuple[pd.DataFrame, DataResult]:
    sector = get_openbb_etf_sector_exposure(symbol)
    country = get_openbb_etf_country_exposure(symbol)
    frames = []
    for result, exposure_type in [(sector, "sector"), (country, "country")]:
        if result.ok and isinstance(result.data, pd.DataFrame) and not result.data.empty:
            frame = result.data.copy()
            frame["ticker"] = symbol.upper()
            frame["exposure_type"] = exposure_type
            frames.append(frame)
    status = combine_results([sector, country], provider="openbb_screener", source=f"{symbol} OpenBB ETF exposure")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(), status


def merge_native_and_openbb_screener_data(native_frame: Any, openbb_frame: Any) -> pd.DataFrame:
    native = native_frame.copy() if isinstance(native_frame, pd.DataFrame) else pd.DataFrame(native_frame)
    openbb = _normalize_frame(openbb_frame)
    if native.empty:
        merged = openbb
    elif openbb.empty or "ticker" not in native.columns:
        merged = native.copy()
        merged["openbb_source_status"] = "not available"
        merged["openbb_data_gap"] = True
    else:
        native = native.copy()
        native["ticker"] = native["ticker"].astype(str).str.upper()
        merged = native.merge(openbb, on="ticker", how="left", suffixes=("", "_openbb"))
        for field in SCREENER_FIELDS:
            openbb_col = f"{field}_openbb"
            if field in merged.columns and openbb_col in merged.columns:
                merged[field] = merged[field].where(merged[field].notna(), merged[openbb_col])
        merged["openbb_data_gap"] = merged.get("source_status").isna() if "source_status" in merged.columns else True
    if "data_quality_score" not in merged.columns or merged["data_quality_score"].isna().all():
        available_cols = [col for col in ["price", "return_1m_pct", "realized_volatility_pct", "market_cap", "sector", "pe", "roe"] if col in merged.columns]
        merged["data_quality_score"] = (merged[available_cols].notna().mean(axis=1) * 100).round(1) if available_cols else 0.0
    merged["source_caveat"] = OPENBB_CAVEAT
    return merged


def build_screener_source_status(source_mode: str = "Auto", openbb_status: DataResult | None = None) -> dict[str, Any]:
    installed = is_openbb_installed()
    return {
        "source_mode": source_mode,
        "openbb_installed": installed,
        "openbb_status": openbb_status.refreshed_status() if openbb_status is not None else ("available" if installed else "not installed"),
        "fallback_allowed": source_mode in {"Auto", "OpenBB preferred"},
        "native_provider": "screeners/market_data",
        "caveat": OPENBB_CAVEAT,
    }


def build_openbb_screener_or_fallback(native_frame: Any, native_status: DataResult, *, asset_class: str, source_mode: str = "Auto") -> tuple[pd.DataFrame, DataResult, dict[str, Any]]:
    if source_mode == "Native only":
        return native_frame, native_status, build_screener_source_status(source_mode)
    if asset_class not in {"Stocks", "ETFs"}:
        if source_mode == "OpenBB only":
            status = ok_result(pd.DataFrame(columns=SCREENER_FIELDS), source="OpenBB screener data gap", provider="openbb_screener", warning=f"OpenBB screener bridge currently supports Stocks and ETFs. {asset_class} remains native-only.", coverage="data gap", is_estimated=True)
            status.ok = False
            return status.data, status, build_screener_source_status(source_mode, status)
        return native_frame, native_status, build_screener_source_status(source_mode)
    if not is_openbb_installed():
        status = openbb_available_result()
        if source_mode == "OpenBB only":
            return pd.DataFrame(columns=SCREENER_FIELDS), status, build_screener_source_status(source_mode, status)
        merged = merge_native_and_openbb_screener_data(native_frame, pd.DataFrame())
        return merged, native_status, build_screener_source_status(source_mode, status)
    if asset_class == "ETFs":
        openbb_frame, openbb_status = get_openbb_etf_screener_candidates()
    else:
        openbb_frame, openbb_status = get_openbb_stock_screener_candidates()
    if source_mode == "OpenBB only":
        return openbb_frame, openbb_status, build_screener_source_status(source_mode, openbb_status)
    merged = merge_native_and_openbb_screener_data(native_frame, openbb_frame)
    status = combine_results([native_status, openbb_status], provider="screeners", source="native + OpenBB screener")
    return merged, status, build_screener_source_status(source_mode, openbb_status)


def build_screener_factor_presets() -> list[dict[str, Any]]:
    return [
        {"preset": "Large-cap quality", "label": "Research candidate screen", "fields": ["market_cap", "roe", "gross_margin", "debt_equity"]},
        {"preset": "Value candidates", "label": "Research candidate screen", "fields": ["pe", "ps", "pb", "ev_ebitda"]},
        {"preset": "Momentum leaders", "label": "Watchlist screen", "fields": ["return_1m_pct", "return_ytd_pct", "rsi", "trend_state"]},
        {"preset": "Low volatility defensive", "label": "Watchlist screen", "fields": ["realized_volatility_pct", "drawdown_pct"]},
        {"preset": "High short interest", "label": "Watchlist screen", "fields": ["short_interest", "volume_zscore"]},
        {"preset": "High options activity", "label": "Watchlist screen", "fields": ["options_unusual_activity", "open_interest"]},
        {"preset": "ETF sector exposure", "label": "ETF exposure screen", "fields": ["etf_sector_exposure", "etf_top_holding_concentration"]},
        {"preset": "ETF country exposure", "label": "ETF exposure screen", "fields": ["etf_country_exposure", "etf_top_holding_concentration"]},
        {"preset": "Macro-sensitive assets", "label": "Watchlist screen", "fields": ["rates_macro_score", "macro_sensitivity", "source_confidence"]},
        {"preset": "Energy/chokepoint exposure", "label": "Watchlist screen", "fields": ["energy_risk_proxy", "chokepoint_exposure", "news_impact_score"]},
        {"preset": "Crypto derivatives stress", "label": "Watchlist screen", "fields": ["funding", "open_interest_change", "taker_ratio"]},
        {"preset": "News impact watchlist", "label": "Watchlist screen", "fields": ["news_impact_score", "data_quality_score"]},
    ]


def enrich_screener_factor_scores(frame: Any) -> pd.DataFrame:
    data = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame(frame)
    if data.empty:
        return data
    for column in ["return_1m_pct", "realized_volatility_pct", "pe", "pb", "roe", "news_impact_score", "options_unusual_activity"]:
        if column not in data.columns:
            data[column] = None
    data["momentum_score"] = pd.to_numeric(data["return_1m_pct"], errors="coerce").rank(pct=True).fillna(0.5).mul(100).round(1)
    data["risk_score"] = (100 - pd.to_numeric(data["realized_volatility_pct"], errors="coerce").rank(pct=True).fillna(0.5).mul(100)).round(1)
    valuation_base = pd.to_numeric(data["pe"], errors="coerce").fillna(pd.to_numeric(data["pb"], errors="coerce"))
    data["valuation_score"] = (100 - valuation_base.rank(pct=True).fillna(0.5).mul(100)).clip(0, 100).round(1)
    data["quality_score"] = pd.to_numeric(data["roe"], errors="coerce").rank(pct=True).fillna(0.5).mul(100).round(1)
    data["news_impact_score"] = pd.to_numeric(data["news_impact_score"], errors="coerce").fillna(0.0)
    data["options_activity_score"] = pd.to_numeric(data["options_unusual_activity"], errors="coerce").fillna(0.0)
    factor_cols = ["momentum_score", "risk_score", "valuation_score", "quality_score", "news_impact_score", "options_activity_score"]
    data["factor_coverage_score"] = data[factor_cols].notna().mean(axis=1).mul(100).round(1)
    data["source_confidence"] = (data.get("data_quality_score", data["factor_coverage_score"]).fillna(data["factor_coverage_score"]) * 0.7 + data["factor_coverage_score"] * 0.3).round(1)
    data["macro_sensitivity"] = data.get("macro_sensitivity", "Data gap")
    data["energy_risk_proxy"] = data.get("energy_risk_proxy", 0.0)
    data["chokepoint_exposure"] = data.get("chokepoint_exposure", "Data gap")
    return data
