from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .chart_specs import build_chart_spec, provider_status_row, record_series, safe_number


EQUITY_INTELLIGENCE_VERSION = "equity_intelligence.v1"
FIXTURE_FETCHED_AT = "2026-06-16T00:00:00+00:00"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fixture_price_history(symbol: str) -> list[dict[str, Any]]:
    closes = [171.2, 173.8, 176.4, 174.9, 179.1, 182.6, 181.3, 185.8, 188.4, 186.5, 190.2, 193.6]
    rows = []
    for idx, close in enumerate(closes, start=1):
        rows.append(
            {
                "date": f"2026-{idx:02d}-15",
                "open": round(close * 0.992, 2),
                "high": round(close * 1.018, 2),
                "low": round(close * 0.982, 2),
                "close": close,
                "volume": 52_000_000 + idx * 1_100_000,
                "symbol": symbol,
                "provider": "fixture",
                "source_status": "fixture",
                "freshness": "fixture",
                "fetched_at": FIXTURE_FETCHED_AT,
                "caveat": "Deterministic price-history fixture for web workstation rendering.",
                "data_gap": "Not live market data; use runtime provider status for live claims.",
                "not_financial_advice": True,
            }
        )
    return rows


def _fixture_contract(symbol: str) -> dict[str, Any]:
    price_history = _fixture_price_history(symbol)
    latest = price_history[-1]["close"]
    technical = {
        "symbol": symbol,
        "latest_price": latest,
        "price_vs_50dma": 0.038,
        "price_vs_200dma": 0.092,
        "rsi": 58.4,
        "rsi_bucket": "Neutral / mixed evidence",
        "macd_regime": "Constructive technical backdrop",
        "realized_volatility": 0.21,
        "range_52w_position": 0.74,
        "drawdown_from_52w_high": -0.041,
        "support": 184.2,
        "resistance": 198.8,
        "provider": "fixture",
        "source_status": "fixture",
        "freshness": "fixture",
        "fetched_at": FIXTURE_FETCHED_AT,
        "caveat": "Technical diagnostics mirror Stock Analyzer fields but are deterministic in fixture mode.",
        "data_gap": "Live yfinance history not requested for fixture export.",
        "not_financial_advice": True,
    }
    financial_overview = {
        "symbol": symbol,
        "company_name": "Apple Inc. fixture profile",
        "sector": "Technology",
        "market_cap": 2_950_000_000_000,
        "revenue_growth_proxy": 0.061,
        "gross_margin_proxy": 0.46,
        "free_cashflow_margin_proxy": 0.27,
        "provider": "fixture",
        "source_status": "fixture",
        "freshness": "fixture",
        "fetched_at": FIXTURE_FETCHED_AT,
        "caveat": "Financial overview is fixture-safe profile context until a fundamentals provider is live or cached.",
        "data_gap": "Full statements, estimates, and segment tables remain provider-gated.",
        "not_financial_advice": True,
    }
    valuation_quality = [
        {
            "metric": "statement coverage",
            "status": "schema-ready",
            "score": 62,
            "provider": "financial_terminal",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": "Coverage score indicates which statement sections can be rendered when provider rows exist.",
            "data_gap": "Fixture mode does not include provider-backed statements.",
            "not_financial_advice": True,
        },
        {
            "metric": "ratio availability",
            "status": "partial",
            "score": 48,
            "provider": "financial_terminal",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": "Ratio availability is a readiness signal, not a valuation opinion.",
            "data_gap": "Optional fundamentals provider rows are not bundled.",
            "not_financial_advice": True,
        },
    ]
    options_gamma_proxy = {
        "symbol": symbol,
        "put_call_open_interest_ratio": None,
        "put_call_volume_ratio": None,
        "largest_oi_strikes": [],
        "expiry_concentration": [],
        "provider": "yfinance options",
        "source_status": "provider-required",
        "freshness": "provider-gated",
        "fetched_at": None,
        "caveat": "Options/gamma is an explicit readiness surface; no dealer positioning is claimed.",
        "data_gap": "Options chain provider is not called during deterministic fixture export.",
        "not_financial_advice": True,
    }
    news_events = [
        {
            "event_id": "equity-fixture-supply-chain",
            "title": f"{symbol} supply-chain watch context",
            "region": "Asia",
            "severity": "watch",
            "provider": "fixture",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": FIXTURE_FETCHED_AT,
            "related_assets": [symbol, "QQQ", "SOXX"],
            "caveat": "Fixture event row demonstrates news-to-asset linkage only.",
            "data_gap": "Live company news is provider-gated.",
            "not_financial_advice": True,
        }
    ]
    scenario_matrix = [
        {
            "scenario": "Constructive continuation",
            "evidence_weight": 64,
            "evidence_summary": "Trend, relative strength, and participation evidence are reviewed for continuation context.",
            "source_status": "fixture",
            "provider": "equity_scenarios",
            "caveat": "Evidence weight is not prediction certainty.",
            "data_gap": "Fixture evidence; live scenario matrix requires provider history.",
            "not_financial_advice": True,
        },
        {
            "scenario": "Range digestion",
            "evidence_weight": 50,
            "evidence_summary": "Mixed momentum can support range behavior while provider evidence is incomplete.",
            "source_status": "fixture",
            "provider": "equity_scenarios",
            "caveat": "Scenario is research context only.",
            "data_gap": "Fixture evidence; live scenario matrix requires provider history.",
            "not_financial_advice": True,
        },
        {
            "scenario": "Downside deterioration",
            "evidence_weight": 36,
            "evidence_summary": "Weak trend or breadth deterioration can elevate downside risk context.",
            "source_status": "fixture",
            "provider": "equity_scenarios",
            "caveat": "Scenario is not a market action instruction.",
            "data_gap": "Fixture evidence; live scenario matrix requires provider history.",
            "not_financial_advice": True,
        },
        {
            "scenario": "Event volatility",
            "evidence_weight": 45,
            "evidence_summary": "Catalyst calendars and options readiness can raise volatility context.",
            "source_status": "provider-required",
            "provider": "equity_options",
            "caveat": "Options data is provider-gated and may be delayed or unavailable.",
            "data_gap": "No options chain rows in deterministic fixture mode.",
            "not_financial_advice": True,
        },
    ]
    chart_specs = _equity_chart_specs(symbol, price_history, scenario_matrix, valuation_quality, source_status="fixture")
    provider_status = _provider_rows(symbol, price_history, chart_specs, [technical], [options_gamma_proxy])
    return _assemble_contract(
        symbol=symbol,
        price_history=price_history,
        technical_diagnostics=technical,
        financial_overview=financial_overview,
        valuation_quality=valuation_quality,
        options_gamma_proxy=options_gamma_proxy,
        news_events=news_events,
        scenario_matrix=scenario_matrix,
        chart_specs=chart_specs,
        provider_status=provider_status,
        include_runtime=False,
    )


def _runtime_contract(symbol: str) -> dict[str, Any] | None:
    try:
        from .equity_scenarios import compute_equity_flow_proxy, compute_equity_scenario_matrix, compute_equity_technical_diagnostics
        from .financial_terminal import build_financial_terminal_state
        from .market_data import fetch_price_history
        from .options_flow import build_options_dashboard

        history, history_status = fetch_price_history(symbol, period="1y")
        price_history = _records_from_frame(history)
        for row in price_history:
            row.update(
                {
                    "symbol": symbol,
                    "provider": "yfinance",
                    "source_status": "live/fresh" if history_status.ok else "unavailable",
                    "freshness": "live/fresh" if history_status.ok else "unavailable",
                    "fetched_at": history_status.fetched_at.isoformat(),
                    "caveat": "Free market-data runtime row; inspect provider freshness.",
                    "data_gap": "" if history_status.ok else history_status.error,
                    "not_financial_advice": True,
                }
            )
        if not price_history:
            return None
        technical, tech_status = compute_equity_technical_diagnostics(symbol)
        flow, flow_status = compute_equity_flow_proxy(symbol)
        scenario_frame, scenario_status = compute_equity_scenario_matrix(symbol)
        scenario_matrix = _mark_rows_non_advisory(_records_from_frame(scenario_frame))
        financial_state = build_financial_terminal_state(symbol)
        options_dashboard = build_options_dashboard(symbol)
        financial_overview = _financial_runtime_overview(symbol, financial_state)
        options_proxy = _options_runtime_proxy(symbol, options_dashboard)
        valuation_quality = _valuation_runtime_rows(financial_state)
        chart_specs = _equity_chart_specs(symbol, price_history, scenario_matrix, valuation_quality, source_status="live/fresh")
        provider_status = [
            history_status.to_dict(),
            tech_status.to_dict(),
            flow_status.to_dict(),
            scenario_status.to_dict(),
            *[provider_status_row(provider=chart["provider"], source=chart["chart_id"], status=chart["source_status"], availability="limited", row_count=0, fetched_at=chart["fetched_at"], caveat=chart["caveat"], data_gap=chart["data_gap"]) for chart in chart_specs],
        ]
        return _assemble_contract(
            symbol=symbol,
            price_history=price_history,
            technical_diagnostics={
                **technical,
                "provider": "equity_scenarios",
                "source_status": "live/fresh" if tech_status.ok else "unavailable",
                "fetched_at": tech_status.fetched_at.isoformat(),
                "not_financial_advice": True,
            },
            financial_overview=financial_overview,
            valuation_quality=valuation_quality,
            options_gamma_proxy=options_proxy,
            news_events=[],
            scenario_matrix=scenario_matrix,
            chart_specs=chart_specs,
            provider_status=provider_status,
            include_runtime=True,
        )
    except Exception:
        return None


def _mark_rows_non_advisory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**row, "not_financial_advice": True} for row in rows]


def _records_from_frame(value: Any, limit: int | None = None) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        rows = value.tail(limit).to_dict(orient="records") if limit else value.to_dict(orient="records")
    elif isinstance(value, list):
        rows = [dict(item) for item in value if isinstance(item, dict)]
    else:
        rows = []
    output = []
    for row in rows:
        clean = {}
        for key, item in row.items():
            if hasattr(item, "isoformat"):
                clean[str(key)] = item.isoformat()
            else:
                clean[str(key)] = item
        output.append(clean)
    return output


def _financial_runtime_overview(symbol: str, state: dict[str, Any]) -> dict[str, Any]:
    header = state.get("company_header") if isinstance(state, dict) else {}
    overview = state.get("financial_overview") if isinstance(state, dict) else {}
    return {
        "symbol": symbol,
        "company_name": (header or {}).get("longName") or (header or {}).get("shortName") or symbol,
        "sector": (header or {}).get("sector"),
        "market_cap": (header or {}).get("marketCap"),
        "revenue_growth_proxy": None,
        "gross_margin_proxy": None,
        "free_cashflow_margin_proxy": None,
        "provider": "financial_terminal",
        "source_status": "cached" if overview else "unavailable",
        "freshness": "cached" if overview else "unavailable",
        "fetched_at": _now_iso(),
        "caveat": "Runtime financial state is provider-dependent and may be sparse.",
        "data_gap": "" if overview else "Financial overview unavailable from runtime provider.",
        "not_financial_advice": True,
    }


def _valuation_runtime_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    availability = state.get("data_availability") if isinstance(state, dict) else {}
    rows = _records_from_frame(availability) if availability is not None else []
    if rows:
        return [
            {
                "metric": row.get("dataset") or row.get("metric") or "financial availability",
                "status": "available" if row.get("available") else "unavailable",
                "score": 100 if row.get("available") else 0,
                "provider": row.get("provider") or "financial_terminal",
                "source_status": "cached",
                "freshness": "cached",
                "fetched_at": _now_iso(),
                "caveat": "Availability row from runtime financial terminal state.",
                "data_gap": row.get("data_gap") or "",
                "not_financial_advice": True,
            }
            for row in rows[:8]
        ]
    return []


def _options_runtime_proxy(symbol: str, dashboard: dict[str, Any]) -> dict[str, Any]:
    summary = dashboard.get("summary") if isinstance(dashboard, dict) else {}
    return {
        "symbol": symbol,
        "put_call_open_interest_ratio": (summary or {}).get("put_call_open_interest_ratio"),
        "put_call_volume_ratio": (summary or {}).get("put_call_volume_ratio"),
        "largest_oi_strikes": dashboard.get("largest_oi_strikes") if isinstance(dashboard, dict) else [],
        "expiry_concentration": dashboard.get("expiry_concentration") if isinstance(dashboard, dict) else [],
        "provider": "yfinance options",
        "source_status": "cached" if dashboard else "unavailable",
        "freshness": "cached" if dashboard else "unavailable",
        "fetched_at": _now_iso(),
        "caveat": "Options rows are delayed/proxy estimates and do not imply dealer positioning.",
        "data_gap": "" if dashboard else "Options dashboard unavailable from runtime provider.",
        "not_financial_advice": True,
    }


def _equity_chart_specs(
    symbol: str,
    price_history: list[dict[str, Any]],
    scenario_matrix: list[dict[str, Any]],
    valuation_quality: list[dict[str, Any]],
    *,
    source_status: str,
) -> list[dict[str, Any]]:
    fetched_at = price_history[-1].get("fetched_at") if price_history else FIXTURE_FETCHED_AT
    provider = price_history[-1].get("provider") if price_history else "fixture"
    return [
        build_chart_spec(
            chart_id=f"{symbol}.price",
            chart_type="line",
            title=f"{symbol} Price History",
            series=[record_series(price_history, x_key="date", y_key="close", name="close")],
            unit="price",
            provider=provider,
            source_status=source_status,
            fetched_at=fetched_at,
            caveat="Price chart is research context with visible source status.",
            data_gap="Fixture mode is not live market data." if source_status == "fixture" else "",
        ),
        build_chart_spec(
            chart_id=f"{symbol}.volume",
            chart_type="bar",
            title=f"{symbol} Volume Context",
            series=[record_series(price_history, x_key="date", y_key="volume", name="volume")],
            unit="shares",
            provider=provider,
            source_status=source_status,
            fetched_at=fetched_at,
            caveat="Volume chart is provider-dependent and may be delayed.",
            data_gap="Fixture mode is not live volume." if source_status == "fixture" else "",
        ),
        build_chart_spec(
            chart_id=f"{symbol}.scenario_weights",
            chart_type="bar",
            title="Scenario Evidence Weights",
            x_axis="scenario",
            y_axis="evidence_weight",
            series=[record_series(scenario_matrix, x_key="scenario", y_key="evidence_weight", name="evidence weight")],
            unit="score",
            provider="equity_scenarios",
            source_status="inferred/proxy" if source_status == "fixture" else "cached",
            fetched_at=fetched_at,
            caveat="Evidence weights are transparent scenario context, not forecasts.",
            data_gap="Options and fundamental rows can be unavailable.",
        ),
        build_chart_spec(
            chart_id=f"{symbol}.valuation_quality",
            chart_type="heat",
            title="Financial Data Readiness",
            x_axis="metric",
            y_axis="score",
            series=[record_series(valuation_quality, x_key="metric", y_key="score", name="coverage")],
            unit="score",
            provider="financial_terminal",
            source_status="fixture" if source_status == "fixture" else "cached",
            fetched_at=fetched_at,
            caveat="Readiness chart shows data availability, not valuation advice.",
            data_gap="Provider-backed statements may be unavailable.",
        ),
    ]


def _provider_rows(
    symbol: str,
    price_history: list[dict[str, Any]],
    chart_specs: list[dict[str, Any]],
    diagnostic_rows: list[dict[str, Any]],
    options_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [
        provider_status_row(
            provider="fixture",
            source=f"Phase 5A equity fixture:{symbol}",
            status="fixture",
            availability="limited",
            row_count=len(price_history),
            fetched_at=FIXTURE_FETCHED_AT,
            caveat="Deterministic fixture used for static web export.",
            data_gap="Runtime yfinance/fundamental/options providers are not called during fixture export.",
        )
    ]
    for item in [*diagnostic_rows, *options_rows]:
        rows.append(
            provider_status_row(
                provider=str(item.get("provider") or "unknown"),
                source=symbol,
                status=str(item.get("source_status") or "unavailable"),
                availability="limited" if item.get("source_status") != "unavailable" else "unavailable",
                row_count=1,
                fetched_at=item.get("fetched_at"),
                caveat=str(item.get("caveat") or ""),
                data_gap=str(item.get("data_gap") or ""),
            )
        )
    rows.extend(
        provider_status_row(
            provider=chart["provider"],
            source=chart["chart_id"],
            status=chart["source_status"],
            availability="limited",
            row_count=sum(len(series.get("points", [])) for series in chart.get("series", [])),
            fetched_at=chart.get("fetched_at"),
            caveat=chart.get("caveat", ""),
            data_gap=chart.get("data_gap", ""),
        )
        for chart in chart_specs
    )
    return rows


def _assemble_contract(
    *,
    symbol: str,
    price_history: list[dict[str, Any]],
    technical_diagnostics: dict[str, Any],
    financial_overview: dict[str, Any],
    valuation_quality: list[dict[str, Any]],
    options_gamma_proxy: dict[str, Any],
    news_events: list[dict[str, Any]],
    scenario_matrix: list[dict[str, Any]],
    chart_specs: list[dict[str, Any]],
    provider_status: list[dict[str, Any]],
    include_runtime: bool,
) -> dict[str, Any]:
    data_gaps = []
    for collection in [price_history, valuation_quality, news_events, scenario_matrix, provider_status]:
        data_gaps.extend(str(row.get("data_gap")) for row in collection if isinstance(row, dict) and row.get("data_gap"))
    for item in [technical_diagnostics, financial_overview, options_gamma_proxy]:
        if item.get("data_gap"):
            data_gaps.append(str(item["data_gap"]))
    latest_price = safe_number(price_history[-1].get("close")) if price_history else None
    return {
        "equity_intelligence_version": EQUITY_INTELLIGENCE_VERSION,
        "workspace": "equity-intelligence",
        "symbol": symbol,
        "price_history": price_history,
        "technical_diagnostics": technical_diagnostics,
        "financial_overview": financial_overview,
        "valuation_quality": valuation_quality,
        "options_gamma_proxy": options_gamma_proxy,
        "news_events": news_events,
        "scenario_matrix": scenario_matrix,
        "chart_specs": chart_specs,
        "provider_status": provider_status,
        "data_gaps": sorted({gap for gap in data_gaps if gap and gap != "None"}),
        "command_routes": [
            {"raw": f"{symbol} FA", "target_view": "equity-intelligence", "source_status": "schema-ready", "not_financial_advice": True},
            {"raw": f"{symbol} DES", "target_view": "financial-fundamentals", "source_status": "schema-ready", "not_financial_advice": True},
            {"raw": f"{symbol} OMON", "target_view": "options-quant", "source_status": "provider-required", "not_financial_advice": True},
        ],
        "summary": {
            "workspace": "equity-intelligence",
            "symbol": symbol,
            "latest_price": latest_price,
            "price_row_count": len(price_history),
            "scenario_count": len(scenario_matrix),
            "chart_count": len(chart_specs),
            "runtime_requested": bool(include_runtime),
            "source_status": price_history[-1].get("source_status") if price_history else "unavailable",
            "non_advisory": True,
            "broker_execution_added": False,
        },
        "caveat": "Equity Intelligence is research context with source labels and explicit provider gaps.",
    }


def build_equity_intelligence_contract(symbol: str = "AAPL", *, include_runtime: bool = False) -> dict[str, Any]:
    normalized = "".join(ch for ch in (symbol or "AAPL").upper() if ch.isalnum() or ch in {".", "-", "="})[:16] or "AAPL"
    if include_runtime:
        runtime = _runtime_contract(normalized)
        if runtime:
            return runtime
    return _fixture_contract(normalized)
