from __future__ import annotations

import math
import re
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import numpy as np
import pandas as pd

from .market_data import fetch_many_price_histories
from .performance_attribution import compute_risk_contribution
from .portfolio_backtester import compute_backtest_metrics
from .risk import compute_drawdown_series, compute_rolling_sharpe
from .research_guard_pipeline import run_research_guard_pipeline, summarize_guard_results
from .stress_tests import build_stress_test_matrix


PORTFOLIO_RISK_VERSION = "portfolio_risk.v1"
PORTFOLIO_CACHE_TTL_SECONDS = 300
PORTFOLIO_CACHE_STALE_SECONDS = 1800
MIN_PERFORMANCE_OBSERVATIONS = 40
MIN_ROLLING_OBSERVATIONS = 63
MIN_CORRELATION_OBSERVATIONS = 20
MIN_FACTOR_OBSERVATIONS = 40
ANNUALIZATION = 252
_FIXTURE_FETCHED_AT = "2026-06-20T16:00:00+00:00"
_CACHE_LOCK = threading.Lock()
_RUNTIME_CACHE: dict[str, dict[str, Any]] = {}
_DISCLOSURE = (
    "Portfolio analytics are historical or assumption-bound research calculations only. "
    "They are not investment advice, trading recommendations, position sizing, rebalancing "
    "instructions, trade approvals, broker actions, autonomous actions, or execution instructions."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_portfolio_id(value: str | None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "demo-core")).strip("-")
    return cleaned[:48] or "demo-core"


def _status_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        try:
            return dict(value.to_dict())
        except Exception:
            pass
    if isinstance(value, dict):
        return dict(value)
    return {}


def _status_name(value: Any, default: str = "unavailable") -> str:
    if hasattr(value, "refreshed_status"):
        try:
            raw = str(value.refreshed_status())
        except Exception:
            raw = ""
    else:
        raw = str(_status_dict(value).get("status") or "")
    normalized = raw.strip().lower()
    if normalized in {"fresh", "live", "ok", "available", "live/fresh"}:
        return "live/fresh"
    if normalized in {"cached", "stale", "fixture", "unavailable", "error"}:
        return "unavailable" if normalized == "error" else normalized
    return default


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, pd.DataFrame):
        return [dict(row) for row in value.to_dict(orient="records")]
    if isinstance(value, list):
        return [dict(row) for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def build_demo_portfolio_holdings() -> list[dict[str, Any]]:
    common = {"currency": "USD", "input_classification": "deterministic_fictional_demo"}
    return [
        {**common, "symbol": "AAPL", "name": "Apple", "asset_class": "stock", "sector": "Technology", "quantity": 18.0, "cost_basis": 168.0},
        {**common, "symbol": "MSFT", "name": "Microsoft", "asset_class": "stock", "sector": "Technology", "quantity": 9.0, "cost_basis": 385.0},
        {**common, "symbol": "SPY", "name": "S&P 500 ETF", "asset_class": "ETF", "sector": "Broad equity", "quantity": 14.0, "cost_basis": 515.0},
        {**common, "symbol": "TLT", "name": "Long Treasury ETF", "asset_class": "bond_proxy", "sector": "Rates", "quantity": 32.0, "cost_basis": 94.0},
        {**common, "symbol": "GLD", "name": "Gold ETF", "asset_class": "commodity", "sector": "Precious metals", "quantity": 15.0, "cost_basis": 205.0},
        {**common, "symbol": "BTC-USD", "name": "Bitcoin", "asset_class": "crypto", "sector": "Digital assets", "quantity": 0.12, "cost_basis": 61_000.0},
        {**common, "symbol": "CASH", "name": "USD Cash", "asset_class": "cash", "sector": "Cash", "quantity": 4_500.0, "cost_basis": 1.0},
    ]


def normalize_holdings(rows: Any) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(_records(rows)):
        symbol = str(raw.get("symbol") or raw.get("ticker") or "").strip().upper()
        quantity = _clean_number(raw.get("quantity"))
        cost_basis = _clean_number(raw.get("cost_basis"))
        currency = str(raw.get("currency") or "USD").strip().upper()
        asset_class = str(raw.get("asset_class") or ("cash" if symbol in {"CASH", "USD"} else "custom")).strip()
        reasons: list[str] = []
        if not symbol:
            reasons.append("missing_symbol")
        if symbol in seen:
            reasons.append("duplicate_symbol")
        if quantity is None or quantity <= 0:
            reasons.append("non_positive_quantity")
        if cost_basis is not None and cost_basis < 0:
            reasons.append("negative_cost_basis")
        if currency != "USD":
            reasons.append("fx_rate_required")
        if reasons:
            rejected.append({"row_index": index, "symbol": symbol or None, "reasons": sorted(set(reasons))})
            continue
        seen.add(symbol)
        accepted.append(
            {
                "holding_id": f"holding-{len(accepted) + 1:02d}",
                "symbol": symbol,
                "name": str(raw.get("name") or symbol).strip()[:80],
                "asset_class": asset_class,
                "sector": str(raw.get("sector") or "Unclassified").strip()[:80],
                "region": str(raw.get("region") or ("Global" if asset_class in {"crypto", "commodity", "cash"} else "United States")).strip()[:80],
                "quantity": float(quantity),
                "cost_basis": cost_basis,
                "currency": currency,
                "cash_flag": asset_class == "cash" or symbol in {"CASH", "USD", "CASH_USD"},
                "input_classification": str(raw.get("input_classification") or "local_private"),
            }
        )
    return {
        "valid": bool(accepted) and not rejected,
        "accepted_rows": accepted,
        "rejected_rows": rejected,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
    }


def _fixture_histories() -> dict[str, pd.DataFrame]:
    dates = pd.bdate_range("2025-04-21", periods=300)
    specs = {
        "AAPL": (181.0, 0.00105, 0.012, 13.0),
        "MSFT": (402.0, 0.00082, 0.009, 17.0),
        "SPY": (512.0, 0.00058, 0.0055, 21.0),
        "TLT": (94.0, -0.00005, 0.0045, 15.0),
        "GLD": (204.0, 0.00048, 0.0065, 19.0),
        "BTC-USD": (62_000.0, 0.0012, 0.023, 11.0),
    }
    output: dict[str, pd.DataFrame] = {}
    for offset, (symbol, (base, drift, amplitude, cycle)) in enumerate(specs.items()):
        steps = np.arange(len(dates), dtype=float)
        daily = drift + amplitude * np.sin((steps + offset * 3.0) / cycle) / 10.0
        prices = base * np.cumprod(1.0 + daily)
        output[symbol] = pd.DataFrame(
            {
                "date": dates,
                "open": prices * 0.998,
                "high": prices * 1.006,
                "low": prices * 0.994,
                "close": prices,
                "adj_close": prices,
                "volume": 1_000_000.0 + steps * (500 + offset * 40),
            }
        )
    return output


def _history_series(frame: Any) -> pd.Series:
    if frame is None or getattr(frame, "empty", True):
        return pd.Series(dtype=float)
    data = frame.copy()
    if "date" in data.columns:
        index = pd.to_datetime(data["date"], errors="coerce", utc=True)
    else:
        index = pd.to_datetime(data.index, errors="coerce", utc=True)
    column = next((name for name in ("adj_close", "Adj Close", "close", "Close") if name in data.columns), None)
    if column is None:
        return pd.Series(dtype=float)
    values = data[column]
    if hasattr(values, "columns"):
        values = values.bfill(axis=1).iloc[:, 0]
    series = pd.Series(pd.to_numeric(values, errors="coerce").to_numpy(), index=index)
    return series[~series.index.isna()].dropna().sort_index()


def _runtime_histories(symbols: list[str], period: str) -> tuple[dict[str, Any], dict[str, Any]]:
    key = f"{period}:{','.join(sorted(set(symbols)))}"
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _RUNTIME_CACHE.get(key)
        if cached and now - float(cached["stored_at"]) <= PORTFOLIO_CACHE_TTL_SECONDS:
            return deepcopy(cached["histories"]), {**deepcopy(cached["status"]), "status": "cached", "cached": True}
        try:
            histories, result = fetch_many_price_histories(symbols, period=period)
            status = _status_dict(result)
            usable = {symbol: frame for symbol, frame in histories.items() if not _history_series(frame).empty}
            if not usable:
                raise RuntimeError(status.get("error") or "Provider returned no usable price histories.")
            normalized_status = {
                "provider": status.get("provider") or "yfinance",
                "source": status.get("source") or ",".join(symbols),
                "source_url": "https://finance.yahoo.com/",
                "status": "live/fresh",
                "fetched_at": status.get("fetched_at") or _now_iso(),
                "cached": False,
                "coverage": status.get("coverage"),
                "warning": status.get("warning"),
                "error": None,
            }
            _RUNTIME_CACHE[key] = {
                "stored_at": now,
                "histories": deepcopy(usable),
                "status": deepcopy(normalized_status),
            }
            return usable, normalized_status
        except Exception as exc:
            if cached and now - float(cached["stored_at"]) <= PORTFOLIO_CACHE_STALE_SECONDS:
                return deepcopy(cached["histories"]), {
                    **deepcopy(cached["status"]),
                    "status": "stale",
                    "cached": True,
                    "warning": f"Live refresh failed; stale history retained. {exc}",
                }
            return {}, {
                "provider": "yfinance",
                "source": ",".join(symbols),
                "source_url": "https://finance.yahoo.com/",
                "status": "unavailable",
                "fetched_at": _now_iso(),
                "cached": False,
                "coverage": "0 usable histories",
                "warning": None,
                "error": str(exc),
            }


def reset_portfolio_risk_cache() -> None:
    with _CACHE_LOCK:
        _RUNTIME_CACHE.clear()


def _allocation_rows(holdings: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, float] = {}
    total = sum(float(row.get("market_value") or 0.0) for row in holdings)
    for row in holdings:
        value = row.get("market_value")
        if value is None:
            continue
        label = str(row.get(key) or "Unclassified")
        grouped[label] = grouped.get(label, 0.0) + float(value)
    return [
        {
            "label": label,
            "market_value": round(value, 6),
            "weight": round(value / total, 10) if total else None,
            "units": "USD and decimal weight",
            "not_financial_advice": True,
        }
        for label, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    ]


def _empty_performance(gap: str, benchmark: str) -> dict[str, Any]:
    return {
        "available": False,
        "series": [],
        "drawdown_series": [],
        "rolling_volatility": [],
        "rolling_sharpe": [],
        "metrics": {},
        "sample_count": 0,
        "window": None,
        "benchmark": benchmark,
        "frequency": "daily",
        "annualization": ANNUALIZATION,
        "missing_data_policy": "complete overlap; missing observations are never zero-filled",
        "methods": {
            "simple": {"available": False, "reason": gap},
            "time_weighted": {"available": False, "reason": gap},
            "money_weighted": {"available": False, "reason": "Dated external cash flows are not supplied."},
        },
        "data_gap": gap,
        "caveat": "No performance is produced without sufficient source history.",
        "not_financial_advice": True,
    }


def _performance_payload(
    price_series: dict[str, pd.Series],
    holdings: list[dict[str, Any]],
    benchmark: str,
) -> tuple[dict[str, Any], pd.DataFrame, pd.Series, pd.Series | None]:
    history_symbols = [
        row["symbol"]
        for row in holdings
        if not row["cash_flag"] and row.get("history_available") and row["symbol"] in price_series
    ]
    if not history_symbols:
        return _empty_performance("No holdings have usable price history.", benchmark), pd.DataFrame(), pd.Series(dtype=float), None
    prices = pd.concat({symbol: price_series[symbol] for symbol in history_symbols}, axis=1).sort_index()
    complete_prices = prices.dropna(how="any")
    returns = complete_prices.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if len(returns) < MIN_PERFORMANCE_OBSERVATIONS:
        gap = f"Performance requires {MIN_PERFORMANCE_OBSERVATIONS} complete observations; observed {len(returns)}."
        return _empty_performance(gap, benchmark), returns, pd.Series(dtype=float), None

    weights = {row["symbol"]: float(row.get("weight") or 0.0) for row in holdings}
    portfolio = sum(returns[symbol] * weights.get(symbol, 0.0) for symbol in history_symbols)
    portfolio = pd.Series(portfolio, index=returns.index, name="portfolio").dropna()
    benchmark_returns: pd.Series | None = None
    if benchmark in price_series:
        bench = price_series[benchmark].pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
        benchmark_returns = bench.reindex(portfolio.index).dropna()
        if len(benchmark_returns) != len(portfolio):
            aligned = pd.concat([portfolio, benchmark_returns.rename("benchmark")], axis=1).dropna()
            portfolio = aligned.iloc[:, 0]
            benchmark_returns = aligned.iloc[:, 1]
    metrics = compute_backtest_metrics(portfolio, benchmark_returns=benchmark_returns, annualization=ANNUALIZATION)
    equity = (1.0 + portfolio).cumprod()
    drawdown = compute_drawdown_series(equity)
    benchmark_equity = (1.0 + benchmark_returns).cumprod() if benchmark_returns is not None and not benchmark_returns.empty else None
    rolling_vol = portfolio.rolling(MIN_ROLLING_OBSERVATIONS).std() * math.sqrt(ANNUALIZATION)
    rolling_sharpe = compute_rolling_sharpe(portfolio, window=MIN_ROLLING_OBSERVATIONS, annualization=ANNUALIZATION)
    series = []
    for date, value in equity.items():
        item = {
            "date": date.date().isoformat(),
            "portfolio_index": round(float(value * 100.0), 6),
            "benchmark_index": None,
        }
        if benchmark_equity is not None and date in benchmark_equity.index:
            item["benchmark_index"] = round(float(benchmark_equity.loc[date] * 100.0), 6)
        series.append(item)
    simple_return = float(equity.iloc[-1] - 1.0)
    output = {
        "available": True,
        "series": series,
        "drawdown_series": [
            {"date": date.date().isoformat(), "drawdown": round(float(value), 10)}
            for date, value in drawdown.items()
        ],
        "rolling_volatility": [
            {"date": date.date().isoformat(), "annualized_volatility": round(float(value), 10)}
            for date, value in rolling_vol.dropna().items()
        ],
        "rolling_sharpe": [
            {"date": date.date().isoformat(), "rolling_sharpe": round(float(value), 10)}
            for date, value in rolling_sharpe.dropna().items()
        ],
        "metrics": {key: _clean_number(value) for key, value in metrics.items()},
        "sample_count": len(portfolio),
        "window": {"start": portfolio.index[0].date().isoformat(), "end": portfolio.index[-1].date().isoformat()},
        "benchmark": benchmark,
        "frequency": "daily",
        "annualization": ANNUALIZATION,
        "missing_data_policy": "complete overlap; missing observations are never zero-filled",
        "methods": {
            "simple": {"available": True, "value": simple_return, "units": "decimal return"},
            "time_weighted": {
                "available": True,
                "value": simple_return,
                "units": "decimal return",
                "reason": "No external cash flows are present, so linked daily returns equal the simple period return.",
            },
            "money_weighted": {"available": False, "value": None, "reason": "Dated external cash flows are not supplied."},
        },
        "data_gap": None,
        "caveat": "Historical delayed public or deterministic fixture prices; past performance does not guarantee future results.",
        "not_financial_advice": True,
    }
    return output, returns, portfolio, benchmark_returns


def _risk_payload(performance: dict[str, Any], portfolio_returns: pd.Series, holdings: list[dict[str, Any]]) -> dict[str, Any]:
    if not performance.get("available") or portfolio_returns.empty:
        return {
            "available": False,
            "sample_count": 0,
            "frequency": "daily",
            "annualization": ANNUALIZATION,
            "metrics": {},
            "data_gap": performance.get("data_gap") or "No portfolio return history.",
            "caveat": "Risk metrics require sufficient observed returns.",
            "not_financial_advice": True,
        }
    metrics = performance.get("metrics") or {}
    largest_weight = max((float(row.get("weight") or 0.0) for row in holdings), default=0.0)
    return {
        "available": True,
        "sample_count": len(portfolio_returns),
        "frequency": "daily",
        "annualization": ANNUALIZATION,
        "lookback": performance.get("window"),
        "missing_data_policy": "complete overlap",
        "metrics": {
            "annualized_volatility": metrics.get("annualized_volatility"),
            "downside_volatility": float(portfolio_returns[portfolio_returns < 0].std() * math.sqrt(ANNUALIZATION)) if (portfolio_returns < 0).any() else 0.0,
            "max_drawdown": metrics.get("max_drawdown"),
            "historical_var_95_daily": metrics.get("var_95"),
            "historical_cvar_95_daily": metrics.get("cvar_95"),
            "sharpe_zero_cash_rate": metrics.get("sharpe"),
            "sortino_zero_cash_rate": metrics.get("sortino"),
            "beta_vs_benchmark": metrics.get("beta_vs_benchmark"),
            "largest_position_weight": largest_weight,
        },
        "units": {
            "returns_and_drawdown": "decimal",
            "volatility": "annualized decimal",
            "var_cvar": "daily decimal loss magnitude",
            "beta_sharpe_sortino": "ratio",
        },
        "data_gap": None,
        "caveat": "Historical estimates are sample-dependent and are not loss forecasts.",
        "not_financial_advice": True,
    }


def _correlation_payload(asset_returns: pd.DataFrame) -> dict[str, Any]:
    if asset_returns.empty or asset_returns.shape[1] < 2:
        return {
            "available": False,
            "assets": list(asset_returns.columns),
            "matrix": [],
            "pairwise_sample_counts": [],
            "method": "pearson",
            "data_gap": "At least two assets with overlapping history are required.",
            "not_financial_advice": True,
        }
    assets = list(asset_returns.columns)
    matrix: list[list[float | None]] = []
    counts: list[list[int]] = []
    for left in assets:
        matrix_row: list[float | None] = []
        count_row: list[int] = []
        for right in assets:
            overlap = pd.concat(
                [
                    asset_returns[left].rename("left"),
                    asset_returns[right].rename("right"),
                ],
                axis=1,
            ).dropna()
            count = len(overlap)
            count_row.append(count)
            matrix_row.append(float(overlap["left"].corr(overlap["right"])) if count >= MIN_CORRELATION_OBSERVATIONS else None)
        counts.append(count_row)
        matrix.append(matrix_row)
    minimum = min(min(row) for row in counts) if counts else 0
    return {
        "available": minimum >= MIN_CORRELATION_OBSERVATIONS,
        "assets": assets,
        "matrix": matrix,
        "pairwise_sample_counts": counts,
        "method": "pearson",
        "minimum_required_samples": MIN_CORRELATION_OBSERVATIONS,
        "minimum_observed_samples": minimum,
        "missing_data_policy": "pairwise complete observations",
        "units": "correlation coefficient",
        "data_gap": None if minimum >= MIN_CORRELATION_OBSERVATIONS else "One or more pairs have insufficient overlap.",
        "caveat": "Correlation is historical, unstable, and not causation.",
        "not_financial_advice": True,
    }


def _factor_payload(
    portfolio_returns: pd.Series,
    price_series: dict[str, pd.Series],
) -> dict[str, Any]:
    proxy_map = {"market": "SPY", "duration": "TLT", "gold": "GLD", "crypto": "BTC-USD"}
    available = {factor: symbol for factor, symbol in proxy_map.items() if symbol in price_series}
    if portfolio_returns.empty or len(available) < 2:
        return {
            "available": False,
            "model": "public_proxy_ols",
            "exposures": [],
            "sample_count": 0,
            "data_gap": "Portfolio returns and at least two public proxy histories are required.",
            "not_financial_advice": True,
        }
    factor_returns = pd.concat(
        {
            factor: price_series[symbol].pct_change(fill_method=None)
            for factor, symbol in available.items()
        },
        axis=1,
    )
    aligned = pd.concat([portfolio_returns.rename("portfolio"), factor_returns], axis=1).dropna(how="any")
    if len(aligned) < MIN_FACTOR_OBSERVATIONS:
        return {
            "available": False,
            "model": "public_proxy_ols",
            "exposures": [],
            "sample_count": len(aligned),
            "data_gap": f"Factor regression requires {MIN_FACTOR_OBSERVATIONS} complete observations.",
            "not_financial_advice": True,
        }
    y = aligned["portfolio"].to_numpy(dtype=float)
    factor_names = list(available)
    x = aligned[factor_names].to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coefficients
    residuals = y - fitted
    total_sum = float(np.sum((y - y.mean()) ** 2))
    residual_sum = float(np.sum(residuals**2))
    r_squared = 1.0 - residual_sum / total_sum if total_sum > 0 else 0.0
    exposures = []
    for index, factor in enumerate(factor_names, start=1):
        symbol = available[factor]
        exposures.append(
            {
                "factor": factor,
                "proxy_symbol": symbol,
                "beta": float(coefficients[index]),
                "annualized_proxy_contribution": float(coefficients[index] * aligned[factor].mean() * ANNUALIZATION),
                "provider": "yfinance" if price_series[symbol].attrs.get("runtime") else "phase5k.fixture",
                "source_url": f"https://finance.yahoo.com/quote/{quote(symbol)}",
                "caveat": "Public asset proxy, not an institutional factor series.",
                "not_financial_advice": True,
            }
        )
    return {
        "available": True,
        "model": "public_proxy_ols",
        "factor_source": "public asset-return proxies",
        "exposures": exposures,
        "sample_count": len(aligned),
        "frequency": "daily",
        "annualization": ANNUALIZATION,
        "alpha_annualized": float(coefficients[0] * ANNUALIZATION),
        "r_squared": float(r_squared),
        "residual_annualized": float(np.mean(residuals) * ANNUALIZATION),
        "unexplained_share_pct": float(max(0.0, 1.0 - r_squared) * 100.0),
        "residual_series": [
            {"date": date.date().isoformat(), "residual_return": float(value)}
            for date, value in zip(aligned.index, residuals)
        ],
        "data_gap": None,
        "caveat": "Proxy OLS exposures are descriptive, may be collinear, and do not establish causality.",
        "not_financial_advice": True,
    }


def _attribution_payload(
    asset_returns: pd.DataFrame,
    portfolio_returns: pd.Series,
    holdings: list[dict[str, Any]],
) -> dict[str, Any]:
    if asset_returns.empty or portfolio_returns.empty:
        return {
            "available": False,
            "return_contribution": [],
            "risk_contribution": [],
            "portfolio_total_return": None,
            "residual": None,
            "reconciled": False,
            "data_gap": "Attribution requires sufficient overlapping return history.",
            "not_financial_advice": True,
        }
    weights = {row["symbol"]: float(row.get("weight") or 0.0) for row in holdings}
    return_rows = []
    arithmetic_sum = 0.0
    for symbol in asset_returns.columns:
        contribution = float((asset_returns[symbol] * weights.get(symbol, 0.0)).sum())
        arithmetic_sum += contribution
        return_rows.append(
            {
                "symbol": symbol,
                "weight": weights.get(symbol, 0.0),
                "arithmetic_asset_return": float(asset_returns[symbol].sum()),
                "return_contribution": contribution,
                "units": "decimal arithmetic contribution",
                "not_financial_advice": True,
            }
        )
    portfolio_total = float((1.0 + portfolio_returns).prod() - 1.0)
    residual = portfolio_total - arithmetic_sum
    risk_frame = compute_risk_contribution(asset_returns, weights)
    risk_rows = [
        {
            "symbol": str(row.get("asset")),
            "weight": _clean_number(row.get("weight")),
            "risk_contribution": float(row.get("risk_contribution") or 0.0),
            "units": "share of portfolio volatility",
            "not_financial_advice": True,
        }
        for row in risk_frame.to_dict(orient="records")
    ]
    reconciled = abs(sum(row["return_contribution"] for row in return_rows) + residual - portfolio_total) < 1e-9
    return {
        "available": True,
        "method": "daily arithmetic contribution with geometric residual",
        "return_contribution": sorted(return_rows, key=lambda row: row["return_contribution"], reverse=True),
        "risk_contribution": sorted(risk_rows, key=lambda row: row["risk_contribution"], reverse=True),
        "portfolio_total_return": portfolio_total,
        "arithmetic_contribution_total": arithmetic_sum,
        "residual": residual,
        "unexplained_share_pct": abs(residual) / max(abs(portfolio_total), 1e-12) * 100.0,
        "reconciled": reconciled,
        "sample_count": len(portfolio_returns),
        "data_gap": None,
        "caveat": "Residual separates geometric compounding from additive arithmetic contribution.",
        "not_financial_advice": True,
    }


def _stress_payload(
    portfolio_returns: pd.Series,
    holdings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in (5, 20):
        if len(portfolio_returns) < window:
            continue
        replay = (1.0 + portfolio_returns).rolling(window).apply(np.prod, raw=True) - 1.0
        replay = replay.dropna()
        if replay.empty:
            continue
        end = replay.idxmin()
        location = portfolio_returns.index.get_loc(end)
        start = portfolio_returns.index[max(0, int(location) - window + 1)]
        rows.append(
            {
                "scenario": f"Worst observed {window}-session window",
                "scenario_type": "historical_replay",
                "estimated_portfolio_impact": float(replay.loc[end]),
                "window": {"start": start.date().isoformat(), "end": end.date().isoformat(), "sessions": window},
                "assumed_shocks": None,
                "sample_count": len(portfolio_returns),
                "caveat": "Observed portfolio replay within the selected source window; not a forecast.",
                "data_gap": None,
                "not_financial_advice": True,
            }
        )
    noncash = [row for row in holdings if not row["cash_flag"] and row.get("weight") is not None]
    symbols = [row["symbol"] for row in noncash]
    weights = [float(row.get("weight") or 0.0) for row in noncash]
    matrix, _ = build_stress_test_matrix(symbols, weights)
    for raw in matrix.to_dict(orient="records"):
        rows.append(
            {
                "scenario": raw.get("scenario"),
                "scenario_type": "deterministic_hypothetical",
                "estimated_portfolio_impact": _clean_number(raw.get("estimated_portfolio_impact")),
                "window": None,
                "assumed_shocks": raw.get("assumed_shocks") or {},
                "largest_contributors": raw.get("largest_contributors") or [],
                "sample_count": None,
                "caveat": raw.get("caveat"),
                "data_gap": "; ".join(raw.get("data_gaps") or []),
                "not_financial_advice": True,
            }
        )
    return rows


def build_portfolio_research_snapshot(
    *,
    portfolio_id: str,
    period: str,
    benchmark: str,
    source_status: str,
    valuation_coverage_pct: float,
    history_coverage_pct: float,
    performance_sample_count: int,
    data_gaps: list[str],
) -> dict[str, Any]:
    safe_context = {
        "report_type": "portfolio_risk_snapshot",
        "portfolio_id": _safe_portfolio_id(portfolio_id),
        "period": period,
        "benchmark": benchmark,
        "source_status": source_status,
        "valuation_coverage_pct": valuation_coverage_pct,
        "history_coverage_pct": history_coverage_pct,
        "performance_sample_count": performance_sample_count,
        "data_gap_count": len(data_gaps),
        "research_only": True,
        "not_financial_advice": True,
    }
    guards = run_research_guard_pipeline(safe_context, _DISCLOSURE)
    return {
        "available": performance_sample_count >= MIN_PERFORMANCE_OBSERVATIONS,
        "report_type": "portfolio_risk_snapshot",
        "generated_at": _FIXTURE_FETCHED_AT if source_status == "fixture" else _now_iso(),
        "persistence": "not_persisted_in_phase_5k",
        "safe_context": safe_context,
        "guard_summary": summarize_guard_results(guards),
        "guards": guards,
        "private_holdings_in_public_report": False,
        "quantities_in_snapshot": False,
        "cost_basis_in_snapshot": False,
        "caveat": "The existing research guard pipeline validates a holdings-free source snapshot. Durable local research memory is Phase 5L.",
    }


def build_portfolio_risk_workstation_contract(
    *,
    portfolio_id: str = "demo-core",
    holdings: Any = None,
    period: str = "1y",
    benchmark: str = "SPY",
    include_runtime: bool = False,
) -> dict[str, Any]:
    portfolio_id = _safe_portfolio_id(portfolio_id)
    period = period if period in {"6mo", "1y", "3y", "5y"} else "1y"
    benchmark = re.sub(r"[^A-Za-z0-9.=_^-]+", "", str(benchmark or "SPY").upper())[:24] or "SPY"
    raw_holdings = build_demo_portfolio_holdings() if holdings is None else holdings
    normalized = normalize_holdings(raw_holdings)
    accepted = normalized["accepted_rows"]
    symbols = [row["symbol"] for row in accepted if not row["cash_flag"]]
    requested_symbols = list(dict.fromkeys([*symbols, benchmark]))

    if include_runtime:
        histories, provider_status = _runtime_histories(requested_symbols, period)
        source_status = str(provider_status.get("status") or "unavailable")
        fetched_at = provider_status.get("fetched_at") or _now_iso()
        provider = str(provider_status.get("provider") or "yfinance")
        source_url = "https://finance.yahoo.com/"
    elif holdings is None:
        histories = _fixture_histories()
        provider_status = {
            "provider": "phase5k.fixture",
            "source": "deterministic fictional portfolio history",
            "source_url": "https://example.test/phase-5k/portfolio-risk",
            "status": "fixture",
            "fetched_at": _FIXTURE_FETCHED_AT,
            "cached": False,
            "coverage": f"{len(histories)}/{len(requested_symbols)} histories",
            "warning": "Deterministic network-free research fixture.",
            "error": None,
        }
        source_status = "fixture"
        fetched_at = _FIXTURE_FETCHED_AT
        provider = "phase5k.fixture"
        source_url = provider_status["source_url"]
    else:
        histories = {}
        provider_status = {
            "provider": "none",
            "source": "local holdings without runtime request",
            "source_url": None,
            "status": "unavailable",
            "fetched_at": _now_iso(),
            "cached": False,
            "coverage": "0 histories",
            "warning": None,
            "error": "Runtime history was not requested for local holdings.",
        }
        source_status = "unavailable"
        fetched_at = provider_status["fetched_at"]
        provider = "none"
        source_url = None

    price_series = {symbol: _history_series(frame) for symbol, frame in histories.items()}
    price_series = {symbol: series for symbol, series in price_series.items() if not series.empty}
    if include_runtime:
        for series in price_series.values():
            series.attrs["runtime"] = True

    valued: list[dict[str, Any]] = []
    for row in accepted:
        is_cash = bool(row["cash_flag"])
        series = price_series.get(row["symbol"], pd.Series(dtype=float))
        price = 1.0 if is_cash else float(series.iloc[-1]) if not series.empty else None
        market_value = float(row["quantity"] * price) if price is not None else None
        cost_value = float(row["quantity"] * row["cost_basis"]) if row.get("cost_basis") is not None else None
        valued.append(
            {
                **row,
                "price": price,
                "valuation_timestamp": fetched_at if price is not None else None,
                "market_value": market_value,
                "cost_value": cost_value,
                "unrealized_change": market_value - cost_value if market_value is not None and cost_value is not None else None,
                "weight": None,
                "price_available": price is not None,
                "history_available": is_cash or row["symbol"] in price_series,
                "provider": "cash_definition" if is_cash else provider,
                "source_url": None if is_cash else f"https://finance.yahoo.com/quote/{quote(row['symbol'])}" if source_url else None,
                "fetched_at": fetched_at if price is not None else None,
                "freshness": "defined" if is_cash else source_status if price is not None else "unavailable",
                "source_status": "defined" if is_cash else source_status if price is not None else "unavailable",
                "confidence": 1.0 if is_cash else 0.82 if price is not None and source_status in {"live/fresh", "cached"} else 0.35 if price is not None else 0.0,
                "caveat": "Cash is defined at one base-currency unit." if is_cash else "Delayed public market history." if include_runtime else "Deterministic fictional fixture price.",
                "data_gap": None if price is not None else "No usable price history; valuation and return contribution are excluded.",
                "not_financial_advice": True,
            }
        )
    known_total = sum(float(row["market_value"]) for row in valued if row.get("market_value") is not None)
    for row in valued:
        row["weight"] = float(row["market_value"]) / known_total if row.get("market_value") is not None and known_total else None

    valuation_available = sum(bool(row.get("price_available")) for row in valued)
    noncash = [row for row in valued if not row["cash_flag"]]
    history_available = sum(bool(row.get("history_available")) for row in noncash)
    valuation_coverage = valuation_available / len(valued) * 100.0 if valued else 0.0
    history_coverage = history_available / len(noncash) * 100.0 if noncash else 0.0
    missing_symbols = [row["symbol"] for row in valued if not row.get("price_available") or (not row["cash_flag"] and not row.get("history_available"))]

    performance, asset_returns, portfolio_returns, _ = _performance_payload(price_series, valued, benchmark)
    risk = _risk_payload(performance, portfolio_returns, valued)
    correlation = _correlation_payload(asset_returns)
    factors = _factor_payload(portfolio_returns, price_series)
    attribution = _attribution_payload(asset_returns, portfolio_returns, valued)
    stress = _stress_payload(portfolio_returns, valued) if not portfolio_returns.empty else []
    gaps = [
        *(f"Rejected holding {row.get('symbol') or row['row_index']}: {', '.join(row['reasons'])}" for row in normalized["rejected_rows"]),
        *(f"Missing valuation/history for {symbol}." for symbol in sorted(set(missing_symbols))),
    ]
    if provider_status.get("error"):
        gaps.append(str(provider_status["error"]))
    if provider_status.get("warning"):
        gaps.append(str(provider_status["warning"]))
    for section in (performance, risk, correlation, factors, attribution):
        if section.get("data_gap"):
            gaps.append(str(section["data_gap"]))

    privacy_class = "deterministic_fictional_demo" if holdings is None else "local_private"
    allocation = {
        "by_asset_class": _allocation_rows(valued, "asset_class"),
        "by_sector": _allocation_rows(valued, "sector"),
        "by_currency": _allocation_rows(valued, "currency"),
        "known_value_total": known_total,
        "weight_total": sum(float(row.get("weight") or 0.0) for row in valued),
        "reconciled": abs(sum(float(row.get("weight") or 0.0) for row in valued) - (1.0 if known_total else 0.0)) < 1e-9,
        "caveat": "Allocation uses known valuations only; missing holdings are excluded and coverage is shown.",
        "not_financial_advice": True,
    }
    live_claimed = source_status in {"live/fresh", "cached", "stale"} and bool(price_series)
    return {
        "portfolio_risk_version": PORTFOLIO_RISK_VERSION,
        "workspace": "portfolio-risk",
        "portfolio": {
            "portfolio_id": portfolio_id,
            "display_name": "Core Multi-Asset Research Demo" if holdings is None else "Local private research portfolio",
            "base_currency": "USD",
            "input_classification": privacy_class,
            "period": period,
            "benchmark": benchmark,
            "external_cash_flows_supplied": False,
            "not_financial_advice": True,
        },
        "holdings": valued,
        "rejected_holdings": normalized["rejected_rows"],
        "allocation": allocation,
        "performance": performance,
        "risk": risk,
        "correlation": correlation,
        "factors": factors,
        "attribution": attribution,
        "stress_tests": stress,
        "source_register": [
            {
                **provider_status,
                "source_status": source_status,
                "row_count": len(price_series),
                "caveat": "Only public symbols are sent to the market-data provider; quantities, costs, names and notes are not transmitted.",
                "data_gap": provider_status.get("error") or provider_status.get("warning"),
                "not_financial_advice": True,
            }
        ],
        "data_gaps": list(dict.fromkeys(gaps)),
        "privacy": {
            "classification": privacy_class,
            "release_safe": holdings is None,
            "symbols_only_provider_requests": True,
            "quantities_in_url": False,
            "cost_basis_in_url": False,
            "external_ai_transmission": False,
            "telemetry_transmission": False,
            "static_fixture_contains_real_holdings": False,
            "local_private_storage_path_exposed": False,
        },
        "readiness": {
            "live_portfolio_claimed": live_claimed,
            "valuation_ready": known_total > 0,
            "performance_ready": bool(performance.get("available")),
            "risk_ready": bool(risk.get("available")),
            "correlation_ready": bool(correlation.get("available")),
            "factor_ready": bool(factors.get("available")),
            "attribution_ready": bool(attribution.get("available")),
            "stress_ready": bool(stress),
            "missing_returns_as_zero": False,
            "cash_return_defined_as_zero": True,
            "recommended_weights_added": False,
            "rebalance_instructions_added": False,
            "broker_execution_added": False,
            "non_advisory": True,
        },
        "summary": {
            "portfolio_id": portfolio_id,
            "holding_count": len(valued),
            "priced_holding_count": valuation_available,
            "history_holding_count": history_available,
            "total_market_value": known_total,
            "valuation_coverage_pct": round(valuation_coverage, 4),
            "history_coverage_pct": round(history_coverage, 4),
            "missing_symbols": sorted(set(missing_symbols)),
            "source_status": source_status if price_series else "unavailable",
            "as_of": fetched_at,
            "performance_sample_count": performance.get("sample_count", 0),
            "base_currency": "USD",
            "not_financial_advice": True,
        },
        "research_snapshot": build_portfolio_research_snapshot(
            portfolio_id=portfolio_id,
            period=period,
            benchmark=benchmark,
            source_status=source_status if price_series else "unavailable",
            valuation_coverage_pct=round(valuation_coverage, 4),
            history_coverage_pct=round(history_coverage, 4),
            performance_sample_count=int(performance.get("sample_count", 0)),
            data_gaps=list(dict.fromkeys(gaps)),
        ),
        "disclosure": _DISCLOSURE,
    }
