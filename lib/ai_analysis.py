from __future__ import annotations

from typing import Any, Callable

from .ai_prompts import (
    crypto_neutral_analysis_prompt,
    energy_geopolitical_neutral_analysis_prompt,
    etf_neutral_analysis_prompt,
    macro_neutral_analysis_prompt,
    portfolio_neutral_risk_prompt,
    scenario_summary_prompt,
    screener_explanation_prompt,
    stock_neutral_analysis_prompt,
)
from .ai_providers import AIResponse, call_ai_model, call_rule_based_fallback
from .ai_safety import ai_output_to_safe_markdown, redact_secrets, validate_ai_output
from .openbb_bridge import OPENBB_CAVEAT, is_openbb_installed


PromptBuilder = Callable[[Any], dict[str, str]]


def _safe_context(context: Any) -> Any:
    if isinstance(context, dict):
        return {key: redact_secrets(str(value))[:1200] for key, value in context.items()}
    if hasattr(context, "head") and hasattr(context, "to_dict"):
        try:
            return {"rows": context.head(20).to_dict(orient="records"), "columns": list(context.columns)}
        except Exception:
            return str(context)[:3000]
    return redact_secrets(str(context))[:3000]


def _finalize_response(response: AIResponse, context: Any) -> AIResponse:
    if not response.ok:
        return call_rule_based_fallback(context=context)
    safe_text = ai_output_to_safe_markdown(response.text)
    ok, violations = validate_ai_output(safe_text)
    response.text = safe_text
    if not ok:
        response.text = ai_output_to_safe_markdown(safe_text)
        response.warning = "AI output contained restricted terms and was neutralized: " + ", ".join(sorted(set(violations)))
    response.source_status["safety_validated"] = True
    response.source_status["safety_violations"] = violations
    return response


def _analyze(context: Any, builder: PromptBuilder, *, preferred: str = "auto") -> AIResponse:
    safe_context = _safe_context(context)
    prompt = builder(safe_context)
    response = call_ai_model(prompt["system"], prompt["user"], preferred=preferred, context=safe_context)
    return _finalize_response(response, safe_context)


def analyze_overview_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, macro_neutral_analysis_prompt, preferred=preferred)


def analyze_stock_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, stock_neutral_analysis_prompt, preferred=preferred)


def analyze_etf_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, etf_neutral_analysis_prompt, preferred=preferred)


def analyze_crypto_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, crypto_neutral_analysis_prompt, preferred=preferred)


def analyze_energy_geopolitical_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, energy_geopolitical_neutral_analysis_prompt, preferred=preferred)


def analyze_portfolio_risk_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, portfolio_neutral_risk_prompt, preferred=preferred)


def analyze_screener_results_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, screener_explanation_prompt, preferred=preferred)


def summarize_cross_asset_scenarios_neutral(context: Any = None, *, preferred: str = "auto") -> AIResponse:
    return _analyze(context, scenario_summary_prompt, preferred=preferred)


def _compact_frame_summary(value: Any, *, max_rows: int = 5) -> Any:
    if hasattr(value, "head") and hasattr(value, "to_dict"):
        try:
            frame = value.head(max_rows)
            return {"columns": list(value.columns), "row_count": int(len(value)), "sample_rows": frame.to_dict(orient="records")}
        except Exception:
            return str(value)[:1200]
    return value


def build_openbb_financial_ai_context(financial_state: dict[str, Any]) -> dict[str, Any]:
    overview = financial_state.get("overview", {}) if isinstance(financial_state, dict) else {}
    return {
        "context_type": "financial_terminal_openbb_enriched",
        "source_mode": financial_state.get("source_mode"),
        "openbb_available": is_openbb_installed(),
        "fallback_used": financial_state.get("fallback_used"),
        "ticker": financial_state.get("ticker"),
        "source_provider": financial_state.get("source_provider"),
        "ratios": overview.get("ratios", {}),
        "availability": _compact_frame_summary(financial_state.get("availability")),
        "data_gaps": overview.get("data_gaps", []),
        "uncertainty": "OpenBB/provider fields may be delayed, missing, licensed, revised, or unavailable.",
        "disclosure": "No financial advice. This context is for neutral research summaries only.",
        "openbb_caveat": OPENBB_CAVEAT,
    }


def build_openbb_portfolio_ai_context(portfolio_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_type": "portfolio_quant_openbb_enriched",
        "source_mode": portfolio_payload.get("source_status", {}).get("source_mode") or portfolio_payload.get("source_mode"),
        "openbb_available": is_openbb_installed(),
        "fallback_used": portfolio_payload.get("source_status", {}).get("fallback_used"),
        "summary": portfolio_payload.get("summary"),
        "backtest_metrics": portfolio_payload.get("backtest", {}).get("metrics", {}),
        "strategy_leaderboard": _compact_frame_summary(portfolio_payload.get("strategy_research", {}).get("leaderboard")),
        "data_gaps": portfolio_payload.get("backtest", {}).get("data_gaps", []),
        "uncertainty": "Backtests and model-estimated forward distributions are sensitive to data windows, costs, and missing assets.",
        "disclosure": "No financial advice. Backtests are not predictions and not recommendations.",
        "openbb_caveat": OPENBB_CAVEAT,
    }


def build_openbb_screener_ai_context(screener_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_type": "screener_openbb_enriched",
        "source_mode": screener_payload.get("source_status", {}).get("source_mode"),
        "openbb_available": is_openbb_installed(),
        "fallback_used": screener_payload.get("source_status", {}).get("fallback_allowed") and not screener_payload.get("source_status", {}).get("openbb_installed"),
        "asset_class": screener_payload.get("asset_class"),
        "filters": screener_payload.get("filters"),
        "rows": _compact_frame_summary(screener_payload.get("rows")),
        "data_gaps": screener_payload.get("data_gaps"),
        "uncertainty": "Screener fields depend on provider coverage and may contain delayed or missing data.",
        "disclosure": "No financial advice. Screener rows are research candidates or watchlist context only.",
        "openbb_caveat": OPENBB_CAVEAT,
    }


def build_mcp_ready_ai_context(payload: dict[str, Any]) -> dict[str, Any]:
    from .openbb_ai_context_router import build_openbb_ai_context_bundle

    return build_openbb_ai_context_bundle(
        financial=payload.get("financial"),
        portfolio=payload.get("portfolio"),
        screener=payload.get("screener"),
        macro_energy=payload.get("macro_energy"),
        war_room=payload.get("war_room"),
    )


def prepare_context_for_button_triggered_ai(packet: dict[str, Any]) -> dict[str, Any]:
    from .mcp_context_router import route_context_to_ai_provider

    return route_context_to_ai_provider(packet, execute=False)
