from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.api_contracts import (
    build_api_analyst_workspace_payload,
    build_api_attention_desk_payload,
    build_api_ai_provider_payload,
    build_api_asset_universe_payload,
    build_api_command_workspace_payload,
    build_api_crypto_intelligence_payload,
    build_api_daily_brief_payload,
    build_api_equity_intelligence_payload,
    build_api_event_asset_graph_payload,
    build_api_feed_registry_payload,
    build_api_financial_fundamentals_payload,
    build_api_hosted_scheduler_operations_payload,
    build_api_layer_runtime_payload,
    build_api_map_news_event_fusion_payload,
    build_api_market_intelligence_payload,
    build_api_market_map_screener_payload,
    build_api_news_dashboard_payload,
    build_api_options_quant_payload,
    build_api_portfolio_risk_payload,
    build_api_research_memory_payload,
    build_api_product_parity_payload,
    build_api_provider_health_payload,
    build_api_route_manifest_payload,
    build_api_screener_drilldown_payload,
    build_api_symbol_directory_payload,
    build_api_symbol_delivery_payload,
    build_api_symbol_workstation_payload,
    build_api_watchlist_desk_payload,
    build_api_watchlist_alert_manager_payload,
    build_api_research_report_payload,
    build_api_war_room_payload,
    build_api_war_room_map_payload,
    build_api_war_room_map_replay_payload,
    validate_api_payload,
)
from lib.attention_desk import build_attention_desk_from_payloads
from lib.watchlist_observation_runs import build_fixture_observation_context
from lib.watchlist_alert_manager import build_watchlist_alert_manager_fixture_contract
from lib.hosted_scheduler_operations import build_fixture_hosted_scheduler_contract
from lib.war_room import build_war_room_state


DEFAULT_OUTPUT_DIR = ROOT / "static" / "api-fixtures"
FIXTURE_TIMESTAMP = "2026-06-16T00:00:00+00:00"
_FIXTURE_PAYLOAD_CACHE: dict[str, dict[str, dict[str, Any]]] = {}

FIXTURE_ENV_VARS = [
    "AI_MODEL",
    "AI_PROVIDER",
    "AISSTREAM_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "ANTHROPIC_API_KEY",
    "COINGECKO_API_KEY",
    "EIA_API_KEY",
    "FINNHUB_API_KEY",
    "FMP_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_ENABLE_GOOGLE_SEARCH",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "MARINETRAFFIC_API_KEY",
    "NASA_FIRMS_MAP_KEY",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENSKY_CLIENT_ID",
    "OPENSKY_CLIENT_SECRET",
    "OPENSKY_PASSWORD",
    "OPENSKY_USERNAME",
    "POLYGON_API_KEY",
    "VESSELFINDER_API_KEY",
    "WEBCAM_PROVIDER_KEY",
    "WORLD_MONITOR_BASE_URL",
    "WORLD_MONITOR_KEY",
]

DYNAMIC_TIMESTAMP_FIELDS = {
    "checked_at",
    "created_at",
    "fetched_at",
    "generated_at",
    "last_contact_iso",
    "last_checked",
    "latest_fetched_at",
    "local_timestamp",
    "published_at",
    "response_time_iso",
    "timestamp",
    "time_position_iso",
    "utc_timestamp",
}

DYNAMIC_NUMBER_FIELDS = {
    "age_seconds",
    "latency_ms",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{10,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{8,}"),
    re.compile(r"gsk_[0-9A-Za-z_\-]{8,}"),
    re.compile(r"Bearer\s+[0-9A-Za-z._\-]+", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|client[_-]?secret|access[_-]?token|authorization|password)\s*[:=]\s*[^,\s\]\}]+"),
]


@contextmanager
def _fixture_environment(*, use_environment: bool = False) -> Iterator[None]:
    if use_environment:
        yield
        return
    previous = {name: os.environ.get(name) for name in FIXTURE_ENV_VARS}
    try:
        for name in FIXTURE_ENV_VARS:
            os.environ.pop(name, None)
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _sample_news_row() -> dict[str, Any]:
    return {
        "title": "Phase 2C fixture: Red Sea shipping risk remains watch-listed",
        "summary": "Static fixture row for contract-driven UI development.",
        "source": "phase2c.fixture",
        "source_url": "https://example.test/phase-2c/news",
        "provider": "fixture",
        "published_at": FIXTURE_TIMESTAMP,
        "fetched_at": FIXTURE_TIMESTAMP,
        "freshness": "fixture",
        "source_status": "fixture",
        "confidence": 0.5,
        "region": "Red Sea",
        "severity": "watch",
        "lat": 18.0,
        "lon": 39.0,
        "coordinate_method": "fixture_coordinates",
        "data_gap": "Fixture row only; not live news.",
        "caveat": "Static fixture for web-shell development.",
    }


def _sample_chokepoint_row() -> dict[str, Any]:
    return {
        "title": "Phase 2C fixture chokepoint",
        "summary": "Static chokepoint fixture; no live vessel tracking is claimed.",
        "timestamp": FIXTURE_TIMESTAMP,
        "fetched_at": FIXTURE_TIMESTAMP,
        "region": "Red Sea",
        "country": "Fixture",
        "lat": 18.0,
        "lon": 39.0,
        "related_tickers": ["CL=F", "BZ=F"],
        "source": "static fixture",
        "source_url": "https://example.test/phase-2c/chokepoint",
        "provider": "fixture",
        "freshness_status": "proxy/static",
        "source_status": "proxy/static",
        "coordinate_method": "fixture_coordinates",
        "data_gap": "No live AIS or vessel flow in static fixtures.",
        "caveat": "Static/proxy fixture row.",
    }


def _fixture_provider_ledger() -> list[dict[str, Any]]:
    return [
        {
            "provider": "fixture",
            "source": "static api fixture",
            "status": "proxy/static",
            "ok": True,
            "availability": "limited",
            "row_count": 1,
            "fetched_at": FIXTURE_TIMESTAMP,
            "age_seconds": 0,
            "stale_after_seconds": None,
            "cached": False,
            "estimated": True,
            "paid_required": False,
            "coverage": "1 fixture row",
            "warning": "Static fixture only; not live provider telemetry.",
            "error": None,
            "recommended_action": "Use fixture for UI development only.",
            "caveat": "Fixture rows never imply live coverage.",
        },
        {
            "provider": "opensky",
            "source": "OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
            "status": "missing-key",
            "ok": False,
            "availability": "unavailable",
            "row_count": 0,
            "fetched_at": None,
            "age_seconds": None,
            "stale_after_seconds": None,
            "cached": False,
            "estimated": False,
            "paid_required": True,
            "coverage": "missing key",
            "warning": "OpenSky remains unavailable until OAuth credentials and /states/all fetch succeed.",
            "error": "Missing optional environment variable: OPENSKY_CLIENT_ID or OPENSKY_CLIENT_SECRET",
            "recommended_action": "Configure optional OpenSky credentials or keep flight layer unavailable.",
            "caveat": "No fake flight tracking is exported.",
        },
    ]


def _freeze_dynamic_fields(value: Any) -> Any:
    if isinstance(value, dict):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if key in DYNAMIC_TIMESTAMP_FIELDS and item not in {None, ""}:
                frozen[key] = FIXTURE_TIMESTAMP
            elif key in DYNAMIC_NUMBER_FIELDS and item is not None:
                frozen[key] = 0
            else:
                frozen[key] = _freeze_dynamic_fields(item)
        return frozen
    if isinstance(value, list):
        return [_freeze_dynamic_fields(item) for item in value]
    return value


def _assert_fixture_safe(name: str, payload: dict[str, Any]) -> None:
    valid, issues = validate_api_payload(payload)
    if not valid:
        raise ValueError(f"{name} fixture failed API validation: {issues}")
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    matches = [pattern.pattern for pattern in SECRET_VALUE_PATTERNS if pattern.search(encoded)]
    if matches:
        raise ValueError(f"{name} fixture contains secret-like values matching: {matches}")
    private_tokens = [str(ROOT), "\\data\\private\\", "/data/private/", ".env"]
    leaked = [token for token in private_tokens if token and token in encoded]
    if leaked:
        raise ValueError(f"{name} fixture contains local/private path markers: {leaked}")


def _compact_symbol_summary_catalog() -> dict[str, Any]:
    entries = [
        build_api_symbol_delivery_payload(
            symbol=symbol,
            delivery="summary",
            asset_class=asset_class,
            runtime_mode="fixture",
        )
        for symbol, asset_class in [
            ("AAPL", "equity"),
            ("MSFT", "equity"),
            ("NVDA", "equity"),
            ("TSLA", "equity"),
            ("JNJ", "equity"),
            ("SPY", "etf"),
            ("QQQ", "etf"),
            ("BTCUSDT", "crypto"),
            ("ETHUSDT", "crypto"),
        ]
    ]
    base = copy.deepcopy(entries[0])
    base["data"] = {
        "catalog_version": "phase6e.compact-summary.v1",
        "summaries": entries,
    }
    base["summary"] = {
        "workspace": "symbol-workstation-summary-catalog",
        "workstation_count": len(entries),
        "delivery": "summary",
        "fixture_only": True,
    }
    base["source_status"] = []
    base["unavailable"] = []
    base["errors"] = []
    base["caveats"] = [
        "Deterministic compact summaries support offline first paint only.",
        "No live, current, or complete-universe coverage is claimed.",
        "Unknown symbols are never substituted with a catalog entry.",
    ]
    return base


def _compact_analyst_workspace_catalog() -> dict[str, Any]:
    entries = [
        build_api_analyst_workspace_payload(
            symbol=symbol,
            asset_class=asset_class,
            runtime_mode="fixture",
        )
        for symbol, asset_class in [
            ("AAPL", "equity"),
            ("MSFT", "equity"),
            ("NVDA", "equity"),
            ("TSLA", "equity"),
            ("JNJ", "equity"),
            ("SPY", "etf"),
            ("QQQ", "etf"),
            ("BTCUSDT", "crypto"),
            ("ETHUSDT", "crypto"),
        ]
    ]
    base = copy.deepcopy(entries[0])
    base["data"] = {
        "catalog_version": "phase6h.compact-workspace.v1",
        "workspaces": entries,
    }
    base["summary"] = {
        "workspace": "analyst-workspace-catalog",
        "workspace_count": len(entries),
        "fixture_only": True,
    }
    base["source_status"] = []
    base["unavailable"] = []
    base["errors"] = []
    base["caveats"] = [
        "Deterministic compact manifests support exact-symbol offline first paint.",
        "No panel body, current market value, or complete-universe coverage is claimed.",
        "Unknown symbols are never substituted with a catalog entry.",
    ]
    return base


def _compact_primary_panel_catalog() -> dict[str, Any]:
    entries = [
        build_api_symbol_delivery_payload(
            symbol=symbol,
            delivery="chart-core",
            asset_class=asset_class,
            runtime_mode="fixture",
        )
        for symbol, asset_class in [
            ("AAPL", "equity"),
            ("MSFT", "equity"),
            ("NVDA", "equity"),
            ("TSLA", "equity"),
            ("JNJ", "equity"),
            ("SPY", "etf"),
            ("QQQ", "etf"),
            ("BTCUSDT", "crypto"),
            ("ETHUSDT", "crypto"),
        ]
    ]
    for entry in entries:
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        data.pop("capabilities", None)
        workstations = data.get("workstations") if isinstance(data.get("workstations"), list) else []
        if workstations and isinstance(workstations[0], dict):
            workstations[0]["chart_specs"] = []
    base = copy.deepcopy(entries[0])
    base["data"] = {
        "catalog_version": "phase6h.saved-primary-panel.v1",
        "primary_panels": entries,
    }
    base["summary"] = {
        "workspace": "analyst-workspace-primary-panel-catalog",
        "workstation_count": len(entries),
        "delivery": "chart-core",
        "fixture_only": True,
    }
    base["source_status"] = []
    base["unavailable"] = []
    base["errors"] = []
    base["caveats"] = [
        "Only one exact saved chart-core envelope is selected for initial workspace rendering.",
        "Fixture OHLCV is deterministic and non-current; runtime revalidation remains independent.",
        "Unknown symbols are never substituted with a catalog entry.",
    ]
    return base


def build_api_fixture_payloads(*, use_environment: bool = False) -> dict[str, dict[str, Any]]:
    """Build deterministic, network-free contract fixtures for Streamlit/web parity."""
    if not use_environment and "masked" in _FIXTURE_PAYLOAD_CACHE:
        return copy.deepcopy(_FIXTURE_PAYLOAD_CACHE["masked"])

    with _fixture_environment(use_environment=use_environment):
        news_row = _sample_news_row()
        war_state = build_war_room_state(
            news=[news_row],
            chokepoints=[_sample_chokepoint_row()],
            statuses=[],
            include_default_runtime=False,
        )
        event_asset_graph_payload = build_api_event_asset_graph_payload(
            events=war_state.get("events"),
            provider_rows=_fixture_provider_ledger(),
        )
        war_room_payload = build_api_war_room_payload(war_state)
        war_room_map_payload = build_api_war_room_map_payload(
            state=war_state,
            provider_rows=_fixture_provider_ledger(),
            event_graph=event_asset_graph_payload.get("data") or {},
        )
        news_payload = build_api_news_dashboard_payload(items=[news_row], statuses=[])
        market_payload = build_api_market_intelligence_payload(include_runtime=False)
        provider_payload = build_api_provider_health_payload(ledger=_fixture_provider_ledger())
        layer_payload = build_api_layer_runtime_payload(runtime_feeds={}, statuses=[])
        map_news_event_fusion_payload = build_api_map_news_event_fusion_payload(
            war_room_map=war_room_map_payload.get("data") or {},
            news_dashboard=news_payload.get("data") or {},
            event_graph=event_asset_graph_payload.get("data") or {},
            provider_health=provider_payload,
            layer_runtime=layer_payload.get("data") or {},
            market_intelligence=market_payload.get("data") or {},
        )
        watchlist_payload = build_api_watchlist_desk_payload(mode="fixture")
        daily_brief_payload = build_api_daily_brief_payload(demo=True)
        attention_payload = build_api_attention_desk_payload(
            build_attention_desk_from_payloads(
                watchlist_payload=watchlist_payload,
                daily_brief_payload=daily_brief_payload,
                news_payload=news_payload,
                provider_health_payload=provider_payload,
                war_map_payload=map_news_event_fusion_payload,
                observation_run=build_fixture_observation_context(),
                mode="fixture",
            )
        )
        payloads = {
            "product-parity.json": build_api_product_parity_payload(),
            "market-intelligence.json": market_payload,
            "equity-intelligence.json": build_api_equity_intelligence_payload(symbol="AAPL", include_runtime=False),
            "financial-fundamentals.json": build_api_financial_fundamentals_payload(symbol="AAPL", include_runtime=False),
            "options-quant.json": build_api_options_quant_payload(symbol="AAPL", include_runtime=False),
            "portfolio-risk.json": build_api_portfolio_risk_payload(
                portfolio_id="demo-core",
                period="1y",
                benchmark="SPY",
                include_runtime=False,
            ),
            "research-memory.json": build_api_research_memory_payload(
                mode="demo",
                collection_id="demo-research",
                surface="inbox",
            ),
            "daily-brief.json": daily_brief_payload,
            "attention-desk.json": attention_payload,
            "screener-drilldown.json": build_api_screener_drilldown_payload(include_runtime=False),
            "market-map-screener.json": build_api_market_map_screener_payload(include_runtime=False),
            "crypto-intelligence.json": build_api_crypto_intelligence_payload(symbol="BTCUSDT", include_runtime=False),
            "symbol-directory.json": build_api_symbol_directory_payload(include_materialized=False),
            "symbol-workstation.json": build_api_symbol_workstation_payload(fixture_catalog=True),
            "symbol-workstation-summaries.json": _compact_symbol_summary_catalog(),
            "analyst-workspace.json": build_api_analyst_workspace_payload(
                symbol="AAPL",
                asset_class="equity",
                runtime_mode="fixture",
            ),
            "analyst-workspace-catalog.json": _compact_analyst_workspace_catalog(),
            "analyst-workspace-primary-panels.json": _compact_primary_panel_catalog(),
            "watchlist-desk.json": watchlist_payload,
            "watchlist-alert-manager.json": build_api_watchlist_alert_manager_payload(
                build_watchlist_alert_manager_fixture_contract()
            ),
            "hosted-scheduler-operations.json": build_api_hosted_scheduler_operations_payload(
                build_fixture_hosted_scheduler_contract("hosted-unverified")
            ),
            "feeds.json": build_api_feed_registry_payload(),
            "provider-health.json": provider_payload,
            "layers.json": layer_payload,
            "news.json": news_payload,
            "war-room.json": war_room_payload,
            "war-room-map.json": war_room_map_payload,
            "map-news-event-fusion.json": map_news_event_fusion_payload,
            "war-room-map-replay.json": build_api_war_room_map_replay_payload(demo=True),
            "ai-providers.json": build_api_ai_provider_payload(preferred="auto"),
            "asset-universe.json": build_api_asset_universe_payload(),
            "event-asset-graph.json": event_asset_graph_payload,
            "research-report.json": build_api_research_report_payload(include_runtime=False),
            "command-workspace.json": build_api_command_workspace_payload(
                event_graph=event_asset_graph_payload.get("data") or {},
                provider_rows=_fixture_provider_ledger(),
            ),
            "manifest.json": build_api_route_manifest_payload(fastapi_available=False),
        }
    frozen = {name: _freeze_dynamic_fields(payload) for name, payload in payloads.items()}
    for name, payload in frozen.items():
        _assert_fixture_safe(name, payload)
    if not use_environment:
        _FIXTURE_PAYLOAD_CACHE["masked"] = copy.deepcopy(frozen)
    return frozen


def export_api_fixtures(output_dir: Path | str = DEFAULT_OUTPUT_DIR, *, use_environment: bool = False) -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, payload in build_api_fixture_payloads(use_environment=use_environment).items():
        target = output_path / name
        target.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export deterministic API contract fixtures.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for exported JSON fixtures.")
    parser.add_argument(
        "--use-environment",
        action="store_true",
        help="Use local optional provider environment variables instead of masked deterministic fixture mode.",
    )
    args = parser.parse_args(argv)
    written = export_api_fixtures(args.output_dir, use_environment=args.use_environment)
    print(json.dumps({"fixture_count": len(written), "files": [str(path) for path in written]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
