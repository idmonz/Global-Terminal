from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .data_status import combine_results, error_result, ok_result
from .market_data import fetch_many_price_histories
from .openbb_bridge import is_openbb_installed, openbb_available_result
from .openbb_provider_adapter import get_openbb_price_history
from .risk import (
    compute_beta,
    compute_calmar,
    compute_drawdown_series,
    compute_historical_cvar,
    compute_historical_var,
    compute_max_drawdown,
    compute_realized_volatility,
    compute_sortino,
)


CASH_TICKERS = {"CASH", "USD", "CASH_USD"}
PORTFOLIO_SOURCE_MODES = ["Auto", "Native only", "OpenBB preferred", "OpenBB only"]


def normalize_portfolio_source_mode(source_mode: str | None = None) -> str:
    lookup = {mode.lower(): mode for mode in PORTFOLIO_SOURCE_MODES}
    return lookup.get(str(source_mode or "Auto").strip().lower(), "Auto")


def _price_series(frame: pd.DataFrame) -> pd.Series:
    if frame is None or getattr(frame, "empty", True):
        return pd.Series(dtype=float)
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        for field in ["Adj Close", "Close", "adj_close", "close"]:
            if field in data.columns.get_level_values(-1):
                sliced = data.xs(field, axis=1, level=-1)
                return sliced.bfill(axis=1).iloc[:, 0].dropna()
    for column in ["adj_close", "Adj Close", "close", "Close"]:
        if column in data.columns:
            values = data[column]
            if hasattr(values, "columns"):
                values = values.bfill(axis=1).iloc[:, 0]
            return pd.to_numeric(values, errors="coerce").dropna()
    if data.shape[1] == 1:
        return pd.to_numeric(data.iloc[:, 0], errors="coerce").dropna()
    return pd.Series(dtype=float)


def fetch_portfolio_price_history(
    tickers: list[str],
    *,
    start_date: Any = None,
    end_date: Any = None,
    period: str = "5y",
    source_mode: str = "Auto",
) -> tuple[dict[str, pd.DataFrame], object]:
    symbols = [ticker for ticker in tickers if str(ticker).upper() not in CASH_TICKERS]
    mode = normalize_portfolio_source_mode(source_mode)
    openbb_statuses = []
    if mode in {"Auto", "OpenBB preferred", "OpenBB only"}:
        if is_openbb_installed():
            histories = {}
            for symbol in symbols:
                result = get_openbb_price_history(symbol, start_date=start_date, end_date=end_date)
                openbb_statuses.append(result)
                if result.ok and isinstance(result.data, pd.DataFrame) and not result.data.empty:
                    histories[symbol] = result.data
            if histories or mode == "OpenBB only":
                status = combine_results(openbb_statuses, provider="portfolio_backtester", source="OpenBB portfolio price history")
                return histories, status
        else:
            openbb_statuses.append(openbb_available_result())
            if mode == "OpenBB only":
                return {}, openbb_statuses[0]
    histories, status = fetch_many_price_histories(symbols, period=period)
    if openbb_statuses and status is not None:
        if getattr(status, "warning", None):
            status.warning = f"{status.warning}; OpenBB optional path unavailable, native fallback used."
        else:
            status.warning = "OpenBB optional path unavailable, native fallback used."
    if start_date or end_date:
        start = pd.to_datetime(start_date, errors="coerce") if start_date is not None else None
        end = pd.to_datetime(end_date, errors="coerce") if end_date is not None else None
        filtered = {}
        for ticker, frame in histories.items():
            data = frame.copy()
            if "date" in data.columns:
                data["date"] = pd.to_datetime(data["date"], errors="coerce")
                mask = pd.Series(True, index=data.index)
                if start is not None and pd.notna(start):
                    mask &= data["date"] >= start
                if end is not None and pd.notna(end):
                    mask &= data["date"] <= end
                data = data.loc[mask]
            filtered[ticker] = data
        histories = filtered
    return histories, status


def align_price_history(price_history: dict[str, Any] | pd.DataFrame, *, cash_tickers: list[str] | None = None) -> pd.DataFrame:
    if isinstance(price_history, pd.DataFrame):
        prices = price_history.copy()
        if "date" in prices.columns:
            prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
            prices = prices.set_index("date")
        return prices.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    series = {}
    for ticker, frame in (price_history or {}).items():
        ticker = str(ticker).upper()
        if ticker in CASH_TICKERS:
            continue
        values = _price_series(frame)
        if not values.empty:
            values.index = pd.to_datetime(values.index, errors="coerce")
            series[ticker] = values
    prices = pd.DataFrame(series).sort_index().dropna(how="all")
    for ticker in cash_tickers or []:
        if str(ticker).upper() in CASH_TICKERS and not prices.empty:
            prices[str(ticker).upper()] = 1.0
    return prices


def compute_asset_returns(prices: pd.DataFrame) -> pd.DataFrame:
    if prices is None or prices.empty:
        return pd.DataFrame()
    returns = prices.sort_index().pct_change()
    for column in returns.columns:
        if str(column).upper() in CASH_TICKERS:
            returns[column] = 0.0
    return returns.replace([np.inf, -np.inf], np.nan).dropna(how="all")


def compute_portfolio_returns(returns: pd.DataFrame, weights: dict[str, float] | list[float]) -> pd.Series:
    if returns is None or returns.empty:
        return pd.Series(dtype=float, name="portfolio")
    if isinstance(weights, dict):
        available = [asset for asset in weights if asset in returns.columns]
        if not available:
            return pd.Series(dtype=float, name="portfolio")
        vector = np.array([weights[asset] for asset in available], dtype=float)
        if vector.sum() > 0:
            vector = vector / vector.sum()
        frame = returns[available].dropna(how="all").fillna(0.0)
    else:
        frame = returns.dropna(how="all").fillna(0.0)
        vector = np.array(weights, dtype=float)[: len(frame.columns)]
        if len(vector) != len(frame.columns):
            vector = np.repeat(1.0 / len(frame.columns), len(frame.columns))
        if vector.sum() > 0:
            vector = vector / vector.sum()
    return pd.Series(frame.to_numpy() @ vector, index=frame.index, name="portfolio")


def apply_transaction_costs(portfolio_returns: pd.Series, turnover: pd.Series | None = None, *, transaction_cost_bps: float = 0.0, slippage_bps: float = 0.0) -> tuple[pd.Series, float]:
    series = pd.to_numeric(pd.Series(portfolio_returns), errors="coerce").fillna(0.0)
    if turnover is None:
        turnover = pd.Series(0.0, index=series.index)
    turnover = pd.Series(turnover, index=series.index).fillna(0.0)
    cost_rate = (float(transaction_cost_bps) + float(slippage_bps)) / 10000.0
    costs = turnover * cost_rate
    adjusted = (series - costs).rename(series.name or "portfolio")
    return adjusted, float(costs.sum())


def apply_rebalancing(
    returns: pd.DataFrame,
    weights: dict[str, float],
    *,
    rebalance_frequency: str = "monthly",
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    if returns is None or returns.empty:
        return pd.Series(dtype=float, name="portfolio"), pd.Series(dtype=float), pd.DataFrame()
    available = [asset for asset in weights if asset in returns.columns]
    frame = returns[available].fillna(0.0)
    target = np.array([weights[asset] for asset in available], dtype=float)
    target = target / target.sum() if target.sum() else np.repeat(1.0 / len(available), len(available))
    if str(rebalance_frequency).lower() in {"none", "buy_and_hold", ""}:
        result = compute_portfolio_returns(frame, dict(zip(available, target)))
        return result, pd.Series(0.0, index=result.index), pd.DataFrame(target, index=available, columns=[frame.index[0] if len(frame.index) else "start"]).T
    freq_map = {"monthly": "ME", "quarterly": "QE", "semiannual": "2QE", "annual": "YE"}
    pandas_freq = freq_map.get(str(rebalance_frequency).lower(), "ME")
    rebalance_dates = set(frame.resample(pandas_freq).last().index)
    current = target.copy()
    portfolio_returns = []
    turnover = []
    weight_rows = []
    for date, row in frame.iterrows():
        if date in rebalance_dates:
            turnover_value = float(np.abs(current - target).sum() / 2.0)
            current = target.copy()
        else:
            turnover_value = 0.0
        day_return = float(np.dot(current, row.to_numpy()))
        portfolio_returns.append((date, day_return))
        turnover.append((date, turnover_value))
        drift = current * (1.0 + row.to_numpy())
        current = drift / drift.sum() if drift.sum() else target.copy()
        weight_rows.append({"date": date, **dict(zip(available, current))})
    return (
        pd.Series(dict(portfolio_returns), name="portfolio").sort_index(),
        pd.Series(dict(turnover)).sort_index(),
        pd.DataFrame(weight_rows).set_index("date") if weight_rows else pd.DataFrame(),
    )


def run_buy_and_hold_backtest(
    returns: pd.DataFrame,
    weights: dict[str, float],
    *,
    transaction_cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> dict[str, Any]:
    portfolio_returns = compute_portfolio_returns(returns, weights)
    initial_turnover = pd.Series(0.0, index=portfolio_returns.index)
    if not initial_turnover.empty:
        initial_turnover.iloc[0] = 1.0
    adjusted, cost = apply_transaction_costs(portfolio_returns, initial_turnover, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps)
    return {"returns": adjusted, "turnover": initial_turnover, "transaction_cost_estimate": cost, "weights_timeline": pd.DataFrame()}


def run_rebalanced_backtest(
    returns: pd.DataFrame,
    weights: dict[str, float],
    *,
    rebalance_frequency: str = "monthly",
    transaction_cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> dict[str, Any]:
    portfolio_returns, turnover, weights_timeline = apply_rebalancing(returns, weights, rebalance_frequency=rebalance_frequency)
    adjusted, cost = apply_transaction_costs(portfolio_returns, turnover, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps)
    return {"returns": adjusted, "turnover": turnover, "transaction_cost_estimate": cost, "weights_timeline": weights_timeline}


def run_strategy_backtest(returns: pd.DataFrame, strategy_weights: dict[str, float], **kwargs) -> dict[str, Any]:
    return run_rebalanced_backtest(returns, strategy_weights, **kwargs)


def _cagr(returns: pd.Series, annualization: int = 252) -> float:
    returns = pd.to_numeric(pd.Series(returns), errors="coerce").dropna()
    if returns.empty:
        return float("nan")
    years = len(returns) / annualization
    if years <= 0:
        return float("nan")
    return float((1.0 + returns).prod() ** (1.0 / years) - 1.0)


def compute_backtest_metrics(
    portfolio_returns: pd.Series,
    *,
    benchmark_returns: pd.Series | None = None,
    turnover: pd.Series | None = None,
    transaction_cost_estimate: float = 0.0,
    annualization: int = 252,
) -> dict[str, float]:
    returns = pd.to_numeric(pd.Series(portfolio_returns), errors="coerce").dropna()
    if returns.empty:
        return {}
    excess = returns
    volatility = compute_realized_volatility(returns, annualization)
    sharpe = float(returns.mean() * annualization / volatility) if volatility and not pd.isna(volatility) else float("nan")
    monthly = (1 + returns).resample("ME").prod() - 1 if isinstance(returns.index, pd.DatetimeIndex) else returns
    metrics = {
        "cumulative_return": float((1.0 + returns).prod() - 1.0),
        "cagr": _cagr(returns, annualization),
        "annualized_volatility": volatility,
        "sharpe": sharpe,
        "sortino": compute_sortino(returns, annualization=annualization),
        "calmar": compute_calmar(returns, annualization=annualization),
        "max_drawdown": compute_max_drawdown(returns),
        "var_95": compute_historical_var(returns, 0.95),
        "cvar_95": compute_historical_cvar(returns, 0.95),
        "win_rate": float((returns > 0).mean()),
        "best_month": float(monthly.max()) if len(monthly) else float("nan"),
        "worst_month": float(monthly.min()) if len(monthly) else float("nan"),
        "positive_month_ratio": float((monthly > 0).mean()) if len(monthly) else float("nan"),
        "turnover": float(pd.Series(turnover).fillna(0).sum()) if turnover is not None else 0.0,
        "transaction_cost_estimate": float(transaction_cost_estimate),
    }
    if benchmark_returns is not None and not pd.Series(benchmark_returns).dropna().empty:
        aligned = pd.concat([returns, pd.Series(benchmark_returns).rename("benchmark")], axis=1).dropna()
        if not aligned.empty:
            beta = compute_beta(aligned.iloc[:, 0], aligned.iloc[:, 1])
            active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
            tracking_error = float(active.std() * math.sqrt(annualization))
            metrics.update(
                {
                    "beta_vs_benchmark": beta,
                    "regression_alpha_estimate": float((aligned.iloc[:, 0].mean() - beta * aligned.iloc[:, 1].mean()) * annualization) if pd.notna(beta) else float("nan"),
                    "tracking_error": tracking_error,
                    "information_ratio": float(active.mean() * annualization / tracking_error) if tracking_error else float("nan"),
                }
            )
    else:
        metrics.update({"beta_vs_benchmark": float("nan"), "regression_alpha_estimate": float("nan"), "tracking_error": float("nan"), "information_ratio": float("nan")})
    return metrics


def build_backtest_result(
    tickers: list[str],
    weights: dict[str, float],
    *,
    price_history: dict[str, Any] | pd.DataFrame | None = None,
    start_date: Any = None,
    end_date: Any = None,
    benchmark: str | None = None,
    rebalance_frequency: str = "none",
    transaction_cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
    cash_rate_proxy: float | None = None,
    base_currency: str | None = None,
    source_mode: str = "Auto",
) -> tuple[dict[str, Any], object]:
    cash_tickers = [ticker for ticker in tickers if str(ticker).upper() in CASH_TICKERS]
    status = None
    if price_history is None:
        price_history, status = fetch_portfolio_price_history(tickers, start_date=start_date, end_date=end_date, source_mode=source_mode)
    history_input = price_history if price_history is not None else {}
    prices = align_price_history(history_input, cash_tickers=cash_tickers)
    missing = [ticker for ticker in tickers if str(ticker).upper() not in CASH_TICKERS and ticker not in prices.columns]
    if prices.empty:
        return {"data_gaps": ["No usable price history."], "missing_assets": missing}, error_result(source="portfolio backtest", provider="portfolio_backtester", error="No usable price history.", warning="Missing assets are not treated as zero return.")
    returns = compute_asset_returns(prices)
    if cash_rate_proxy is not None:
        daily_cash = float(cash_rate_proxy) / 252.0
        for ticker in cash_tickers:
            returns[ticker] = daily_cash
    if str(rebalance_frequency).lower() in {"none", "buy_and_hold", ""}:
        run = run_buy_and_hold_backtest(returns, weights, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps)
    else:
        run = run_rebalanced_backtest(returns, weights, rebalance_frequency=rebalance_frequency, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps)
    benchmark_returns = returns[benchmark] if benchmark and benchmark in returns.columns else None
    metrics = compute_backtest_metrics(run["returns"], benchmark_returns=benchmark_returns, turnover=run["turnover"], transaction_cost_estimate=run["transaction_cost_estimate"])
    equity_curve = (1.0 + run["returns"]).cumprod().rename("equity_curve")
    drawdown = compute_drawdown_series(equity_curve).rename("drawdown")
    result = {
        "tickers": tickers,
        "weights": weights,
        "base_currency": base_currency or "USD",
        "prices": prices,
        "asset_returns": returns,
        "portfolio_returns": run["returns"],
        "equity_curve": equity_curve,
        "drawdown": drawdown,
        "turnover": run["turnover"],
        "weights_timeline": run["weights_timeline"],
        "metrics": metrics,
        "missing_assets": missing,
        "data_gaps": [f"Missing price history for: {', '.join(missing)}"] if missing else [],
        "caveat": "Backtests are historical research estimates and do not guarantee future results.",
    }
    warning = "Missing assets are excluded from return math, not assumed to be zero return." if missing else getattr(status, "warning", None)
    return result, ok_result(result, source="portfolio backtest", provider="portfolio_backtester", warning=warning, is_estimated=True, coverage=f"{len(prices.columns)}/{len(tickers)} assets")
