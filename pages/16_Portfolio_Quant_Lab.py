from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from lib.alpha_library import (
    compute_low_volatility_signal,
    compute_momentum_signal,
    compute_multi_signal_score,
    compute_trend_signal,
)
from lib.alpha_strategy_workbench import build_alpha_strategy_workbench
from lib.alpha_combination_search import build_alpha_combination_cards, run_alpha_combination_search
from lib.performance_attribution import build_attribution_report
from lib.heatmap_layout_engine import build_factor_exposure_heatmap, build_heatmap_layout, build_portfolio_heatmap, build_portfolio_risk_heatmap
from lib.portfolio_backtester import build_backtest_result
from lib.portfolio_optimizer import (
    equal_weight,
    inverse_volatility_weight,
    optimize_portfolio_candidates,
)
from lib.portfolio_quant_lab import RESEARCH_DISCLOSURE, build_data_status_table, build_portfolio_source_status, build_strategy_research_payload, methodology_notes
from lib.regime_performance_engine import build_regime_performance_summary, build_regime_performance_table
from lib.strategy_data_quality import build_strategy_data_quality_cards, compute_strategy_data_quality_score, detect_strategy_data_gaps
from lib.strategy_ensemble_engine import build_strategy_ensemble_report
from lib.strategy_risk_budgeting import build_strategy_risk_budget
from lib.strategy_visual_lab import strategy_ensemble_drawdown_chart, strategy_ensemble_equity_curve, strategy_regime_heatmap, strategy_risk_budget_chart
from lib.portfolio_state import (
    default_portfolio_rows,
    list_saved_portfolios,
    load_portfolio_from_json,
    normalize_portfolio_rows,
    portfolio_rows_to_weights,
    portfolio_summary,
    rebalance_weights,
    save_portfolio_to_json,
)
from lib.portfolio_visuals import (
    allocation_pie_or_bar,
    correlation_heatmap,
    drawdown_chart,
    equity_curve_chart,
    factor_exposure_radar_or_bar,
    forecast_distribution_chart,
    monthly_returns_heatmap,
    return_contribution_chart,
    risk_contribution_chart,
    rolling_sharpe_chart,
    rolling_volatility_chart,
    strategy_leaderboard_chart,
    turnover_chart,
)
from lib.portfolio_factor_router import build_factor_data_gap_report, build_portfolio_factor_profile, build_strategy_factor_matrix
from lib.stress_tests import build_stress_test_matrix
from lib.terminal_ui import goal10_summary_strip, intelligence_card, metric_strip, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="Portfolio Quant Lab", layout="wide")


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


terminal_page_header(
    st,
    "Portfolio Quant Lab",
    "Research portfolios, strategy candidates, historical backtests, attribution, and model-estimated forward distributions.",
    meta=[
        {"label": "Mode", "value": "Research only", "tone": "info"},
        {"label": "Data", "value": "Optional public providers", "tone": "estimated"},
        {"label": "OpenBB", "value": "optional backend", "tone": "estimated"},
        {"label": "Advice", "value": "None", "tone": "watch"},
    ],
)
st.caption(RESEARCH_DISCLOSURE)
goal10_summary_strip(st, workspace="Portfolio Quant Lab", risk_state="watch", data_confidence="backtest/source labeled", provider_status="factor backend optional", caveat=RESEARCH_DISCLOSURE)

if "portfolio_quant_rows" not in st.session_state:
    st.session_state["portfolio_quant_rows"] = normalize_portfolio_rows(default_portfolio_rows())
if "portfolio_quant_backtest" not in st.session_state:
    st.session_state["portfolio_quant_backtest"] = None
if "portfolio_quant_status" not in st.session_state:
    st.session_state["portfolio_quant_status"] = None
if "portfolio_factor_profile" not in st.session_state:
    st.session_state["portfolio_factor_profile"] = None
if "portfolio_factor_matrix" not in st.session_state:
    st.session_state["portfolio_factor_matrix"] = None
if "portfolio_factor_gaps" not in st.session_state:
    st.session_state["portfolio_factor_gaps"] = None

with st.sidebar:
    st.subheader("Lab Controls")
    benchmark = st.selectbox("Benchmark", ["SPY", "QQQ", "ACWI", "BTC-USD", "None"], index=0)
    today = date.today()
    start_date = st.date_input("Start date", today - timedelta(days=365 * 3))
    end_date = st.date_input("End date", today)
    source_mode = st.selectbox("Source mode", ["Auto", "Native only", "OpenBB preferred", "OpenBB only"], index=0)
    factor_backend = st.selectbox("Factor Backend", ["auto", "native_only", "openbb_preferred"], index=0)
    rebalance_frequency = st.selectbox("Rebalance", ["none", "monthly", "quarterly", "semiannual", "annual"], index=1)
    transaction_cost_bps = st.number_input("Transaction cost bps", min_value=0.0, max_value=250.0, value=2.0, step=0.5)
    slippage_bps = st.number_input("Slippage bps", min_value=0.0, max_value=250.0, value=1.0, step=0.5)

tabs = st.tabs(
    [
        "Portfolio Builder",
        "Backtest",
        "Strategy Research Engine",
        "Alpha Strategy Workbench",
        "Optimizer",
        "Forecast Lab",
        "Attribution",
        "Risk & Stress",
        "Data Status",
        "Methodology",
        "Walk-Forward / OOS",
        "Strategy Correlation",
        "Factor Exposure",
        "Alpha Combination Search",
        "Ensemble Builder",
        "Regime Performance",
        "Risk Budgeting",
        "Data Quality",
    ]
)

with tabs[0]:
    terminal_section_header(st, "Portfolio Builder", "Editable research portfolio state")
    rows = st.data_editor(
        st.session_state["portfolio_quant_rows"],
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="portfolio_quant_editor",
    )
    st.session_state["portfolio_quant_rows"] = normalize_portfolio_rows(rows)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Equal weight", use_container_width=True):
            st.session_state["portfolio_quant_rows"] = rebalance_weights(st.session_state["portfolio_quant_rows"], method="equal")
            st.rerun()
    with col2:
        if st.button("Normalize weights", use_container_width=True):
            st.session_state["portfolio_quant_rows"] = rebalance_weights(st.session_state["portfolio_quant_rows"], method="normalize")
            st.rerun()
    with col3:
        if st.button("Inverse vol weights", use_container_width=True):
            st.info("Run a backtest first so the lab can use realized volatility.")
    with col4:
        portfolio_name = st.text_input("Save name", "Research Portfolio")
    save_col, load_col = st.columns(2)
    with save_col:
        if st.button("Save portfolio", use_container_width=True):
            save_portfolio_to_json(portfolio_name, st.session_state["portfolio_quant_rows"])
            st.success("Portfolio saved to gitignored private storage.")
    with load_col:
        saved = list_saved_portfolios()
        selected = st.selectbox("Saved portfolios", saved or ["No saved portfolios"])
        if st.button("Load portfolio", use_container_width=True) and saved:
            st.session_state["portfolio_quant_rows"] = load_portfolio_from_json(selected)
            st.rerun()
    summary = portfolio_summary(st.session_state["portfolio_quant_rows"])
    metric_strip(
        st,
        [
            {"label": "Assets", "value": summary["asset_count"], "delta": "included", "freshness": "estimated"},
            {"label": "Weight Sum", "value": summary["weight_sum"], "delta": "normalized", "freshness": "estimated"},
            {"label": "Cash Weight", "value": summary["cash_weight"], "delta": "portfolio", "freshness": "estimated"},
            {"label": "Largest Weight", "value": summary["largest_weight"], "delta": "concentration", "freshness": "estimated"},
        ],
    )
    weights = portfolio_rows_to_weights(st.session_state["portfolio_quant_rows"])
    st.plotly_chart(allocation_pie_or_bar(weights), use_container_width=True)
    heatmap_rows = [
        {
            "symbol": ticker,
            "portfolio_bucket": "Portfolio",
            "weight": weight,
            "portfolio_weight": weight,
            "daily_return": 0,
            "source": "session portfolio",
            "freshness": "estimated",
            "tile_type": "portfolio",
        }
        for ticker, weight in weights.items()
    ]
    terminal_section_header(st, "Portfolio Heatmaps", "Exposure and data-quality heatmaps use the current session portfolio.")
    h1, h2 = st.columns(2)
    with h1:
        render_table(st, build_portfolio_heatmap(heatmap_rows)["table"])
    with h2:
        render_table(st, build_heatmap_layout([{**row, "quality_score": 85, "data_quality": "estimated"} for row in heatmap_rows], title="Portfolio Data Quality Heatmap", size_mode="portfolio_weight", color_mode="data_quality", group_mode="portfolio_bucket")["table"])

with tabs[1]:
    terminal_section_header(st, "Backtest", "Historical portfolio research run")
    weights = portfolio_rows_to_weights(st.session_state["portfolio_quant_rows"])
    tickers = list(weights)
    if st.button("Run backtest", type="primary"):
        result, status = build_backtest_result(
            tickers,
            weights,
            start_date=start_date,
            end_date=end_date,
            benchmark=None if benchmark == "None" else benchmark,
            rebalance_frequency=rebalance_frequency,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
            source_mode=source_mode,
        )
        st.session_state["portfolio_quant_backtest"] = result
        st.session_state["portfolio_quant_status"] = status
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        render_status(st, st.session_state["portfolio_quant_status"])
        metrics = result.get("metrics", {})
        metric_strip(
            st,
            [
                {"label": "Cumulative Return", "value": metrics.get("cumulative_return"), "delta": "historical", "freshness": "estimated"},
                {"label": "CAGR", "value": metrics.get("cagr"), "delta": "historical", "freshness": "estimated"},
                {"label": "Volatility", "value": metrics.get("annualized_volatility"), "delta": "annualized", "freshness": "estimated"},
                {"label": "Max Drawdown", "value": metrics.get("max_drawdown"), "delta": "historical", "freshness": "estimated"},
            ],
        )
        c1, c2 = st.columns(2)
        c1.plotly_chart(equity_curve_chart(result["equity_curve"]), use_container_width=True)
        c2.plotly_chart(drawdown_chart(result["drawdown"]), use_container_width=True)
        c3, c4 = st.columns(2)
        c3.plotly_chart(monthly_returns_heatmap(result["portfolio_returns"]), use_container_width=True)
        c4.plotly_chart(correlation_heatmap(result["asset_returns"]), use_container_width=True)
        c5, c6 = st.columns(2)
        c5.plotly_chart(rolling_sharpe_chart(result["portfolio_returns"]), use_container_width=True)
        c6.plotly_chart(rolling_volatility_chart(result["portfolio_returns"]), use_container_width=True)
        with st.expander("Backtest metrics"):
            render_table(st, pd.DataFrame([metrics]))
    else:
        st.info("Run a backtest to populate historical charts and metrics.")

with tabs[2]:
    terminal_section_header(st, "Strategy Research Engine", "Backtest-ranked strategy candidates and risk-return comparison")
    from lib.strategy_registry import build_strategy_candidate_set, rank_strategy_candidates_by_risk_adjusted_score

    available = {"ticker list"}
    if st.session_state["portfolio_quant_backtest"]:
        available.add("price history")
    candidates = build_strategy_candidate_set(available)
    render_table(st, candidates[["name", "category", "weighting_method", "rebalance_frequency", "is_available", "data_gaps"]])
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        ranked = research["leaderboard"]
        render_table(st, ranked)
        st.plotly_chart(strategy_leaderboard_chart(ranked), use_container_width=True)
        if not research["strategy_returns"].empty:
            c1, c2 = st.columns(2)
            c1.plotly_chart(equity_curve_chart((1 + research["strategy_returns"].fillna(0)).cumprod().iloc[:, 0]), use_container_width=True)
            c2.plotly_chart(drawdown_chart((1 + research["strategy_returns"].fillna(0)).cumprod().iloc[:, 0] / (1 + research["strategy_returns"].fillna(0)).cumprod().iloc[:, 0].cummax() - 1), use_container_width=True)
    else:
        sample = pd.DataFrame(
            [
                {"candidate": row["name"], "sharpe": 0.0, "calmar": 0.0, "cagr": 0.0, "max_drawdown": 0.0}
                for _, row in candidates.head(8).iterrows()
            ]
        )
        ranked = rank_strategy_candidates_by_risk_adjusted_score(sample)
        st.plotly_chart(strategy_leaderboard_chart(ranked), use_container_width=True)
        st.caption("Run a backtest to generate comparable strategy candidate rankings.")

with tabs[3]:
    terminal_section_header(st, "Alpha Strategy Workbench", "Dense research view for signals, strategy candidates, combinations, validation, and source quality.")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        workbench = build_alpha_strategy_workbench(research, st.session_state.get("portfolio_factor_profile"))
        metric_strip(st, workbench["metrics"], columns=5)
        card_cols = st.columns(3)
        for idx, card in enumerate(workbench["cards"]):
            with card_cols[idx % len(card_cols)]:
                intelligence_card(
                    st,
                    title=card["title"],
                    summary=card["summary"],
                    severity=card["severity"],
                    tags=card["tags"],
                    source=card["source"],
                    freshness=card["freshness"],
                )
        workbench_tabs = st.tabs(["Ranked Candidates", "Validation", "Ensemble", "Combinations", "Signals"])
        with workbench_tabs[0]:
            render_table(st, workbench["leaderboard"])
        with workbench_tabs[1]:
            render_table(st, workbench["validation"])
        with workbench_tabs[2]:
            render_table(st, workbench["ensemble_weights"])
            if not workbench["ensemble_returns"].empty:
                st.plotly_chart(equity_curve_chart((1 + workbench["ensemble_returns"].fillna(0)).cumprod()), use_container_width=True)
        with workbench_tabs[3]:
            render_table(st, workbench["combinations"])
        with workbench_tabs[4]:
            prices = result["prices"]
            signals = compute_momentum_signal(prices) + compute_trend_signal(prices) + compute_low_volatility_signal(prices)
            signal_frame = pd.DataFrame(signals)
            score_frame = compute_multi_signal_score(signals)
            render_table(st, score_frame)
            with st.expander("Signal evidence"):
                render_table(st, signal_frame)
        st.caption(workbench["caveat"])
    else:
        st.info("Run a backtest to calculate price-based alpha signals and strategy workbench diagnostics.")

with tabs[4]:
    terminal_section_header(st, "Optimizer", "Research candidates under no-short default constraints")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        returns = result["asset_returns"]
        candidates = optimize_portfolio_candidates(returns)
        render_table(st, candidates[["candidate", "max_weight", "cash_weight", "caveat"]])
        for _, row in candidates.head(3).iterrows():
            st.plotly_chart(allocation_pie_or_bar(row["weights"]), use_container_width=True)
    else:
        weights = portfolio_rows_to_weights(st.session_state["portfolio_quant_rows"])
        render_table(st, pd.DataFrame([{"candidate": "Equal Weight", "weights": equal_weight(list(weights)), "caveat": "Run a backtest for volatility-aware candidates."}]))

with tabs[5]:
    terminal_section_header(st, "Forecast Lab", "Model-estimated forward distributions")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        from lib.return_forecast import build_expected_return_distribution

        method = st.selectbox("Distribution method", ["bootstrap", "monte_carlo"], index=0)
        horizon = st.slider("Horizon days", min_value=21, max_value=504, value=126, step=21)
        forecast = build_expected_return_distribution(result["portfolio_returns"], method=method, horizon=horizon, simulations=500)
        st.plotly_chart(forecast_distribution_chart(forecast), use_container_width=True)
        render_table(st, pd.DataFrame([{k: v for k, v in forecast.items() if k != "paths"}]))
    else:
        st.info("Run a backtest to build model-estimated forward distributions.")

with tabs[6]:
    terminal_section_header(st, "Attribution", "Historical/proxy return and risk contribution")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        weights = result["weights"]
        report = build_attribution_report(result["asset_returns"], weights, weights_timeline=result.get("weights_timeline"))
        c1, c2 = st.columns(2)
        c1.plotly_chart(return_contribution_chart(report["return_contribution"]), use_container_width=True)
        c2.plotly_chart(risk_contribution_chart(report["risk_contribution"]), use_container_width=True)
        risk_rows = [
            {
                "symbol": row.get("ticker") or row.get("asset") or row.get("symbol"),
                "portfolio_bucket": "Risk contribution",
                "risk_contribution": row.get("risk_contribution") or row.get("contribution") or row.get("value") or 1,
                "risk_score": abs(_safe_float(row.get("risk_contribution") or row.get("contribution") or row.get("value") or 0)) * 100,
                "source": "performance attribution",
                "freshness": "estimated",
                "tile_type": "portfolio",
            }
            for row in report["risk_contribution"].to_dict(orient="records")
        ] if hasattr(report.get("risk_contribution"), "to_dict") else []
        render_table(st, build_portfolio_risk_heatmap(risk_rows)["table"])
        render_table(st, report["drawdown_contribution"])
        st.plotly_chart(turnover_chart(report["turnover"].set_index("date")["turnover"] if not report["turnover"].empty else pd.Series(dtype=float)), use_container_width=True)
        st.plotly_chart(factor_exposure_radar_or_bar(pd.DataFrame()), use_container_width=True)
    else:
        st.info("Run a backtest to populate attribution.")

with tabs[7]:
    terminal_section_header(st, "Risk & Stress", "Scenario estimates using the existing stress engine")
    weights = portfolio_rows_to_weights(st.session_state["portfolio_quant_rows"])
    stress, status = build_stress_test_matrix(list(weights), list(weights.values()))
    render_status(st, status)
    render_table(st, stress[["scenario", "estimated_portfolio_impact", "largest_contributors", "caveat", "data_gaps"]])

with tabs[8]:
    terminal_section_header(st, "Data Status", "Price availability and source state")
    render_table(st, pd.DataFrame([build_portfolio_source_status(source_mode)]))
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        render_table(st, build_data_status_table(result, st.session_state["portfolio_quant_status"]))
    else:
        rows = normalize_portfolio_rows(st.session_state["portfolio_quant_rows"])
        render_table(st, rows[["ticker", "asset_class", "region", "currency", "include", "notes"]])

with tabs[9]:
    terminal_section_header(st, "Methodology", "Assumptions, limitations, and caveats")
    render_table(st, pd.DataFrame(methodology_notes()))

with tabs[10]:
    terminal_section_header(st, "Walk-Forward / OOS", "Rolling validation, IS vs OOS comparison, and overfit warning payloads")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        walk = research["walk_forward"]
        render_table(st, walk.get("windows", pd.DataFrame()))
        st.json(walk.get("metrics", {}))
        st.json(research.get("oos", {}))
    else:
        st.info("Run a backtest to populate walk-forward and OOS diagnostics.")

with tabs[11]:
    terminal_section_header(st, "Strategy Correlation", "Strategy return and drawdown correlation for ensemble diversification research")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        corr = research["correlation"]
        st.plotly_chart(correlation_heatmap(corr["return_correlation"]), use_container_width=True)
        st.plotly_chart(correlation_heatmap(corr["drawdown_correlation"]), use_container_width=True)
        render_table(st, corr["clusters"])
        st.caption(corr["caveat"])
    else:
        st.info("Run a backtest to populate strategy correlation.")

with tabs[12]:
    terminal_section_header(st, "Factor Exposure", "Unified factor backend with source confidence, coverage, and data quality penalty")
    result = st.session_state["portfolio_quant_backtest"]
    if st.button("Run factor backend", key="run_portfolio_factor_backend"):
        st.session_state["portfolio_factor_profile"] = build_portfolio_factor_profile(st.session_state["portfolio_quant_rows"], source_mode=factor_backend)
        st.session_state["portfolio_factor_matrix"] = build_strategy_factor_matrix(st.session_state["portfolio_quant_rows"], source_mode=factor_backend)
        st.session_state["portfolio_factor_gaps"] = build_factor_data_gap_report(st.session_state["portfolio_quant_rows"], source_mode=factor_backend)
    factor_profile = st.session_state["portfolio_factor_profile"]
    if factor_profile:
        metric_strip(
            st,
            [
                {"label": "Factor Coverage", "value": factor_profile.get("factor_coverage_pct"), "delta": "%", "freshness": "estimated"},
                {"label": "Source Confidence", "value": factor_profile.get("source_confidence"), "delta": "score", "freshness": "estimated"},
                {"label": "Data Quality Penalty", "value": max(0, 100 - factor_profile.get("factor_coverage_pct", 0)), "delta": "lower is better", "freshness": "estimated"},
                {"label": "Symbols", "value": len(factor_profile.get("symbols", [])), "delta": factor_backend, "freshness": "estimated"},
            ],
        )
        render_table(st, factor_profile["factors"]["table"])
        render_table(st, st.session_state["portfolio_factor_matrix"])
        render_table(st, st.session_state["portfolio_factor_gaps"])
        factor_rows = []
        factor_table = factor_profile["factors"]["table"]
        if hasattr(factor_table, "to_dict"):
            for row in factor_table.to_dict(orient="records"):
                factor_rows.append(
                    {
                        "symbol": row.get("factor") or row.get("name") or row.get("symbol"),
                        "asset_class": "Factor",
                        "portfolio_weight": abs(_safe_float(row.get("exposure") or row.get("value") or 1)),
                        "macro_sensitivity": _safe_float(row.get("exposure") or row.get("value") or 0),
                        "source": row.get("source", "factor backend"),
                        "freshness": "estimated",
                    }
                )
        render_table(st, build_factor_exposure_heatmap(factor_rows)["table"])
    elif result:
        st.plotly_chart(factor_exposure_radar_or_bar(pd.DataFrame()), use_container_width=True)
        render_table(st, pd.DataFrame([build_portfolio_source_status(source_mode)]))
    else:
        st.info("Run the factor backend to populate factor profiles and strategy factor matrix.")

with tabs[13]:
    terminal_section_header(st, "Alpha Combination Search", "Backtest-ranked research bundles from available strategy candidates")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        combinations = run_alpha_combination_search(research["leaderboard"], max_size=3)
        render_table(st, combinations)
        cards = build_alpha_combination_cards(combinations)
        combo_cols = st.columns(3)
        for idx, card in enumerate(cards):
            with combo_cols[idx % len(combo_cols)]:
                intelligence_card(st, title=card["title"], summary=card["summary"], severity=card["severity"], tags=card["tags"], freshness="estimated")
        st.caption("Alpha combinations are research candidates only and require validation.")
    else:
        st.info("Run a backtest to populate alpha combination search.")

with tabs[14]:
    terminal_section_header(st, "Ensemble Builder", "Research-only strategy ensemble from ranked candidates")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        ensemble = build_strategy_ensemble_report(research["leaderboard"], research["strategy_returns"])
        metric_strip(
            st,
            [
                {"label": "Periods", "value": ensemble["metrics"].get("periods"), "delta": "observed", "freshness": "estimated"},
                {"label": "Cumulative Return", "value": ensemble["metrics"].get("cumulative_return"), "delta": "historical", "freshness": "estimated"},
                {"label": "Volatility", "value": ensemble["metrics"].get("annualized_volatility"), "delta": "annualized", "freshness": "estimated"},
                {"label": "Risk-Adjusted", "value": ensemble["metrics"].get("risk_adjusted_score"), "delta": "research metric", "freshness": "estimated"},
            ],
        )
        c1, c2 = st.columns(2)
        c1.plotly_chart(strategy_ensemble_equity_curve(ensemble["returns"]), use_container_width=True)
        c2.plotly_chart(strategy_ensemble_drawdown_chart(ensemble["returns"]), use_container_width=True)
        render_table(st, ensemble["weights"])
        st.caption(ensemble["caveat"])
    else:
        st.info("Run a backtest to build strategy ensembles.")

with tabs[15]:
    terminal_section_header(st, "Regime Performance", "Strategy behavior by proxy regime label")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        regime_table = build_regime_performance_table(research["strategy_returns"])
        summary = build_regime_performance_summary(regime_table)
        st.plotly_chart(strategy_regime_heatmap(regime_table), use_container_width=True)
        render_table(st, regime_table)
        st.json(summary)
    else:
        st.info("Run a backtest to calculate regime performance.")

with tabs[16]:
    terminal_section_header(st, "Risk Budgeting", "Estimated contribution of strategy candidates to ensemble risk")
    result = st.session_state["portfolio_quant_backtest"]
    if result:
        research = build_strategy_research_payload(result["asset_returns"])
        ensemble = build_strategy_ensemble_report(research["leaderboard"], research["strategy_returns"])
        budget = build_strategy_risk_budget(research["strategy_returns"], ensemble["weights"])
        st.plotly_chart(strategy_risk_budget_chart(budget["table"]), use_container_width=True)
        render_table(st, budget["table"])
        st.caption(budget["caveat"])
    else:
        st.info("Run a backtest to calculate strategy risk budgets.")

with tabs[17]:
    terminal_section_header(st, "Data Quality", "Strategy data quality, factor coverage, sample length, and proxy dependence")
    result = st.session_state["portfolio_quant_backtest"]
    payload = {
        "factors": (st.session_state.get("portfolio_factor_profile") or {}).get("factors", {}).get("table", {}).to_dict() if hasattr((st.session_state.get("portfolio_factor_profile") or {}).get("factors", {}).get("table", None), "to_dict") else {},
        "sample_length": len(result.get("portfolio_returns", [])) if result else 0,
        "missing_pct": 0.0,
        "oos_available": bool(result),
        "source_confidence": (st.session_state.get("portfolio_factor_profile") or {}).get("source_confidence", 50),
        "proxy_dependence": factor_backend != "openbb_preferred",
    }
    quality = compute_strategy_data_quality_score(payload)
    metric_strip(
        st,
        [
            {"label": "Data Quality", "value": quality["score"], "delta": quality["label"], "freshness": "estimated"},
            {"label": "Factor Coverage", "value": quality["factor_coverage_score"], "delta": "%", "freshness": "estimated"},
            {"label": "Backtest Reliability", "value": quality["backtest_reliability_score"], "delta": "score", "freshness": "estimated"},
            {"label": "Data Gaps", "value": len(detect_strategy_data_gaps(payload)), "delta": "visible", "freshness": "missing" if detect_strategy_data_gaps(payload) else "fresh"},
        ],
    )
    quality_cols = st.columns(2)
    for idx, card in enumerate(build_strategy_data_quality_cards(payload)):
        with quality_cols[idx % len(quality_cols)]:
            intelligence_card(st, title=card["title"], summary=card["summary"], severity=card["severity"], tags=card["tags"], freshness="estimated")
    render_table(st, pd.DataFrame({"data_gap": detect_strategy_data_gaps(payload)}))

page_footer(st)
