from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .portfolio_backtester import compute_backtest_metrics, run_buy_and_hold_backtest, run_rebalanced_backtest
from .strategy_registry import build_strategy_candidate_set, build_strategy_registry


STRATEGY_CAVEAT = "Backtest-ranked bundle for research only. Past performance does not guarantee future results."


def _normalize_returns(returns: Any) -> pd.DataFrame:
    frame = returns.copy() if isinstance(returns, pd.DataFrame) else pd.DataFrame(returns)
    return frame.apply(pd.to_numeric, errors="coerce").dropna(how="all")


def _weights_for_candidate(candidate: dict[str, Any], returns: pd.DataFrame) -> dict[str, float]:
    assets = list(returns.columns)
    if not assets:
        return {}
    method = str(candidate.get("weighting_method", "equal_weight")).lower()
    if method in {"inverse_volatility", "risk_parity_proxy", "defensive_tilt", "volatility_target"}:
        vol = returns.std().replace(0, np.nan)
        inv = 1.0 / vol
        inv = inv.replace([np.inf, -np.inf], np.nan).fillna(inv.median() if inv.notna().any() else 1.0)
        weights = inv / inv.sum() if inv.sum() else pd.Series(1.0 / len(assets), index=assets)
        return weights.to_dict()
    if method in {"signal_rank", "trend_score", "multi_signal_score"} and len(returns) > 20:
        momentum = (1.0 + returns.tail(63).fillna(0.0)).prod() - 1.0
        ranked = momentum.rank(pct=True).clip(lower=0.05)
        weights = ranked / ranked.sum() if ranked.sum() else pd.Series(1.0 / len(assets), index=assets)
        return weights.to_dict()
    return {asset: 1.0 / len(assets) for asset in assets}


def run_strategy_candidate_backtest(
    candidate: dict[str, Any],
    returns: Any,
    *,
    rebalance_frequency: str = "monthly",
    transaction_cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> dict[str, Any]:
    frame = _normalize_returns(returns)
    name = candidate.get("name") or candidate.get("candidate") or "Strategy candidate"
    if frame.empty:
        return {
            "candidate": name,
            "ok": False,
            "returns": pd.Series(dtype=float),
            "weights": {},
            "metrics": {},
            "data_gaps": ["No return history supplied."],
            "caveat": STRATEGY_CAVEAT,
        }
    weights = _weights_for_candidate(candidate, frame)
    run = run_buy_and_hold_backtest(frame, weights, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps) if str(rebalance_frequency).lower() in {"none", "buy_and_hold", ""} else run_rebalanced_backtest(frame, weights, rebalance_frequency=rebalance_frequency, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps)
    metrics = compute_backtest_metrics(run["returns"], turnover=run.get("turnover"), transaction_cost_estimate=run.get("transaction_cost_estimate", 0.0))
    return {
        "candidate": name,
        "ok": True,
        "category": candidate.get("category"),
        "signals_used": candidate.get("signals_used", []),
        "rebalance_rule": rebalance_frequency,
        "risk_controls": candidate.get("risk_controls", []),
        "returns": run["returns"],
        "turnover": run.get("turnover"),
        "weights": weights,
        "weights_timeline": run.get("weights_timeline", pd.DataFrame()),
        "metrics": metrics,
        "data_gaps": candidate.get("data_gaps", []),
        "caveat": STRATEGY_CAVEAT,
    }


def run_all_strategy_backtests(
    returns: Any,
    candidates: list[dict[str, Any]] | pd.DataFrame | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    if candidates is None:
        candidates = build_strategy_registry()
    rows = candidates.to_dict(orient="records") if isinstance(candidates, pd.DataFrame) else list(candidates)
    return [run_strategy_candidate_backtest(candidate, returns, **kwargs) for candidate in rows]


def compare_strategy_backtests(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for result in results:
        metrics = result.get("metrics", {})
        rows.append(
            {
                "candidate": result.get("candidate"),
                "ok": result.get("ok", False),
                "category": result.get("category"),
                "signals_used": ", ".join(result.get("signals_used", [])),
                "cagr": metrics.get("cagr"),
                "annualized_volatility": metrics.get("annualized_volatility"),
                "sharpe": metrics.get("sharpe"),
                "sortino": metrics.get("sortino"),
                "calmar": metrics.get("calmar"),
                "max_drawdown": metrics.get("max_drawdown"),
                "turnover": metrics.get("turnover"),
                "data_gaps": result.get("data_gaps", []),
                "caveat": result.get("caveat", STRATEGY_CAVEAT),
            }
        )
    return pd.DataFrame(rows)


def build_strategy_leaderboard(results: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    frame = results.copy() if isinstance(results, pd.DataFrame) else compare_strategy_backtests(results)
    if frame.empty:
        return frame
    for col in ["sharpe", "sortino", "calmar", "cagr", "max_drawdown", "turnover"]:
        if col not in frame.columns:
            frame[col] = 0.0
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)
    frame["risk_adjusted_score"] = (
        frame["sharpe"].clip(-2, 4) * 24
        + frame["sortino"].clip(-2, 5) * 16
        + frame["calmar"].clip(-2, 5) * 14
        + frame["cagr"].clip(-1, 1) * 25
        - frame["max_drawdown"].abs().clip(0, 1) * 20
        - frame["turnover"].clip(0, 10) * 1.5
    ).clip(0, 100).round(1)
    if "source_confidence" not in frame.columns:
        frame["source_confidence"] = 0.5
    if "factor_coverage_pct" not in frame.columns:
        frame["factor_coverage_pct"] = 0.0
    if "data_quality_penalty" not in frame.columns:
        frame["data_quality_penalty"] = (100 - pd.to_numeric(frame["factor_coverage_pct"], errors="coerce").fillna(0)).clip(0, 100)
    if "overfit_warning" not in frame.columns:
        frame["overfit_warning"] = frame["factor_coverage_pct"].apply(lambda value: "Higher risk" if float(value or 0) < 50 else "Monitor")
    frame["label"] = "Strategy candidate"
    return frame.sort_values("risk_adjusted_score", ascending=False).reset_index(drop=True)


def build_strategy_risk_return_table(results: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    frame = build_strategy_leaderboard(results)
    if frame.empty:
        return frame
    columns = ["candidate", "category", "cagr", "annualized_volatility", "sharpe", "max_drawdown", "risk_adjusted_score", "caveat"]
    return frame[[col for col in columns if col in frame.columns]]


def build_available_strategy_candidates(available_data: set[str] | None = None) -> pd.DataFrame:
    return build_strategy_candidate_set(available_data or {"ticker list", "price history"})


def enrich_strategy_leaderboard_with_factor_backend(leaderboard: pd.DataFrame, factor_matrix: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = leaderboard.copy() if isinstance(leaderboard, pd.DataFrame) else pd.DataFrame(leaderboard)
    if frame.empty or factor_matrix is None or factor_matrix.empty:
        return build_strategy_leaderboard(frame)
    matrix = factor_matrix.rename(columns={"strategy": "candidate"})
    enriched = frame.merge(matrix[["candidate", "factor_coverage_pct", "source_confidence", "data_quality_penalty", "overfit_warning"]], on="candidate", how="left")
    return build_strategy_leaderboard(enriched)
