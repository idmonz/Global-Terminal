from __future__ import annotations

from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE


def options_formula_summary(model: str) -> str:
    model = str(model or "black_scholes")
    if model == "black_76":
        return "Black-76 discounts the expected futures-option payoff using the risk-free discount factor and lognormal futures dynamics."
    if model == "garman_kohlhagen":
        return "Garman-Kohlhagen is the FX form of Black-Scholes using domestic discounting and foreign-rate carry."
    return "Black-Scholes values a European option using spot, strike, time, rate, volatility, and continuous dividend/carry yield."


def render_options_report_markdown(title: str, result: dict[str, Any], *, report_kind: str = "options_pricing_report") -> str:
    payload = result.get("payload", result)
    inputs = payload.get("inputs", payload.get("base_inputs", {}))
    model = payload.get("model") or inputs.get("model", "black_scholes")
    lines = [
        f"# {title}",
        "",
        RESEARCH_ONLY_OPTIONS_NOTICE,
        "",
        "## Report type",
        f"- {report_kind}",
        "",
        "## Model / formula summary",
        f"- model: `{model}`",
        f"- formula: {options_formula_summary(model)}",
        "",
        "## Inputs",
    ]
    if inputs:
        for key, value in sorted(inputs.items()):
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- Inputs were not supplied in a structured payload.")
    lines.extend(["", "## Outputs"])
    for key in ["price", "contract_value", "implied_volatility", "converged", "scenario_count", "error_reason"]:
        if key in payload:
            lines.append(f"- {key}: `{payload.get(key)}`")
    if "greeks" in payload:
        lines.extend(["", "## Greeks"])
        for key, value in payload.get("greeks", {}).items():
            lines.append(f"- {key}: `{value}`")
    if "rows" in payload:
        lines.extend(["", "## Scenario / payoff rows", f"- row_count: `{len(payload.get('rows', []))}`"])
    lines.extend(["", "## Caveats"])
    caveats = result.get("caveats", []) or payload.get("caveats", []) or ["Manual/supplied data calculation; no live option chain is assumed."]
    for caveat in caveats:
        lines.append(f"- {caveat}")
    lines.extend(["", "## Source snapshot", f"```json\n{result.get('source_snapshot', {})}\n```", ""])
    return "\n".join(lines)
