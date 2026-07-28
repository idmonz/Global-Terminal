from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = (
    "You are a financial research analyst. You must not recommend buying, selling, holding, "
    "shorting, longing, entering, exiting, allocating, or timing trades. You may summarize factual "
    "evidence, risks, uncertainty, scenarios, data gaps, and watch-points. Use neutral language. "
    "Do not personalize advice."
)


def _compact_context(context: Any) -> str:
    if context is None:
        return "No structured context supplied."
    if isinstance(context, str):
        return context[:6000]
    if isinstance(context, dict):
        lines = []
        for key, value in context.items():
            text = str(value)
            lines.append(f"- {key}: {text[:700]}")
        return "\n".join(lines)[:6000]
    return str(context)[:6000]


def _prompt(task: str, context: Any) -> dict[str, str]:
    return {
        "system": SYSTEM_PROMPT,
        "user": (
            f"{task}\n\n"
            "Use concise bullets with these sections: Evidence, Risks, Uncertainty, Watch-points, Data gaps.\n"
            "Avoid recommendation language and avoid personalized advice.\n\n"
            f"Context:\n{_compact_context(context)}"
        ),
    }


def stock_neutral_analysis_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral stock research summary.", context)


def etf_neutral_analysis_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral ETF research summary.", context)


def crypto_neutral_analysis_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral crypto market structure summary.", context)


def macro_neutral_analysis_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral macro cross-asset summary.", context)


def energy_geopolitical_neutral_analysis_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral energy and geopolitical risk summary.", context)


def portfolio_neutral_risk_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral portfolio risk summary.", context)


def scenario_summary_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Summarize scenario evidence neutrally.", context)


def news_digest_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral news and event digest.", context)


def screener_explanation_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Explain screener results neutrally.", context)


def openbb_enriched_context_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral OpenBB-enriched research context summary.", context)


def mcp_ready_context_prompt(context: Any = None) -> dict[str, str]:
    return _prompt("Prepare a neutral MCP-ready endpoint context summary with source confidence and data gaps.", context)
