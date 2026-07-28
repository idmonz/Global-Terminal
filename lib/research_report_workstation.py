from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .crypto_intelligence_contract import build_crypto_intelligence_contract
from .equity_intelligence import build_equity_intelligence_contract
from .market_intelligence import build_market_intelligence_contract
from .provider_health_engine import build_provider_health_ledger, summarize_provider_health_ledger


RESEARCH_REPORT_WORKSTATION_VERSION = "research_report_workstation.v1"
FIXTURE_FETCHED_AT = "2026-06-16T00:00:00+00:00"

FORBIDDEN_RESEARCH_PHRASES = [
    "trade permission",
    "recommended leverage",
    "maximum leverage",
    "long entry",
    "short entry",
    "entry zone",
    "stop loss",
    "take profit",
    "position size",
    "position sizing",
    "final action",
    "order type recommendation",
    "execution method",
    "broker execution",
    "order routing",
]

REPLACEMENT_LANGUAGE = {
    "trade permission": "research readiness",
    "recommended leverage": "risk exposure context",
    "maximum leverage": "risk exposure ceiling context",
    "long entry": "upside observation trigger",
    "short entry": "downside observation trigger",
    "entry zone": "evidence zone",
    "stop loss": "invalidating evidence",
    "take profit": "scenario objective area",
    "position size": "risk budget context",
    "position sizing": "risk budget context",
    "final action": "final research stance",
    "order type recommendation": "execution-risk observation",
    "execution method": "market-access caveat",
    "broker execution": "account-action pathway",
    "order routing": "account-action pathway",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else fallback).replace("\x00", "").strip()
    return text or fallback


def rewrite_non_advisory_text(value: Any) -> str:
    text = _safe_text(value)
    lowered = text.lower()
    for phrase, replacement in REPLACEMENT_LANGUAGE.items():
        if phrase in lowered:
            text = _replace_case_insensitive(text, phrase, replacement)
            lowered = text.lower()
    return text


def _replace_case_insensitive(text: str, needle: str, replacement: str) -> str:
    import re

    return re.sub(re.escape(needle), replacement, text, flags=re.IGNORECASE)


def find_forbidden_report_phrases(value: Any) -> list[str]:
    encoded = _safe_text(value).lower() if not isinstance(value, (dict, list, tuple)) else _flatten_text(value).lower()
    return sorted({phrase for phrase in FORBIDDEN_RESEARCH_PHRASES if phrase in encoded})


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return _safe_text(value)


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _status(row: dict[str, Any], fallback: str = "fixture") -> str:
    return _safe_text(row.get("source_status") or row.get("status") or row.get("freshness") or fallback, fallback)


def _provider(row: dict[str, Any], fallback: str = "research_report_workstation") -> str:
    return _safe_text(row.get("provider") or row.get("source") or fallback, fallback)


def _fetched_at(row: dict[str, Any]) -> str | None:
    value = row.get("fetched_at") or row.get("latest_fetched_at") or row.get("generated_at")
    return _safe_text(value) if value else None


def _confidence(status: str, *, proxy: bool = False) -> float:
    normalized = status.lower()
    if normalized == "live/fresh":
        return 0.86
    if normalized == "cached":
        return 0.74
    if normalized == "stale":
        return 0.56
    if "fixture" in normalized:
        return 0.42
    if "proxy" in normalized or proxy:
        return 0.46
    if normalized in {"missing-key", "provider-required", "unavailable"}:
        return 0.2
    return 0.5


def _evidence_row(
    *,
    label: str,
    observation: Any,
    row: dict[str, Any] | None = None,
    source_status: str | None = None,
    provider: str | None = None,
    data_gap: str | None = None,
    caveat: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    source = dict(row or {})
    status = source_status or _status(source)
    return {
        "label": rewrite_non_advisory_text(label),
        "observation": rewrite_non_advisory_text(observation),
        "provider": provider or _provider(source),
        "source": _safe_text(source.get("source") or source.get("source_url") or source.get("chart_id") or label),
        "source_url": _safe_text(source.get("source_url")) or None,
        "source_status": status,
        "freshness": _safe_text(source.get("freshness") or status),
        "fetched_at": _fetched_at(source),
        "confidence": confidence if confidence is not None else _confidence(status),
        "caveat": rewrite_non_advisory_text(caveat or source.get("caveat") or "Source status must be inspected before using this observation."),
        "data_gap": rewrite_non_advisory_text(data_gap or source.get("data_gap") or "No additional data gap reported."),
        "not_financial_advice": True,
    }


def _section(section_id: str, title: str, summary: Iterable[Any], evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_evidence_row(label="section placeholder", observation="No source rows were available.", source_status="unavailable", data_gap="Section has no source rows yet.")] if not evidence_rows else evidence_rows
    statuses = [_status(row) for row in rows]
    confidence = round(sum(float(row.get("confidence") or 0.0) for row in rows) / max(1, len(rows)), 3)
    return {
        "section_id": section_id,
        "title": rewrite_non_advisory_text(title),
        "summary_bullets": [rewrite_non_advisory_text(item) for item in summary if _safe_text(item)],
        "evidence_rows": rows,
        "source_status": "mixed" if len(set(statuses)) > 1 else statuses[0],
        "provider": "multi-source" if len({row.get("provider") for row in rows}) > 1 else _safe_text(rows[0].get("provider")),
        "fetched_at": next((row.get("fetched_at") for row in rows if row.get("fetched_at")), FIXTURE_FETCHED_AT),
        "confidence": confidence,
        "caveat": "Section is source-bound research context, not investment advice.",
        "data_gap": "; ".join(sorted({str(row.get("data_gap")) for row in rows if row.get("data_gap")}))[:800],
        "not_financial_advice": True,
    }


def _market_snapshot_rows(market: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in _records(market.get("market_tape"))[:12]:
        change = row.get("daily_return_pct")
        monthly = row.get("one_month_return_pct")
        rows.append(_evidence_row(label=_safe_text(row.get("symbol"), "asset"), observation=f"{row.get('label')} daily {change}; one month {monthly}; status {_status(row)}.", row=row))
    return rows


def _macro_rows(market: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in _records(market.get("macro_context")):
        rows.append(_evidence_row(label=_safe_text(row.get("theme"), "macro context"), observation=f"Linked symbols: {row.get('linked_symbols')}; status {_status(row)}.", row=row))
    return rows


def _technical_rows(equity: dict[str, Any], crypto: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    technical = equity.get("technical_diagnostics") if isinstance(equity.get("technical_diagnostics"), dict) else {}
    if technical:
        rows.append(_evidence_row(label=f"{equity.get('symbol', 'equity')} technical context", observation=f"RSI bucket {technical.get('rsi_bucket')}; MACD regime {technical.get('macd_regime')}; 52-week position {technical.get('range_52w_position')}.", row=technical))
    derivative = crypto.get("derivatives_snapshot") if isinstance(crypto.get("derivatives_snapshot"), dict) else {}
    if derivative:
        rows.append(_evidence_row(label=f"{crypto.get('symbol', 'crypto')} derivatives context", observation=f"Funding bps {derivative.get('funding_rate_bps')}; open interest {derivative.get('open_interest_billions')}; taker ratio {derivative.get('taker_buy_sell_ratio')}.", row=derivative))
    for row in _records(equity.get("scenario_matrix"))[:2] + _records(crypto.get("scenario_matrix"))[:2]:
        rows.append(_evidence_row(label=_safe_text(row.get("scenario"), "scenario"), observation=row.get("evidence_summary") or f"Evidence weight {row.get('evidence_weight')}", row=row))
    return rows


def _options_readiness_rows(equity: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    options = equity.get("options_gamma_proxy") if isinstance(equity.get("options_gamma_proxy"), dict) else {}
    if options:
        rows.append(_evidence_row(label="Options and volatility readiness", observation="Options, GEX, volatility, and dealer-positioning claims remain provider-gated unless source rows are present.", row=options, data_gap=options.get("data_gap") or "No provider-backed options chain is available."))
    for row in _records(equity.get("valuation_quality")):
        rows.append(_evidence_row(label=_safe_text(row.get("metric"), "readiness metric"), observation=f"Readiness status {row.get('status')} with score {row.get('score')}.", row=row))
    return rows


def _scenario_rows(equity: dict[str, Any], crypto: dict[str, Any]) -> list[dict[str, Any]]:
    source_rows = _records(equity.get("scenario_matrix"))[:3] + _records(crypto.get("scenario_matrix"))[:3]
    rows = []
    for row in source_rows:
        rows.append(
            {
                "scenario": rewrite_non_advisory_text(row.get("scenario")),
                "probability_hint": None,
                "evidence_weight": row.get("evidence_weight"),
                "research_condition": rewrite_non_advisory_text(row.get("evidence_summary") or "Scenario condition requires source review."),
                "invalidating_evidence": "Source status changes, provider gaps, or contradictory market/news evidence would lower confidence.",
                "provider": _provider(row),
                "source_status": _status(row),
                "fetched_at": _fetched_at(row),
                "confidence": _confidence(_status(row) ),
                "caveat": rewrite_non_advisory_text(row.get("caveat") or "Scenario is research context only."),
                "data_gap": rewrite_non_advisory_text(row.get("data_gap") or "No additional data gap reported."),
                "not_financial_advice": True,
            }
        )
    return rows


def _source_register(*collections: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    register: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for collection in collections:
        for row in collection:
            provider = _provider(row)
            source = _safe_text(row.get("source") or row.get("source_url") or row.get("chart_id") or row.get("label") or provider)
            status = _status(row)
            key = (provider, source, status)
            if key in seen:
                continue
            seen.add(key)
            register.append(
                {
                    "provider": provider,
                    "source": source,
                    "source_url": _safe_text(row.get("source_url")) or None,
                    "source_status": status,
                    "freshness": _safe_text(row.get("freshness") or status),
                    "fetched_at": _fetched_at(row),
                    "confidence": _confidence(status),
                    "caveat": rewrite_non_advisory_text(row.get("caveat") or "Inspect provider status before use."),
                    "data_gap": rewrite_non_advisory_text(row.get("data_gap") or "No additional data gap reported."),
                    "not_financial_advice": True,
                }
            )
    return register[:80]


def build_research_report_workstation_contract(
    *,
    include_runtime: bool = False,
    symbol: str = "AAPL",
    crypto_symbol: str = "BTCUSDT",
    market: dict[str, Any] | None = None,
    equity: dict[str, Any] | None = None,
    crypto: dict[str, Any] | None = None,
    provider_rows: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    market_contract = market or build_market_intelligence_contract(include_runtime=include_runtime)
    equity_contract = equity or build_equity_intelligence_contract(symbol=symbol, include_runtime=include_runtime)
    crypto_contract = crypto or build_crypto_intelligence_contract(symbol=crypto_symbol, include_runtime=include_runtime)
    provider_ledger = list(provider_rows or build_provider_health_ledger([]))
    market_rows = _market_snapshot_rows(market_contract)
    macro_rows = _macro_rows(market_contract)
    technical_rows = _technical_rows(equity_contract, crypto_contract)
    options_rows = _options_readiness_rows(equity_contract)
    scenario_matrix = _scenario_rows(equity_contract, crypto_contract)
    source_register = _source_register(
        market_contract.get("provider_status") or [],
        equity_contract.get("provider_status") or [],
        crypto_contract.get("provider_status") or [],
        provider_ledger,
    )
    news_rows = [
        _evidence_row(
            label="News and geopolitical risk readiness",
            observation="News, map, and geopolitical rows should be connected in the next report slice; this v1 contract keeps the missing link explicit.",
            source_status="provider-required",
            provider="news_dashboard",
            data_gap="Report v1 does not yet ingest live news dashboard rows by default.",
            caveat="Use War Map and News workspace source rows before making market-impact claims.",
            confidence=0.24,
        )
    ]
    sections = [
        _section(
            "executive_summary",
            "Executive Summary",
            [
                f"Market rows: {len(market_contract.get('market_tape') or [])}; equity symbol: {equity_contract.get('symbol')}; crypto symbol: {crypto_contract.get('symbol')}.",
                "The report is source-bound and non-advisory; missing provider data remains visible as data gaps.",
                "Scenario language is observational and avoids account-action or leverage instructions.",
            ],
            market_rows[:4] + technical_rows[:2],
        ),
        _section("market_snapshot", "Market Snapshot", ["Cross-asset tape rows are summarized with source labels and freshness."], market_rows),
        _section("macro_cross_asset_context", "Macro And Cross-Asset Context", ["Macro links are contextual relationships, not forecasts."], macro_rows),
        _section("news_geopolitical_risk", "News And Geopolitical Risk", ["News-to-map integration is tracked as an explicit data gap in v1."], news_rows),
        _section("technical_market_structure", "Technical And Market-Structure Observations", ["Technical, derivatives, and scenario rows remain evidence observations."], technical_rows),
        _section("options_gex_volatility_readiness", "Options, GEX, And Volatility Readiness", ["Options/GEX claims require provider-backed chains; otherwise readiness is unavailable."], options_rows),
        _section("scenario_matrix", "Scenario Matrix", ["Scenarios express conditions and invalidating evidence, not instructions."], [_evidence_row(label=row["scenario"], observation=row["research_condition"], row=row) for row in scenario_matrix]),
        _section("sources_confidence_caveats", "Data Sources, Confidence, Caveats, And Gaps", ["All source rows are deduplicated across market, equity, crypto, and provider ledgers."], [_evidence_row(label=row["provider"], observation=row["source"], row=row) for row in source_register[:20]]),
    ]
    payload = {
        "research_report_workstation_version": RESEARCH_REPORT_WORKSTATION_VERSION,
        "workspace": "research-report",
        "report_id": "source_bound_cross_asset_regime_v1",
        "report_title": "Source-Bound Cross-Asset Research Summary",
        "style_reference": {
            "source": "Gold Quant Regime and Leveraged MFT Report",
            "local_path_reference": "external (2)/Gold Quant Regime and Leveraged MFT Report GEX, Options Flow, Macro, Geopolitics, Technicals and Execution Playbook.md",
            "adoption_mode": "structure-only-clean-room",
            "license_stance": "user-supplied reference; no source code copied",
            "caveat": "Trade, leverage, account-action, and execution language is rewritten into non-advisory research sections.",
        },
        "sections": sections,
        "scenario_matrix": scenario_matrix,
        "source_register": source_register,
        "provider_health_summary": summarize_provider_health_ledger(provider_ledger),
        "policy": {
            "non_advisory": True,
            "account_action_enabled": False,
            "broker_or_order_path_enabled": False,
            "forbidden_language_detected": [],
            "replacement_language": sorted(set(REPLACEMENT_LANGUAGE.values())),
        },
        "summary": {
            "workspace": "research-report",
            "section_count": len(sections),
            "scenario_count": len(scenario_matrix),
            "source_count": len(source_register),
            "runtime_requested": bool(include_runtime),
            "source_status": "mixed" if source_register else "unavailable",
            "non_advisory": True,
            "account_action_enabled": False,
        },
        "caveat": "Research report output is source-bound context only and does not provide investment advice or account actions.",
    }
    detected = find_forbidden_report_phrases(payload)
    payload["policy"]["forbidden_language_detected"] = detected
    return payload
