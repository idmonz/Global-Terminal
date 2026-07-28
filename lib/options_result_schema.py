from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE

OPTION_RESULT_TYPES = {"pricing", "scenario", "iv", "payoff", "provider_capability", "chain", "surface", "book", "diagnostics"}


@dataclass(frozen=True)
class OptionsResult:
    result_type: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)
    source_snapshot: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    research_only: bool = True
    notice: str = RESEARCH_ONLY_OPTIONS_NOTICE


def build_options_result(result_type: str, title: str, payload: dict[str, Any] | None = None, source_snapshot: dict[str, Any] | None = None, caveats: list[str] | None = None) -> dict[str, Any]:
    normalized = str(result_type or "pricing").lower()
    if normalized not in OPTION_RESULT_TYPES:
        raise ValueError(f"Unsupported options result type: {result_type}")
    return asdict(OptionsResult(normalized, str(title or "Options research result"), payload or {}, source_snapshot or {"source": "manual", "freshness": "supplied", "confidence": "user-supplied"}, caveats or []))


def summarize_options_result(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return {
        "result_type": result.get("result_type", "unknown"),
        "title": result.get("title", "Options research result"),
        "model": payload.get("model") or payload.get("inputs", {}).get("model"),
        "price": payload.get("price"),
        "converged": payload.get("converged"),
        "scenario_count": payload.get("scenario_count") or len(payload.get("rows", [])),
        "research_only": True,
        "notice": RESEARCH_ONLY_OPTIONS_NOTICE,
    }
