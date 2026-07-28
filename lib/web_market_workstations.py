from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .equity_intelligence import build_equity_intelligence_contract
from .heatmap_drilldown_engine import build_heatmap_drilldown_target
from .market_intelligence import build_market_intelligence_contract
from .options_lab_page_layout import build_options_lab_page_payload
from .options_provider_capabilities import inspect_options_provider_capabilities
from .options_quant_workstation import (
    OPTIONS_QUANT_WORKSTATION_VERSION,
    build_options_quant_workstation_contract,
)


FINANCIAL_FUNDAMENTALS_VERSION = "financial_fundamentals.v1"
OPTIONS_QUANT_VERSION = OPTIONS_QUANT_WORKSTATION_VERSION
SCREENER_DRILLDOWN_VERSION = "screener_drilldown.v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _source_status(row: dict[str, Any]) -> str:
    return str(row.get("source_status") or row.get("status") or row.get("freshness") or "unknown")


def _source_row(row: dict[str, Any], *, provider: str, source: str, row_count: int = 1) -> dict[str, Any]:
    status = _source_status(row)
    return {
        "provider": row.get("provider") or provider,
        "source": row.get("source") or source,
        "source_url": row.get("source_url") or "",
        "status": status,
        "source_status": status,
        "freshness": row.get("freshness") or status,
        "fetched_at": row.get("fetched_at") or row.get("last_checked"),
        "availability": "unavailable" if status in {"missing-key", "unavailable", "provider-required"} else "limited",
        "row_count": row.get("row_count", row_count),
        "confidence": row.get("confidence"),
        "caveat": row.get("caveat") or row.get("notice") or "",
        "data_gap": row.get("data_gap") or row.get("error") or "",
        "not_financial_advice": True,
    }


def _metric_row(
    *,
    metric: str,
    value: Any,
    category: str,
    source: dict[str, Any],
    source_status: str | None = None,
    caveat: str | None = None,
    data_gap: str | None = None,
) -> dict[str, Any]:
    return {
        "metric": metric,
        "value": value,
        "category": category,
        "provider": source.get("provider") or "financial_terminal",
        "source_status": source_status or _source_status(source),
        "freshness": source.get("freshness") or source_status or _source_status(source),
        "fetched_at": source.get("fetched_at"),
        "confidence": source.get("confidence"),
        "caveat": caveat or source.get("caveat") or "",
        "data_gap": data_gap or source.get("data_gap") or "",
        "not_financial_advice": True,
    }


def _evidence_rows(*collections: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for collection in collections:
        rows.extend(_records(collection))
    return rows


def build_financial_fundamentals_contract(
    symbol: str = "AAPL",
    *,
    include_runtime: bool = False,
    equity_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    equity = equity_contract or build_equity_intelligence_contract(symbol=symbol, include_runtime=include_runtime)
    symbol = str(equity.get("symbol") or symbol or "AAPL").upper()
    overview = dict(equity.get("financial_overview") or {})
    quality = _records(equity.get("valuation_quality"))
    providers = _records(equity.get("provider_status"))
    chart_specs = [
        chart
        for chart in _records(equity.get("chart_specs"))
        if "valuation" in str(chart.get("chart_id") or "") or "financial" in str(chart.get("title") or "").lower()
    ]
    statement_metrics = [
        _metric_row(metric="company name", value=overview.get("company_name"), category="profile", source=overview),
        _metric_row(metric="sector", value=overview.get("sector"), category="profile", source=overview),
        _metric_row(metric="market cap", value=overview.get("market_cap"), category="profile", source=overview),
        _metric_row(metric="revenue growth proxy", value=overview.get("revenue_growth_proxy"), category="growth", source=overview),
        _metric_row(metric="gross margin proxy", value=overview.get("gross_margin_proxy"), category="profitability", source=overview),
        _metric_row(metric="free cashflow margin proxy", value=overview.get("free_cashflow_margin_proxy"), category="cashflow", source=overview),
    ]
    quality_rows = [
        {
            **row,
            "category": "data_quality",
            "not_financial_advice": True,
        }
        for row in quality
    ]
    data_gaps = sorted(
        {
            str(gap)
            for gap in [
                overview.get("data_gap"),
                *[row.get("data_gap") for row in quality_rows],
                *equity.get("data_gaps", []),
            ]
            if gap and str(gap) != "None"
        }
    )
    source_rows = [_source_row(overview, provider="financial_terminal", source=f"{symbol}:financial_overview")]
    source_rows.extend(_source_row(row, provider="financial_terminal", source=f"{symbol}:valuation_quality") for row in quality_rows)
    source_rows.extend(providers)
    unavailable = [
        row
        for row in source_rows
        if row.get("availability") == "unavailable"
        or str(row.get("source_status") or row.get("status") or "").lower() in {"missing-key", "unavailable", "provider-required"}
    ]
    return {
        "financial_fundamentals_version": FINANCIAL_FUNDAMENTALS_VERSION,
        "workspace": "financial-fundamentals",
        "symbol": symbol,
        "financial_overview": overview,
        "statement_metrics": statement_metrics,
        "valuation_quality": quality_rows,
        "chart_specs": chart_specs,
        "source_register": source_rows,
        "unavailable_sources": unavailable,
        "data_gaps": data_gaps,
        "command_routes": [
            {"raw": f"{symbol} FA", "target_view": "equity-intelligence", "source_status": "schema-ready", "not_financial_advice": True},
            {"raw": f"{symbol} DES", "target_view": "financial-fundamentals", "source_status": "schema-ready", "not_financial_advice": True},
            {"raw": f"{symbol} KEY", "target_view": "financial-fundamentals", "source_status": "schema-ready", "not_financial_advice": True},
        ],
        "summary": {
            "workspace": "financial-fundamentals",
            "symbol": symbol,
            "metric_count": len(statement_metrics),
            "quality_row_count": len(quality_rows),
            "chart_count": len(chart_specs),
            "runtime_requested": bool(include_runtime),
            "source_status": overview.get("source_status") or "unavailable",
            "provider_required_count": sum(1 for row in unavailable if str(row.get("source_status") or row.get("status")) == "provider-required"),
            "non_advisory": True,
            "broker_execution_added": False,
        },
        "caveat": "Financial/Fundamentals is source-bound research context; missing statements remain explicit data gaps.",
    }


def build_options_quant_contract(
    symbol: str = "AAPL",
    *,
    expiry: str | None = None,
    include_runtime: bool = False,
    equity_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = equity_contract
    return build_options_quant_workstation_contract(
        symbol=symbol,
        expiry=expiry,
        include_runtime=include_runtime,
    )


def _build_options_quant_contract_legacy(
    symbol: str = "AAPL",
    *,
    include_runtime: bool = False,
    equity_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    equity = equity_contract or build_equity_intelligence_contract(symbol=symbol, include_runtime=include_runtime)
    symbol = str(equity.get("symbol") or symbol or "AAPL").upper()
    options = dict(equity.get("options_gamma_proxy") or {})
    scenarios = [
        {
            **row,
            "not_financial_advice": True,
        }
        for row in _records(equity.get("scenario_matrix"))
    ]
    provider_capabilities = inspect_options_provider_capabilities()
    capability_rows = [
        {
            **row,
            "source_status": "supplied" if row.get("used_for_calculation") else "provider-required" if "OpenBB" in str(row.get("provider")) else row.get("freshness", "unknown"),
            "freshness": row.get("freshness") or "unknown",
            "fetched_at": row.get("last_checked"),
            "data_gap": "" if row.get("used_for_calculation") else row.get("caveat"),
            "not_financial_advice": True,
        }
        for row in _records(provider_capabilities.get("cards"))
    ]
    lab_payload = build_options_lab_page_payload(demo_mode=True)
    greeks_rows = _records(lab_payload.get("greeks_table"))
    raw_scenario_table = _records(lab_payload.get("scenario_table"))
    scenario_table: list[dict[str, Any]] = []
    for row in raw_scenario_table:
        nested = _records(row.get("rows"))
        if nested:
            scenario_table.extend(nested)
        else:
            scenario_table.append(row)
    strategy_templates = _records(lab_payload.get("strategy_templates"))
    source_rows = [
        _source_row(options, provider="equity_options", source=f"{symbol}:options_gamma_proxy"),
        *[_source_row(row, provider="options_lab", source=f"{symbol}:provider_capability") for row in capability_rows],
    ]
    unavailable = [
        row
        for row in source_rows
        if str(row.get("source_status") or row.get("status") or "").lower() in {"missing-key", "unavailable", "provider-required"}
        or row.get("availability") == "unavailable"
    ]
    data_gaps = sorted(
        {
            str(gap)
            for gap in [
                options.get("data_gap"),
                provider_capabilities.get("missing_option_chain_caveat"),
                provider_capabilities.get("no_live_data_caveat"),
                *[row.get("data_gap") for row in scenarios],
            ]
            if gap and str(gap) != "None"
        }
    )
    return {
        "options_quant_version": OPTIONS_QUANT_VERSION,
        "workspace": "options-quant",
        "symbol": symbol,
        "options_gamma_proxy": options,
        "provider_capabilities": capability_rows,
        "pricing_preview": lab_payload.get("price_card") or {},
        "greeks_table": greeks_rows,
        "scenario_table": scenario_table[:15],
        "strategy_templates": strategy_templates,
        "scenario_matrix": scenarios,
        "source_register": source_rows,
        "unavailable_sources": unavailable,
        "data_gaps": data_gaps,
        "readiness": {
            "live_option_chain_claimed": False,
            "gex_claimed": False,
            "dealer_positioning_claimed": False,
            "broker_execution_added": False,
            "account_action_added": False,
            "manual_calculator_available": True,
            "provider_required": True,
        },
        "command_routes": [
            {"raw": f"{symbol} OMON", "target_view": "options-quant", "source_status": "provider-required", "not_financial_advice": True},
            {"raw": "PRICE OPTION", "target_view": "options-quant", "source_status": "supplied", "not_financial_advice": True},
            {"raw": "SOLVE IV", "target_view": "options-quant", "source_status": "supplied", "not_financial_advice": True},
        ],
        "summary": {
            "workspace": "options-quant",
            "symbol": symbol,
            "capability_count": len(capability_rows),
            "greeks_row_count": len(greeks_rows),
            "scenario_row_count": len(scenario_table),
            "source_status": options.get("source_status") or "provider-required",
            "provider_required_count": len(unavailable),
            "non_advisory": True,
            "broker_execution_added": False,
        },
        "caveat": "Options/Quant is a research-only readiness and calculator surface; no live GEX, flow, dealer positioning, or account action is claimed.",
    }


def _heatmap_tile_to_drilldown(row: dict[str, Any]) -> dict[str, Any]:
    symbol = str(row.get("symbol") or "")
    tile = {
        "label": symbol,
        "group": row.get("sector"),
        "raw": {
            "ticker": symbol,
            "symbol": symbol,
            "asset_class": row.get("asset_class") or row.get("sector") or "equity",
            "sector": row.get("sector"),
            "provider": row.get("provider"),
        },
    }
    target = build_heatmap_drilldown_target(tile)
    target_view = "crypto-intelligence" if "CRYPTO" in target.get("command", "") else "equity-intelligence"
    return {
        "symbol": symbol,
        "label": row.get("label") or symbol,
        "sector": row.get("sector"),
        "industry": row.get("industry"),
        "daily_return_pct": row.get("daily_return_pct"),
        "market_cap_weight": row.get("market_cap_weight"),
        "color_bucket": row.get("color_bucket"),
        "target_command": target.get("command"),
        "legacy_streamlit_page": target.get("page"),
        "target_view": target_view,
        "web_href": (
            f"/?view=asset&symbol={target.get('symbol', 'AAPL')}&assetClass="
            f"{'crypto' if target_view == 'crypto-intelligence' else 'equity'}&timeframe=1D&mode=fixture"
        ),
        "provider": row.get("provider") or "market_intelligence",
        "source_status": row.get("source_status") or "fixture",
        "freshness": row.get("freshness") or row.get("source_status") or "fixture",
        "fetched_at": row.get("fetched_at"),
        "confidence": row.get("confidence"),
        "caveat": row.get("caveat") or "Heatmap drilldown is schema-driven and non-advisory.",
        "data_gap": row.get("data_gap") or "Live drilldown requires provider-backed symbol data.",
        "not_financial_advice": True,
    }


def build_screener_drilldown_contract(
    *,
    include_runtime: bool = False,
    market_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    market = market_contract or build_market_intelligence_contract(include_runtime=include_runtime)
    heatmap_rows = _records(market.get("market_heatmap"))
    drilldowns = [_heatmap_tile_to_drilldown(row) for row in heatmap_rows]
    sectors = sorted({str(row.get("sector")) for row in drilldowns if row.get("sector")})
    sector_rows = []
    for sector in sectors:
        members = [row for row in drilldowns if row.get("sector") == sector]
        sector_rows.append(
            {
                "sector": sector,
                "tile_count": len(members),
                "weight": round(sum(float(row.get("market_cap_weight") or 0) for row in members), 4),
                "strongest_symbol": max(members, key=lambda row: float(row.get("daily_return_pct") or 0)).get("symbol"),
                "weakest_symbol": min(members, key=lambda row: float(row.get("daily_return_pct") or 0)).get("symbol"),
                "provider": "market_intelligence",
                "source_status": "fixture",
                "freshness": "fixture",
                "fetched_at": members[0].get("fetched_at") if members else None,
                "caveat": "Sector summary is derived from source-labeled heatmap rows.",
                "data_gap": "Live screener mode requires provider-backed universe, returns, and fundamentals.",
                "not_financial_advice": True,
            }
        )
    source_rows = [
        _source_row(row, provider="market_intelligence", source=f"heatmap:{row.get('symbol')}")
        for row in drilldowns
    ]
    return {
        "screener_drilldown_version": SCREENER_DRILLDOWN_VERSION,
        "workspace": "screener-drilldown",
        "drilldown_tiles": drilldowns,
        "sector_summaries": sector_rows,
        "source_register": source_rows,
        "unavailable_sources": [
            {
                "provider": "screener_live_universe",
                "source": "provider-backed screener",
                "status": "provider-required",
                "source_status": "provider-required",
                "availability": "unavailable",
                "row_count": 0,
                "fetched_at": None,
                "recommended_action": "Wire a provider-backed screener universe before claiming live drilldown.",
                "caveat": "Fixture heatmap rows are useful for UI and routing, not live screening.",
                "data_gap": "No live screener universe is exported in deterministic fixture mode.",
                "not_financial_advice": True,
            }
        ],
        "summary": {
            "workspace": "screener-drilldown",
            "tile_count": len(drilldowns),
            "sector_count": len(sector_rows),
            "runtime_requested": bool(include_runtime),
            "source_status": "fixture" if drilldowns else "unavailable",
            "non_advisory": True,
            "broker_execution_added": False,
        },
        "caveat": "Screener drilldown maps heatmap tiles to research workstations; it is not a recommendation or live screener claim.",
    }
