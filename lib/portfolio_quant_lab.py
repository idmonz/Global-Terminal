from __future__ import annotations

from typing import Any

import pandas as pd

from .alpha_library import (
    compute_low_volatility_signal,
    compute_momentum_signal,
    compute_multi_signal_score,
    compute_trend_signal,
)
from .performance_attribution import build_attribution_report
from .portfolio_backtester import build_backtest_result
from .portfolio_backtester import normalize_portfolio_source_mode
from .portfolio_optimizer import optimize_portfolio_candidates
from .portfolio_state import normalize_portfolio_rows, portfolio_rows_to_weights, portfolio_summary
from .return_forecast import FORECAST_CAVEAT, build_expected_return_distribution
from .openbb_bridge import OPENBB_CAVEAT, is_openbb_installed
from .strategy_backtest_engine import build_strategy_leaderboard, run_all_strategy_backtests
from .strategy_combination_engine import build_strategy_combination_candidates
from .strategy_correlation import build_strategy_correlation_heatmap_payload
from .walk_forward_validator import run_walk_forward_validation
from .oos_validation import compare_is_oos_decay, flag_overfit_risk, split_in_sample_out_of_sample
from .strategy_registry import build_strategy_candidate_set


RESEARCH_DISCLOSURE = "Backtests and model-estimated forward distributions are for research only. They are not financial advice, not predictions, and not recommendations. Past performance does not guarantee future results."


def default_portfolio_rows() -> list[dict[str, Any]]:
    from .portfolio_state import default_portfolio_rows as _default_portfolio_rows

    return _default_portfolio_rows()


def run_buy_and_hold_backtest(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .portfolio_backtester import run_buy_and_hold_backtest as _run_buy_and_hold_backtest

    return _run_buy_and_hold_backtest(*args, **kwargs)


def run_rebalanced_backtest(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .portfolio_backtester import run_rebalanced_backtest as _run_rebalanced_backtest

    return _run_rebalanced_backtest(*args, **kwargs)


def build_strategy_registry() -> list[dict[str, Any]]:
    from .strategy_registry import build_strategy_registry as _build_strategy_registry

    return _build_strategy_registry()


def generate_alpha_combinations(families: list[str] | None = None, *, max_size: int = 3) -> list[dict[str, Any]]:
    from .alpha_library import generate_alpha_combinations as _generate_alpha_combinations

    return _generate_alpha_combinations(families, max_size=max_size)


def build_portfolio_lab_inputs(rows: Any) -> dict[str, Any]:
    frame = normalize_portfolio_rows(rows)
    return {
        "rows": frame,
        "weights": portfolio_rows_to_weights(frame),
        "summary": portfolio_summary(frame),
        "disclosure": RESEARCH_DISCLOSURE,
    }


def build_portfolio_source_status(source_mode: str = "Auto") -> dict[str, Any]:
    mode = normalize_portfolio_source_mode(source_mode)
    installed = is_openbb_installed()
    return {
        "source_mode": mode,
        "openbb_installed": installed,
        "fallback_policy": "native fallback allowed" if mode in {"Auto", "OpenBB preferred"} else "no silent fallback" if mode == "OpenBB only" else "native only",
        "caveat": OPENBB_CAVEAT,
    }


def build_portfolio_factor_inputs(rows: Any, source_mode: str = "auto") -> dict[str, Any]:
    frame = normalize_portfolio_rows(rows)
    weights = portfolio_rows_to_weights(frame)
    return {
        "symbols": list(weights),
        "weights": weights,
        "source_mode": source_mode,
        "factor_inputs": frame.to_dict(orient="records"),
        "caveat": "Factor inputs are research-only and may include proxy coverage.",
    }


def build_strategy_research_payload(returns: Any) -> dict[str, Any]:
    frame = returns.copy() if isinstance(returns, pd.DataFrame) else pd.DataFrame(returns)
    candidates = build_strategy_candidate_set({"ticker list", "price history"} if not frame.empty else {"ticker list"})
    results = run_all_strategy_backtests(frame, candidates)
    leaderboard = build_strategy_leaderboard(results)
    strategy_returns = pd.DataFrame({result["candidate"]: result["returns"] for result in results if result.get("ok") and not result.get("returns", pd.Series(dtype=float)).empty})
    combinations = build_strategy_combination_candidates(strategy_returns)
    correlation = build_strategy_correlation_heatmap_payload(strategy_returns)
    oos_payload = {}
    walk_forward = {"windows": pd.DataFrame(), "metrics": {}, "caveat": "Run a backtest to populate walk-forward validation."}
    if not strategy_returns.empty:
        first = strategy_returns.iloc[:, 0]
        ins, oos = split_in_sample_out_of_sample(first)
        comparison = compare_is_oos_decay(ins, oos)
        oos_payload = {**comparison, "overfit": flag_overfit_risk(comparison)}
        walk_forward = run_walk_forward_validation(first)
    return {
        "results": results,
        "leaderboard": leaderboard,
        "strategy_returns": strategy_returns,
        "combinations": combinations,
        "correlation": correlation,
        "oos": oos_payload,
        "walk_forward": walk_forward,
        "caveat": RESEARCH_DISCLOSURE,
    }


def build_quant_lab_snapshot(rows: Any, price_history: pd.DataFrame | dict[str, Any] | None = None, source_mode: str = "Auto") -> dict[str, Any]:
    inputs = build_portfolio_lab_inputs(rows)
    tickers = list(inputs["weights"])
    backtest, status = build_backtest_result(tickers, inputs["weights"], price_history=price_history, source_mode=source_mode)
    returns = backtest.get("asset_returns", pd.DataFrame())
    alpha_signals = []
    if isinstance(price_history, pd.DataFrame):
        alpha_signals.extend(compute_momentum_signal(price_history))
        alpha_signals.extend(compute_trend_signal(price_history))
        alpha_signals.extend(compute_low_volatility_signal(price_history))
    alpha_score = compute_multi_signal_score(alpha_signals)
    attribution = build_attribution_report(returns, inputs["weights"]) if isinstance(returns, pd.DataFrame) else {}
    forecast = build_expected_return_distribution(backtest.get("portfolio_returns", pd.Series(dtype=float)), horizon=126, simulations=250)
    return {
        **inputs,
        "backtest": backtest,
        "status": status,
        "source_status": build_portfolio_source_status(source_mode),
        "strategy_research": build_strategy_research_payload(returns),
        "strategy_candidates": build_strategy_candidate_set({"ticker list", "price history"}),
        "alpha_signals": pd.DataFrame(alpha_signals),
        "alpha_score": alpha_score,
        "optimizer_candidates": optimize_portfolio_candidates(returns) if isinstance(returns, pd.DataFrame) and not returns.empty else pd.DataFrame(),
        "forecast": forecast,
        "attribution": attribution,
        "forecast_caveat": FORECAST_CAVEAT,
        "disclosure": RESEARCH_DISCLOSURE,
    }


def build_data_status_table(backtest_result: dict[str, Any], status: Any = None) -> pd.DataFrame:
    rows = []
    for asset in backtest_result.get("tickers", []):
        rows.append(
            {
                "asset": asset,
                "available": asset not in backtest_result.get("missing_assets", []),
                "provider": getattr(status, "provider", "portfolio_backtester"),
                "source": getattr(status, "source", "price history"),
                "freshness": status.refreshed_status() if status is not None and hasattr(status, "refreshed_status") else "estimated",
                "data_gap": asset in backtest_result.get("missing_assets", []),
            }
        )
    return pd.DataFrame(rows)


def methodology_notes() -> list[dict[str, str]]:
    return [
        {"section": "Backtesting", "note": "Uses adjusted or close prices where available, aligned by date. Missing non-cash assets are excluded and flagged."},
        {"section": "Alpha Families", "note": "Momentum, trend, low volatility, value, quality, carry, macro, crypto derivatives, and news-aware signals are neutral research scores."},
        {"section": "Optimizers", "note": "Optimizers produce research candidates under no-short defaults and simple weight constraints."},
        {"section": "Forecasts", "note": FORECAST_CAVEAT},
        {"section": "Compliance", "note": RESEARCH_DISCLOSURE},
    ]
