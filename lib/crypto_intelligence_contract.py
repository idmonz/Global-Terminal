from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .chart_specs import build_chart_spec, provider_status_row, record_series, safe_number


CRYPTO_INTELLIGENCE_VERSION = "crypto_intelligence.v1"
FIXTURE_FETCHED_AT = "2026-06-16T00:00:00+00:00"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fixture_timeseries(symbol: str) -> dict[str, list[dict[str, Any]]]:
    price = [63300, 64150, 63820, 64980, 65840, 65260, 66400]
    oi = [18.2, 18.6, 18.4, 19.1, 19.7, 19.4, 20.2]
    funding = [0.004, 0.006, 0.002, 0.008, 0.01, 0.007, 0.009]
    taker = [1.02, 0.98, 1.05, 1.12, 1.08, 1.01, 1.16]
    long_short = [1.18, 1.2, 1.17, 1.25, 1.29, 1.22, 1.27]
    rows = []
    for idx in range(len(price)):
        rows.append(
            {
                "timestamp": f"2026-06-{10 + idx:02d}T00:00:00+00:00",
                "symbol": symbol,
                "close": price[idx],
                "open_interest_billions": oi[idx],
                "funding_rate_bps": funding[idx] * 10000,
                "taker_buy_sell_ratio": taker[idx],
                "long_short_ratio": long_short[idx],
                "provider": "fixture",
                "source_status": "fixture",
                "freshness": "fixture",
                "fetched_at": FIXTURE_FETCHED_AT,
                "caveat": "Deterministic crypto derivatives fixture for web workstation rendering.",
                "data_gap": "Not live Binance/CoinGecko data; use runtime provider status for live claims.",
                "not_financial_advice": True,
            }
        )
    return {"derivatives_timeseries": rows}


def _fixture_contract(symbol: str) -> dict[str, Any]:
    timeseries = _fixture_timeseries(symbol)["derivatives_timeseries"]
    last = timeseries[-1]
    market_overview = {
        "symbol": symbol,
        "current_price": last["close"],
        "market_cap_proxy": 1_310_000_000_000,
        "total_volume_proxy": 38_000_000_000,
        "asset_rank_proxy": 1,
        "provider": "fixture",
        "source_status": "fixture",
        "freshness": "fixture",
        "fetched_at": FIXTURE_FETCHED_AT,
        "caveat": "Fixture market overview mirrors CoinGecko-style fields without live claims.",
        "data_gap": "Live CoinGecko markets are not called during fixture export.",
        "not_financial_advice": True,
    }
    derivatives_snapshot = {
        "symbol": symbol,
        "mark_price": last["close"],
        "premium_pct": 0.08,
        "open_interest_billions": last["open_interest_billions"],
        "funding_rate_bps": last["funding_rate_bps"],
        "taker_buy_sell_ratio": last["taker_buy_sell_ratio"],
        "global_long_short_ratio": last["long_short_ratio"],
        "provider": "fixture",
        "source_status": "fixture",
        "freshness": "fixture",
        "fetched_at": FIXTURE_FETCHED_AT,
        "caveat": "Derivatives snapshot is fixture-safe and non-advisory.",
        "data_gap": "Live Binance futures endpoints are not called during fixture export.",
        "not_financial_advice": True,
    }
    liquidation_pressure_proxy = [
        {
            "band": "lower liquidity pocket",
            "price_level": 62000,
            "pressure_score": 42,
            "side": "downside exposure context",
            "provider": "crypto_scenarios",
            "source_status": "inferred/proxy",
            "freshness": "inferred/proxy",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": "Pressure score is a transparent proxy, not exchange account data.",
            "data_gap": "No liquidation order-book feed is bundled.",
            "not_financial_advice": True,
        },
        {
            "band": "upper liquidity pocket",
            "price_level": 69000,
            "pressure_score": 57,
            "side": "upside exposure context",
            "provider": "crypto_scenarios",
            "source_status": "inferred/proxy",
            "freshness": "inferred/proxy",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": "Pressure score is a transparent proxy, not exchange account data.",
            "data_gap": "No liquidation order-book feed is bundled.",
            "not_financial_advice": True,
        },
    ]
    scenario_matrix = [
        {
            "scenario": "Liquidity continuation",
            "evidence_weight": 61,
            "evidence_summary": "Open interest, funding, and taker flow are reviewed as transparent context.",
            "provider": "crypto_scenarios",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": "Scenario is research context only.",
            "data_gap": "Fixture evidence; live provider rows are not requested.",
            "not_financial_advice": True,
        },
        {
            "scenario": "Leverage reset",
            "evidence_weight": 47,
            "evidence_summary": "Funding and open-interest concentration can indicate reset risk context.",
            "provider": "crypto_scenarios",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": "Scenario is not an instruction.",
            "data_gap": "No liquidation feed is bundled.",
            "not_financial_advice": True,
        },
        {
            "scenario": "Range compression",
            "evidence_weight": 52,
            "evidence_summary": "Mixed derivatives evidence can support range context.",
            "provider": "crypto_scenarios",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": "Scenario is non-advisory context.",
            "data_gap": "Fixture evidence; live vol/order-book feeds are unavailable.",
            "not_financial_advice": True,
        },
    ]
    chart_specs = _crypto_chart_specs(symbol, timeseries, scenario_matrix, liquidation_pressure_proxy, source_status="fixture")
    provider_status = _provider_rows(symbol, timeseries, chart_specs, [market_overview, derivatives_snapshot], liquidation_pressure_proxy)
    return _assemble_contract(
        symbol=symbol,
        market_overview=market_overview,
        derivatives_snapshot=derivatives_snapshot,
        derivatives_timeseries=timeseries,
        funding=timeseries,
        open_interest=timeseries,
        taker_flow=timeseries,
        long_short_bias=timeseries,
        liquidation_pressure_proxy=liquidation_pressure_proxy,
        scenario_matrix=scenario_matrix,
        chart_specs=chart_specs,
        provider_status=provider_status,
        include_runtime=False,
    )


def _runtime_contract(symbol: str) -> dict[str, Any] | None:
    try:
        from .crypto_derivatives import build_derivatives_snapshot, build_derivatives_timeseries
        from .crypto_prices import get_crypto_market_overview
        from .crypto_scenarios import crypto_scenario_matrix, estimate_liquidation_pressure_map

        overview, overview_status = get_crypto_market_overview()
        snapshot, snapshot_status = build_derivatives_snapshot(symbol)
        ts_payload, ts_status = build_derivatives_timeseries(symbol, limit=80)
        klines = _records_from_frame(ts_payload.get("klines") if isinstance(ts_payload, dict) else [])
        oi_rows = _mark_rows_non_advisory(_records_from_frame(ts_payload.get("open_interest") if isinstance(ts_payload, dict) else []))
        funding_rows = _mark_rows_non_advisory(_records_from_frame(ts_payload.get("funding") if isinstance(ts_payload, dict) else []))
        taker_rows = _mark_rows_non_advisory(_records_from_frame(ts_payload.get("taker") if isinstance(ts_payload, dict) else []))
        ratio_rows = _mark_rows_non_advisory(_records_from_frame(ts_payload.get("global_long_short") if isinstance(ts_payload, dict) else []))
        merged = _merge_crypto_timeseries(symbol, klines, oi_rows, funding_rows, taker_rows, ratio_rows, ts_status)
        if not merged:
            return None
        pressure_frame, pressure_status = estimate_liquidation_pressure_map(
            klines=ts_payload.get("klines") if isinstance(ts_payload, dict) else None,
            oi_history=ts_payload.get("open_interest") if isinstance(ts_payload, dict) else None,
            snapshot=snapshot,
        )
        pressure = _mark_rows_non_advisory(_records_from_frame(pressure_frame) or [])
        scenarios = _mark_rows_non_advisory(_records_from_frame(
            crypto_scenario_matrix(
                symbol=symbol,
                klines=ts_payload.get("klines") if isinstance(ts_payload, dict) else None,
                oi_history=ts_payload.get("open_interest") if isinstance(ts_payload, dict) else None,
                snapshot=snapshot,
                pressure_map=pressure_frame,
            )
        ) or [])
        chart_specs = _crypto_chart_specs(symbol, merged, scenarios, pressure, source_status="live/fresh" if ts_status.ok else "unavailable")
        provider_status = [overview_status.to_dict(), snapshot_status.to_dict(), ts_status.to_dict(), pressure_status.to_dict()]
        provider_status.extend(
            provider_status_row(provider=chart["provider"], source=chart["chart_id"], status=chart["source_status"], availability="limited", row_count=0, fetched_at=chart["fetched_at"], caveat=chart["caveat"], data_gap=chart["data_gap"])
            for chart in chart_specs
        )
        return _assemble_contract(
            symbol=symbol,
            market_overview={
                **overview,
                "symbol": symbol,
                "provider": "CoinGecko",
                "source_status": "live/fresh" if overview_status.ok else "unavailable",
                "fetched_at": overview_status.fetched_at.isoformat(),
                "not_financial_advice": True,
            },
            derivatives_snapshot={
                **snapshot,
                "provider": "Binance USD-M Futures",
                "source_status": "live/fresh" if snapshot_status.ok else "unavailable",
                "fetched_at": snapshot_status.fetched_at.isoformat(),
                "not_financial_advice": True,
            },
            derivatives_timeseries=merged,
            funding=funding_rows,
            open_interest=oi_rows,
            taker_flow=taker_rows,
            long_short_bias=ratio_rows,
            liquidation_pressure_proxy=pressure,
            scenario_matrix=scenarios,
            chart_specs=chart_specs,
            provider_status=provider_status,
            include_runtime=True,
        )
    except Exception:
        return None


def _mark_rows_non_advisory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**row, "not_financial_advice": True} for row in rows]


def _records_from_frame(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        rows = value.to_dict(orient="records")
    elif isinstance(value, list):
        rows = [dict(item) for item in value if isinstance(item, dict)]
    else:
        rows = []
    output = []
    for row in rows:
        clean = {}
        for key, item in row.items():
            clean[str(key)] = item.isoformat() if hasattr(item, "isoformat") else item
        output.append(clean)
    return output


def _merge_crypto_timeseries(
    symbol: str,
    klines: list[dict[str, Any]],
    oi_rows: list[dict[str, Any]],
    funding_rows: list[dict[str, Any]],
    taker_rows: list[dict[str, Any]],
    ratio_rows: list[dict[str, Any]],
    status: Any,
) -> list[dict[str, Any]]:
    rows = []
    max_len = max(len(klines), len(oi_rows), len(funding_rows), len(taker_rows), len(ratio_rows))
    for idx in range(max_len):
        kline = klines[idx] if idx < len(klines) else {}
        oi = oi_rows[idx] if idx < len(oi_rows) else {}
        funding = funding_rows[idx] if idx < len(funding_rows) else {}
        taker = taker_rows[idx] if idx < len(taker_rows) else {}
        ratio = ratio_rows[idx] if idx < len(ratio_rows) else {}
        rows.append(
            {
                "timestamp": kline.get("close_time") or oi.get("timestamp") or funding.get("funding_time") or taker.get("timestamp") or ratio.get("timestamp"),
                "symbol": symbol,
                "close": kline.get("close"),
                "open_interest_billions": (safe_number(oi.get("sum_open_interest_value")) or 0) / 1_000_000_000 if oi.get("sum_open_interest_value") is not None else None,
                "funding_rate_bps": (safe_number(funding.get("funding_rate")) or 0) * 10000 if funding.get("funding_rate") is not None else None,
                "taker_buy_sell_ratio": taker.get("buy_sell_ratio"),
                "long_short_ratio": ratio.get("long_short_ratio"),
                "provider": "Binance USD-M Futures",
                "source_status": "live/fresh" if status.ok else "unavailable",
                "freshness": "live/fresh" if status.ok else "unavailable",
                "fetched_at": status.fetched_at.isoformat(),
                "caveat": "Runtime public Binance derivatives row; inspect provider status.",
                "data_gap": "" if status.ok else status.error,
                "not_financial_advice": True,
            }
        )
    return rows


def _crypto_chart_specs(
    symbol: str,
    timeseries: list[dict[str, Any]],
    scenario_matrix: list[dict[str, Any]],
    pressure: list[dict[str, Any]],
    *,
    source_status: str,
) -> list[dict[str, Any]]:
    fetched_at = timeseries[-1].get("fetched_at") if timeseries else FIXTURE_FETCHED_AT
    provider = timeseries[-1].get("provider") if timeseries else "fixture"
    return [
        build_chart_spec(
            chart_id=f"{symbol}.price",
            chart_type="line",
            title=f"{symbol} Price Proxy",
            x_axis="timestamp",
            y_axis="close",
            series=[record_series(timeseries, x_key="timestamp", y_key="close", name="close")],
            unit="price",
            provider=provider,
            source_status=source_status,
            fetched_at=fetched_at,
            caveat="Price proxy uses public/fixture crypto rows and remains non-advisory.",
            data_gap="Fixture mode is not live exchange data." if source_status == "fixture" else "",
        ),
        build_chart_spec(
            chart_id=f"{symbol}.open_interest",
            chart_type="line",
            title="Open Interest Proxy",
            x_axis="timestamp",
            y_axis="open_interest_billions",
            series=[record_series(timeseries, x_key="timestamp", y_key="open_interest_billions", name="open interest")],
            unit="USD billions",
            provider=provider,
            source_status=source_status,
            fetched_at=fetched_at,
            caveat="Open-interest rows depend on public derivatives provider availability.",
            data_gap="Fixture mode is not live Binance data." if source_status == "fixture" else "",
        ),
        build_chart_spec(
            chart_id=f"{symbol}.funding_taker",
            chart_type="multi_line",
            title="Funding And Taker Flow",
            x_axis="timestamp",
            y_axis="mixed",
            series=[
                record_series(timeseries, x_key="timestamp", y_key="funding_rate_bps", name="funding bps"),
                record_series(timeseries, x_key="timestamp", y_key="taker_buy_sell_ratio", name="taker ratio"),
            ],
            unit="mixed",
            provider=provider,
            source_status=source_status,
            fetched_at=fetched_at,
            caveat="Taker flow is market-structure context, not direction advice.",
            data_gap="Fixture mode is not live derivatives data." if source_status == "fixture" else "",
        ),
        build_chart_spec(
            chart_id=f"{symbol}.scenario_weights",
            chart_type="bar",
            title="Crypto Scenario Evidence",
            x_axis="scenario",
            y_axis="evidence_weight",
            series=[record_series(scenario_matrix, x_key="scenario", y_key="evidence_weight", name="evidence weight")],
            unit="score",
            provider="crypto_scenarios",
            source_status="inferred/proxy" if source_status == "fixture" else "cached",
            fetched_at=fetched_at,
            caveat="Scenario evidence is transparent context and not prediction certainty.",
            data_gap="Liquidation/order-book feeds are unavailable unless separately wired.",
        ),
        build_chart_spec(
            chart_id=f"{symbol}.liquidity_pressure",
            chart_type="bar",
            title="Liquidity Pressure Proxy",
            x_axis="band",
            y_axis="pressure_score",
            series=[record_series(pressure, x_key="band", y_key="pressure_score", name="pressure")],
            unit="score",
            provider="crypto_scenarios",
            source_status="inferred/proxy",
            fetched_at=fetched_at,
            caveat="Pressure map is proxy context only.",
            data_gap="No liquidation order-book feed is bundled.",
        ),
    ]


def _provider_rows(
    symbol: str,
    timeseries: list[dict[str, Any]],
    chart_specs: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    pressure: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [
        provider_status_row(
            provider="fixture",
            source=f"Phase 5A crypto fixture:{symbol}",
            status="fixture",
            availability="limited",
            row_count=len(timeseries),
            fetched_at=FIXTURE_FETCHED_AT,
            caveat="Deterministic fixture used for static web export.",
            data_gap="Runtime CoinGecko/Binance providers are not called during fixture export.",
        )
    ]
    for item in [*snapshots, *pressure]:
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
    market_overview: dict[str, Any],
    derivatives_snapshot: dict[str, Any],
    derivatives_timeseries: list[dict[str, Any]],
    funding: list[dict[str, Any]],
    open_interest: list[dict[str, Any]],
    taker_flow: list[dict[str, Any]],
    long_short_bias: list[dict[str, Any]],
    liquidation_pressure_proxy: list[dict[str, Any]],
    scenario_matrix: list[dict[str, Any]],
    chart_specs: list[dict[str, Any]],
    provider_status: list[dict[str, Any]],
    include_runtime: bool,
) -> dict[str, Any]:
    data_gaps = []
    for collection in [derivatives_timeseries, liquidation_pressure_proxy, scenario_matrix, provider_status]:
        data_gaps.extend(str(row.get("data_gap")) for row in collection if isinstance(row, dict) and row.get("data_gap"))
    for item in [market_overview, derivatives_snapshot]:
        if item.get("data_gap"):
            data_gaps.append(str(item["data_gap"]))
    return {
        "crypto_intelligence_version": CRYPTO_INTELLIGENCE_VERSION,
        "workspace": "crypto-intelligence",
        "symbol": symbol,
        "market_overview": market_overview,
        "derivatives_snapshot": derivatives_snapshot,
        "derivatives_timeseries": derivatives_timeseries,
        "funding": funding,
        "open_interest": open_interest,
        "taker_flow": taker_flow,
        "long_short_bias": long_short_bias,
        "liquidation_pressure_proxy": liquidation_pressure_proxy,
        "scenario_matrix": scenario_matrix,
        "chart_specs": chart_specs,
        "provider_status": provider_status,
        "data_gaps": sorted({gap for gap in data_gaps if gap and gap != "None"}),
        "command_routes": [
            {"raw": f"{symbol} CRYPTO", "target_view": "crypto-intelligence", "source_status": "schema-ready", "not_financial_advice": True},
            {"raw": "NI", "target_view": "market-intelligence", "source_status": "schema-ready", "not_financial_advice": True},
        ],
        "summary": {
            "workspace": "crypto-intelligence",
            "symbol": symbol,
            "price": market_overview.get("current_price") or derivatives_snapshot.get("mark_price"),
            "timeseries_row_count": len(derivatives_timeseries),
            "scenario_count": len(scenario_matrix),
            "chart_count": len(chart_specs),
            "runtime_requested": bool(include_runtime),
            "source_status": derivatives_snapshot.get("source_status") or "unavailable",
            "non_advisory": True,
            "broker_execution_added": False,
            "exchange_account_dependency_added": False,
        },
        "caveat": "Crypto Intelligence is read-only source/status context; no exchange account action is added.",
    }


def build_crypto_intelligence_contract(symbol: str = "BTCUSDT", *, include_runtime: bool = False) -> dict[str, Any]:
    normalized = "".join(ch for ch in (symbol or "BTCUSDT").upper() if ch.isalnum())[:20] or "BTCUSDT"
    if normalized.endswith("USD") and not normalized.endswith("USDT"):
        normalized = f"{normalized}T"
    if include_runtime:
        runtime = _runtime_contract(normalized)
        if runtime:
            return runtime
    return _fixture_contract(normalized)
