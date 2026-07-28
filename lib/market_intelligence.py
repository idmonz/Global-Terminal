from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .chart_specs import build_chart_spec, provider_status_row, record_series


MARKET_INTELLIGENCE_VERSION = "market_intelligence.v1"
FIXTURE_FETCHED_AT = "2026-06-16T00:00:00+00:00"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fixture_market_rows() -> list[dict[str, Any]]:
    rows = [
        ("SPY", "S&P 500 ETF", "equity_index_proxy", 548.4, 0.42, 1.8, "US equity benchmark proxy"),
        ("QQQ", "Nasdaq 100 ETF", "growth_equity_proxy", 473.2, 0.58, 2.2, "US growth/mega-cap proxy"),
        ("IWM", "Russell 2000 ETF", "small_cap_proxy", 207.5, -0.18, -1.1, "Small-cap breadth proxy"),
        ("TLT", "20+ Year Treasury ETF", "rates_proxy", 91.8, -0.34, -2.6, "Long-duration rates proxy"),
        ("DX-Y.NYB", "US Dollar Index", "fx_proxy", 104.6, 0.16, 0.8, "DXY proxy ticker"),
        ("GLD", "Gold ETF", "commodity_proxy", 219.7, 0.21, 3.4, "Gold proxy"),
        ("CL=F", "WTI Crude", "energy_proxy", 78.2, -0.52, 4.6, "WTI futures proxy"),
        ("BTC-USD", "Bitcoin", "crypto_proxy", 66400.0, 1.2, 8.8, "Public crypto proxy"),
    ]
    return [
        {
            "symbol": symbol,
            "label": label,
            "asset_class": asset_class,
            "last_price": price,
            "daily_return_pct": daily,
            "one_month_return_pct": monthly,
            "provider": "fixture",
            "source": "Phase 5A deterministic market tape",
            "source_status": "fixture",
            "freshness": "fixture",
            "fetched_at": FIXTURE_FETCHED_AT,
            "caveat": caveat,
            "data_gap": "Fixture-safe market tape; not live exchange or broker data.",
            "not_financial_advice": True,
        }
        for symbol, label, asset_class, price, daily, monthly, caveat in rows
    ]


def _market_heat_rows(market_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    heat_rows = []
    for row in market_rows:
        change = float(row.get("one_month_return_pct") or 0.0)
        if change >= 3:
            bucket = "constructive"
        elif change <= -2:
            bucket = "elevated downside risk"
        else:
            bucket = "mixed"
        heat_rows.append(
            {
                "symbol": row["symbol"],
                "label": row["label"],
                "asset_class": row["asset_class"],
                "risk_bucket": bucket,
                "score": max(0, min(100, 50 + change * 5)),
                "provider": row["provider"],
                "source_status": row["source_status"],
                "fetched_at": row["fetched_at"],
                "caveat": "Bucket is a simple fixture-safe cross-asset move classification.",
                "data_gap": row["data_gap"],
                "not_financial_advice": True,
            }
        )
    return heat_rows


def _heatmap_color_bucket(change: float) -> str:
    if change >= 2.5:
        return "gain-strong"
    if change >= 0.35:
        return "gain"
    if change <= -2.5:
        return "loss-strong"
    if change <= -0.35:
        return "loss"
    return "flat"


def _fixture_market_heatmap_rows() -> list[dict[str, Any]]:
    """Clean-room Finviz/TradingView-style heatmap fixture rows.

    Size is a deterministic market-cap-style weight, color is daily performance.
    The rows are synthetic product fixtures and do not copy external map data.
    """
    sectors = [
        (
            "Electronic technology",
            [
                ("NVDA", "NVIDIA", "Semiconductors", 13.4, 2.95),
                ("AAPL", "Apple", "Consumer electronics", 11.2, 0.70),
                ("AVGO", "Broadcom", "Semiconductors", 3.8, 4.70),
                ("AMD", "AMD", "Semiconductors", 2.7, 4.86),
                ("MU", "Micron", "Memory", 1.8, 8.70),
            ],
        ),
        (
            "Technology services",
            [
                ("GOOGL", "Alphabet", "Internet content", 9.8, 1.17),
                ("MSFT", "Microsoft", "Software", 9.2, 0.13),
                ("META", "Meta Platforms", "Internet content", 5.6, 1.70),
                ("ORCL", "Oracle", "Enterprise software", 2.1, 0.41),
                ("NFLX", "Netflix", "Streaming", 1.5, 0.55),
                ("PLTR", "Palantir", "Data platforms", 1.2, -1.65),
            ],
        ),
        (
            "Retail trade",
            [
                ("AMZN", "Amazon", "Internet retail", 8.1, 2.90),
                ("WMT", "Walmart", "Retail", 2.9, -0.80),
                ("COST", "Costco", "Retail", 1.8, -1.46),
                ("HD", "Home Depot", "Home improvement", 1.7, 2.08),
            ],
        ),
        (
            "Finance",
            [
                ("BRK.B", "Berkshire Hathaway", "Insurance", 4.3, -0.37),
                ("JPM", "JPMorgan", "Banks", 2.3, -2.47),
                ("V", "Visa", "Payments", 2.1, -0.95),
                ("MA", "Mastercard", "Payments", 1.8, -0.65),
                ("BAC", "Bank of America", "Banks", 1.1, -0.58),
            ],
        ),
        (
            "Health technology",
            [
                ("LLY", "Eli Lilly", "Pharmaceuticals", 4.2, -1.21),
                ("JNJ", "Johnson & Johnson", "Pharmaceuticals", 2.2, -2.48),
                ("ABBV", "AbbVie", "Biotech", 1.8, -2.14),
                ("UNH", "UnitedHealth", "Healthcare plans", 2.0, 0.36),
            ],
        ),
        (
            "Consumer services",
            [
                ("MCD", "McDonald's", "Restaurants", 1.2, -1.84),
                ("SBUX", "Starbucks", "Restaurants", 0.7, 0.21),
                ("DIS", "Disney", "Entertainment", 1.0, 3.00),
            ],
        ),
        (
            "Energy minerals",
            [
                ("XOM", "Exxon Mobil", "Integrated oil", 2.4, -2.08),
                ("CVX", "Chevron", "Integrated oil", 1.6, -2.22),
                ("COP", "ConocoPhillips", "Oil and gas", 0.9, 0.40),
            ],
        ),
    ]
    rows: list[dict[str, Any]] = []
    for sector, members in sectors:
        sector_weight = round(sum(item[3] for item in members), 2)
        for symbol, label, industry, weight, daily_return in members:
            rows.append(
                {
                    "symbol": symbol,
                    "label": label,
                    "sector": sector,
                    "industry": industry,
                    "market_cap_weight": weight,
                    "sector_weight": sector_weight,
                    "daily_return_pct": daily_return,
                    "one_day_change_pct": daily_return,
                    "tile_area_pct": weight,
                    "color_bucket": _heatmap_color_bucket(daily_return),
                    "size_metric": "market_cap_weight",
                    "color_metric": "daily_return_pct",
                    "provider": "fixture",
                    "source": "Phase 5E clean-room market heatmap fixture",
                    "source_status": "fixture",
                    "freshness": "fixture",
                    "fetched_at": FIXTURE_FETCHED_AT,
                    "confidence": 0.42,
                    "caveat": "Synthetic heatmap fixture for workstation design; not live market data.",
                    "data_gap": "Real heatmap requires provider-backed index constituents, market caps, and returns.",
                    "not_financial_advice": True,
                }
            )
    return rows


def _source_rows(rows: list[dict[str, Any]], chart_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_rows = [
        provider_status_row(
            provider="fixture",
            source="Phase 5A deterministic market tape",
            status="fixture",
            availability="limited",
            row_count=len(rows),
            fetched_at=FIXTURE_FETCHED_AT,
            caveat="Fixture data keeps the workstation renderable without live provider calls.",
            data_gap="Use include_runtime mode or optional backend wiring for live yfinance/free-provider rows.",
        )
    ]
    source_rows.extend(
        provider_status_row(
            provider=chart.get("provider", "fixture"),
            source=chart.get("chart_id", "chart_spec"),
            status=chart.get("source_status", "fixture"),
            availability="limited",
            row_count=sum(len(series.get("points", [])) for series in chart.get("series", [])),
            fetched_at=chart.get("fetched_at"),
            caveat=chart.get("caveat", ""),
            data_gap=chart.get("data_gap", ""),
        )
        for chart in chart_specs
    )
    return source_rows


def _runtime_market_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from .market_data import latest_price_snapshot

        symbols = ["SPY", "QQQ", "IWM", "TLT", "DX-Y.NYB", "GLD", "CL=F", "BTC-USD"]
        frame, status = latest_price_snapshot(symbols)
        if getattr(frame, "empty", True):
            return [], [status.to_dict()]
        rows = []
        for item in frame.to_dict(orient="records"):
            rows.append(
                {
                    "symbol": item.get("ticker"),
                    "label": item.get("ticker"),
                    "asset_class": "market_proxy",
                    "last_price": item.get("price"),
                    "daily_return_pct": round(float(item.get("daily_return") or 0.0) * 100, 4),
                    "one_month_return_pct": None,
                    "provider": "yfinance",
                    "source": "latest_price_snapshot",
                    "source_status": "live/fresh" if status.ok else "unavailable",
                    "freshness": "live/fresh" if status.ok else "unavailable",
                    "fetched_at": status.fetched_at.isoformat(),
                    "caveat": "Runtime market row from free yfinance path; inspect status before use.",
                    "data_gap": "" if status.ok else status.error,
                    "not_financial_advice": True,
                }
            )
        return rows, [status.to_dict()]
    except Exception as exc:
        return [], [
            provider_status_row(
                provider="yfinance",
                source="latest_price_snapshot",
                status="unavailable",
                availability="unavailable",
                row_count=0,
                fetched_at=_now_iso(),
                caveat="Runtime market snapshot failed and fixture rows were used.",
                data_gap=str(exc),
            )
        ]


def build_market_intelligence_contract(*, include_runtime: bool = False) -> dict[str, Any]:
    runtime_status: list[dict[str, Any]] = []
    market_rows: list[dict[str, Any]] = []
    if include_runtime:
        market_rows, runtime_status = _runtime_market_rows()
    if not market_rows:
        market_rows = _fixture_market_rows()

    heat_rows = _market_heat_rows(market_rows)
    heatmap_rows = _fixture_market_heatmap_rows()
    chart_specs = [
        build_chart_spec(
            chart_id="market.daily_return",
            chart_type="bar",
            title="Cross-Asset Daily Return",
            x_axis="symbol",
            y_axis="daily_return_pct",
            series=[record_series(market_rows, x_key="symbol", y_key="daily_return_pct", name="daily return")],
            unit="percent",
            provider=market_rows[0]["provider"] if market_rows else "fixture",
            source_status=market_rows[0]["source_status"] if market_rows else "fixture",
            fetched_at=market_rows[0]["fetched_at"] if market_rows else FIXTURE_FETCHED_AT,
            caveat="Cross-asset return chart is non-advisory context.",
            data_gap="Fixture mode is not live market data." if not include_runtime else "Runtime provider gaps are shown in source rows.",
        ),
        build_chart_spec(
            chart_id="market.one_month_return",
            chart_type="bar",
            title="One-Month Proxy Move",
            x_axis="symbol",
            y_axis="one_month_return_pct",
            series=[record_series(market_rows, x_key="symbol", y_key="one_month_return_pct", name="one month move")],
            unit="percent",
            provider="fixture" if not include_runtime else market_rows[0]["provider"],
            source_status="fixture" if not include_runtime else market_rows[0]["source_status"],
            fetched_at=FIXTURE_FETCHED_AT if not include_runtime else market_rows[0]["fetched_at"],
            caveat="One-month move is fixture-safe unless runtime rows supply history.",
            data_gap="Runtime latest snapshot does not include one-month return unless a history contract is wired.",
        ),
        build_chart_spec(
            chart_id="market.risk_heat",
            chart_type="heat",
            title="Cross-Asset Risk Heat",
            x_axis="symbol",
            y_axis="score",
            series=[record_series(heat_rows, x_key="symbol", y_key="score", name="risk heat")],
            unit="score",
            provider="phase5a_market_contract",
            source_status="inferred/proxy",
            fetched_at=market_rows[0]["fetched_at"] if market_rows else FIXTURE_FETCHED_AT,
            caveat="Heat scores classify observable moves; they are not predictions.",
            data_gap="Classification is proxy context only.",
        ),
    ]
    source_status = _source_rows(market_rows, chart_specs) + runtime_status
    source_status.append(
        provider_status_row(
            provider="fixture",
            source="Phase 5E clean-room market heatmap fixture",
            status="fixture",
            availability="limited",
            row_count=len(heatmap_rows),
            fetched_at=FIXTURE_FETCHED_AT,
            caveat="Synthetic market heatmap rows preserve Finviz/TradingView-style behavior without copying external data.",
            data_gap="Provider-backed constituents, market caps, and returns are required before live heatmap coverage is claimed.",
        )
    )
    data_gaps = [row.get("data_gap") for row in market_rows if row.get("data_gap")]
    return {
        "market_intelligence_version": MARKET_INTELLIGENCE_VERSION,
        "workspace": "market-intelligence",
        "market_tape": market_rows,
        "risk_heat": heat_rows,
        "market_heatmap": heatmap_rows,
        "macro_context": [
            {
                "theme": "Rates and duration",
                "linked_symbols": ["TLT", "DX-Y.NYB"],
                "source_status": "fixture",
                "provider": "phase5a_market_contract",
                "caveat": "Fixture-safe cross-asset context; live macro providers remain separately gated.",
                "data_gap": "No live rates curve is claimed in fixture mode.",
                "not_financial_advice": True,
            },
            {
                "theme": "Energy and geopolitical risk",
                "linked_symbols": ["CL=F", "GLD"],
                "source_status": "proxy/static",
                "provider": "war_room_context",
                "caveat": "Proxy links must be inspected with War Map source rows.",
                "data_gap": "No live AIS/vessel flow is claimed.",
                "not_financial_advice": True,
            },
            {
                "theme": "Crypto liquidity",
                "linked_symbols": ["BTC-USD"],
                "source_status": "fixture",
                "provider": "phase5a_market_contract",
                "caveat": "Crypto detail lives in the crypto-intelligence workspace.",
                "data_gap": "Use crypto provider status before treating rows as live.",
                "not_financial_advice": True,
            },
        ],
        "chart_specs": chart_specs,
        "provider_status": source_status,
        "data_gaps": sorted({str(gap) for gap in data_gaps if gap}),
        "summary": {
            "workspace": "market-intelligence",
            "market_row_count": len(market_rows),
            "heatmap_tile_count": len(heatmap_rows),
            "chart_count": len(chart_specs),
            "source_status": market_rows[0]["source_status"] if market_rows else "unavailable",
            "runtime_requested": bool(include_runtime),
            "non_advisory": True,
            "broker_execution_added": False,
        },
        "caveat": "Market Intelligence is source/status-aware context and does not provide trading advice.",
    }
