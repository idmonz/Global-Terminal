from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.api_contract_panels import contract_collection_rows, contract_preview
from lib.api_contracts import (
    build_api_ai_provider_payload,
    build_api_feed_registry_payload,
    build_api_layer_runtime_payload,
    build_api_provider_health_payload,
    build_api_route_manifest_payload,
)
from lib.cache import cache_status_payload
from lib.data_status import get_recent_results
from lib.env_loader import build_env_status_table, load_project_env
from lib.feed_registry import feed_registry_table
from lib.free_api_setup_guide import build_free_api_setup_table
from lib.live_feeds import (
    AIS_UNAVAILABLE_MESSAGE,
    FLIGHT_UNAVAILABLE_MESSAGE,
    build_live_feed_status,
    fetch_aisstream_optional_status,
    fetch_opensky_optional_status,
)
from lib.provider_diagnostics import (
    provider_error_table,
    provider_gap_report,
    provider_health_summary,
    provider_rate_limit_status,
    provider_freshness_dashboard,
    test_all_configured_providers,
    test_provider_connection,
)
from lib.provider_health_engine import build_provider_health_snapshot
from lib.provider_quality import build_provider_quality_scorecard, build_provider_quality_summary
from lib.provider_probe_runner import run_provider_probes
from lib.provider_probe_store import load_provider_probe_results, provider_probe_store_is_gitignored
from lib.provider_probe_visuals import build_provider_probe_metric_cards, build_provider_probe_table
from lib.heatmap_layout_engine import build_provider_health_heatmap
from lib.no_key_provider_catalog import build_no_key_provider_table
from lib.openbb_catalog import list_openbb_required_keys, openbb_endpoint_status_table
from lib.openbb_diagnostics import build_openbb_diagnostics_table, openbb_installation_status, openbb_provider_key_status
from lib.provider_registry import (
    build_provider_registry,
    list_providers_by_domain,
    provider_capability_matrix,
)
from lib.terminal_ui import goal10_summary_strip, metric_strip, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_table


st.set_page_config(page_title="Data Provider Center", layout="wide")
load_project_env()
terminal_page_header(
    st,
    "Live Data Provider Center",
    "Provider registry, optional-key diagnostics, live-feed readiness, and explicit data gaps.",
    meta=[
        {"label": "Base Launch", "value": "No paid APIs required", "tone": "fresh"},
        {"label": "AIS", "value": "Optional", "tone": "estimated"},
        {"label": "Flight", "value": "Optional", "tone": "estimated"},
    ],
)
goal10_summary_strip(st, workspace="OpenBB / Data Provider Desk", risk_state="data gap", data_confidence="probe-labeled", provider_status="probe center ready", caveat="Provider probes are diagnostics only; missing keys, rate limits, and outages remain visible and nonfatal.")

registry = build_provider_registry()
matrix = provider_capability_matrix()
summary = provider_health_summary(registry)

tabs = st.tabs(
    [
        "Provider Overview",
        "Market Data",
        "OpenBB",
        "Crypto Data",
        "News / OSINT",
        "Geopolitics",
        "AIS / Shipping",
        "Flight Tracking",
        "Natural / Weather",
        "Provider Tests",
        "Real Probe Center",
        "No-Key Sources",
        "Environment",
        "Data Gaps",
        "Setup Guide",
    ]
)

with tabs[0]:
    terminal_section_header(st, "Provider Overview", "Capability matrix and free-mode readiness")
    metric_strip(
        st,
        [
            {"label": "Providers", "value": summary["total_providers"], "delta": "registered", "freshness": "fresh"},
            {"label": "Available", "value": summary["available"], "delta": "free/configured", "freshness": "fresh"},
            {"label": "Configured", "value": summary["configured"], "delta": "env present", "freshness": "fresh"},
            {"label": "Optional Missing", "value": summary["optional_missing"], "delta": "graceful gaps", "freshness": "estimated"},
        ],
    )
    quality = build_provider_quality_scorecard(registry=registry)
    quality_summary = build_provider_quality_summary(quality)
    metric_strip(
        st,
        [
            {"label": "Quality Avg", "value": quality_summary["average_quality"], "delta": quality_summary["summary_label"], "freshness": "estimated"},
            {"label": "Ready", "value": quality_summary["ready_count"], "delta": "providers", "freshness": "fresh"},
            {"label": "Limited", "value": quality_summary["limited_count"], "delta": "visible gaps", "freshness": "estimated"},
            {"label": "Gap", "value": quality_summary["gap_count"], "delta": "needs setup", "freshness": "missing" if quality_summary["gap_count"] else "fresh"},
        ],
    )
    render_table(st, matrix[["provider_id", "name", "domain", "free_mode", "paid_optional", "is_configured", "is_available", "supports_realtime", "supports_streaming", "caveat"]])
    with st.expander("Provider quality scorecard", expanded=False):
        render_table(st, quality)
        if quality_summary["top_gaps"]:
            st.warning("Top provider quality gaps are visible below.")
            render_table(st, pd.DataFrame(quality_summary["top_gaps"]))
    st.json(cache_status_payload())

with tabs[1]:
    terminal_section_header(st, "Market Data", "yfinance, FRED, EIA, pykrx, and optional market providers")
    render_table(st, pd.DataFrame(list_providers_by_domain("Market")))

with tabs[2]:
    terminal_section_header(st, "OpenBB Optional Backend", "Installation, optional provider keys, catalog status, and license caveat")
    openbb_status = openbb_installation_status()
    metric_strip(
        st,
        [
            {"label": "Installed", "value": "Yes" if openbb_status["installed"] else "No", "delta": openbb_status.get("version") or "optional", "freshness": "fresh" if openbb_status["installed"] else "missing"},
            {"label": "Backend", "value": "Optional", "delta": "native fallback", "freshness": "fresh"},
            {"label": "Provider keys", "value": "Optional", "delta": "hidden values", "freshness": "estimated"},
            {"label": "Base launch", "value": "No OpenBB required", "delta": "safe", "freshness": "fresh"},
        ],
    )
    render_table(st, build_openbb_diagnostics_table())
    render_table(st, openbb_provider_key_status())
    with st.expander("OpenBB capability catalog", expanded=False):
        render_table(st, openbb_endpoint_status_table())

with tabs[3]:
    terminal_section_header(st, "Crypto Data", "Public crypto feeds plus optional derivatives intelligence")
    render_table(st, pd.DataFrame(list_providers_by_domain("Crypto")))
    st.info("Official liquidation heatmaps require an official/paid provider. Free-mode liquidation pressure remains labeled as an estimate/proxy.")

with tabs[4]:
    terminal_section_header(st, "News / OSINT", "RSS, GDELT, Yahoo news, optional NewsAPI, optional WorldMonitor adapter")
    render_table(st, pd.DataFrame(list_providers_by_domain("News / OSINT")))
    terminal_section_header(st, "Curated Feed Taxonomy", "Registry-backed defaults and optional OSINT feeds with source risk and caveats.")
    render_table(st, pd.DataFrame(feed_registry_table()))
    terminal_section_header(st, "Recent Runtime Health Ledger", "Recent fetches classified as fresh, cached, stale, rate-limited, forbidden, missing-key, unavailable, or proxy/static.")
    render_table(st, pd.DataFrame(build_provider_health_snapshot(get_recent_results())["ledger"]))

with tabs[5]:
    terminal_section_header(st, "Geopolitics", "Conflict providers and curated public feed status")
    render_table(st, pd.DataFrame(list_providers_by_domain("Geopolitics / Conflict")))

with tabs[6]:
    terminal_section_header(st, "AIS / Shipping", "Optional AIS providers plus chokepoint fallback")
    ais = fetch_aisstream_optional_status()
    st.warning(ais["warning"] or "AIS provider configured; live vessel flow remains unavailable until a provider test succeeds.")
    render_table(st, pd.DataFrame(list_providers_by_domain("AIS / Shipping")))
    st.caption(AIS_UNAVAILABLE_MESSAGE)

with tabs[7]:
    terminal_section_header(st, "Flight Tracking", "Optional OpenSky / ADS-B provider status")
    flight = fetch_opensky_optional_status()
    st.warning(flight["warning"] or "Flight provider configured. Use Provider Tests before displaying live tracking.")
    render_table(st, pd.DataFrame(list_providers_by_domain("Flight")))
    st.caption(FLIGHT_UNAVAILABLE_MESSAGE)

with tabs[8]:
    terminal_section_header(st, "Natural / Weather", "USGS public feed and optional weather/fire providers")
    render_table(st, pd.DataFrame(list_providers_by_domain("Natural / Weather")))

with tabs[9]:
    terminal_section_header(st, "Provider Tests", "Button-triggered diagnostics only")
    provider_ids = matrix["provider_id"].tolist()
    selected = st.selectbox("Provider", provider_ids)
    if st.button("Test selected provider"):
        st.dataframe(pd.DataFrame([test_provider_connection(selected)]), use_container_width=True, hide_index=True)
        st.json(provider_rate_limit_status(selected))
    if st.button("Test configured/free providers"):
        diagnostics = test_all_configured_providers()
        render_table(st, diagnostics)
        probe_quality = build_provider_quality_scorecard(diagnostics, registry=registry)
        probe_summary = build_provider_quality_summary(probe_quality)
        metric_strip(
            st,
            [
                {"label": "Probe Avg", "value": probe_summary["average_quality"], "delta": probe_summary["summary_label"], "freshness": "estimated"},
                {"label": "Ready", "value": probe_summary["ready_count"], "delta": "observed", "freshness": "fresh"},
                {"label": "Limited", "value": probe_summary["limited_count"], "delta": "observed", "freshness": "estimated"},
                {"label": "Gap", "value": probe_summary["gap_count"], "delta": "observed", "freshness": "missing" if probe_summary["gap_count"] else "fresh"},
            ],
        )
        render_table(st, probe_quality)
        errors = provider_error_table(diagnostics)
        if not errors.empty:
            st.warning("Provider warnings or errors detected.")
            render_table(st, errors)
    freshness = provider_freshness_dashboard()
    if not freshness.empty:
        st.subheader("Recent Fetch Freshness")
        render_table(st, freshness)

with tabs[10]:
    terminal_section_header(st, "Real Provider Probe Center", "Optional lightweight diagnostics; dry-run mode never requires internet or keys")
    stored = load_provider_probe_results()
    dry_run = st.toggle("Dry run", value=True, key="goal10_provider_probe_dry_run")
    if st.button("Run Goal 10 provider probes", key="goal10_provider_probes"):
        probe_results = run_provider_probes(dry_run=dry_run, save=not dry_run)
    else:
        probe_results = stored.get("results", []) or run_provider_probes(dry_run=True)
    metric_strip(st, build_provider_probe_metric_cards(probe_results), columns=4)
    provider_heatmap = build_provider_health_heatmap(
        [
            {
                **row,
                "domain": row.get("source_type", "provider"),
                "score": 100 if row.get("ok") else 25,
                "tile_type": "provider",
                "source": row.get("provider"),
                "freshness": row.get("status"),
            }
            for row in probe_results
        ]
    )
    terminal_section_header(st, "Provider Health Heatmap", "Coverage, missing keys, historical-only providers, and provider-status tooltips.")
    render_table(st, provider_heatmap["table"])
    render_table(st, build_provider_probe_table(probe_results))
    split_scripts = pd.DataFrame(
        [
            {"suite": "OpenBB runtime", "script": "python scripts/probe_openbb_runtime.py --dry-run", "purpose": "Optional OpenBB install, version, resolver, sample status."},
            {"suite": "Provider matrix", "script": "python scripts/probe_provider_matrix.py --dry-run", "purpose": "All lightweight providers, domain coverage, missing keys."},
            {"suite": "Macro/Energy", "script": "python scripts/probe_macro_energy_sources.py --dry-run", "purpose": "Treasury, World Bank, SDMX, FRED, EIA, BLS, Open-Meteo."},
            {"suite": "Crypto", "script": "python scripts/probe_crypto_sources.py --dry-run", "purpose": "Binance public, DefiLlama, CoinGecko keyless/demo."},
            {"suite": "News/OSINT", "script": "python scripts/probe_news_osint_sources.py --dry-run", "purpose": "GDELT, USGS, weather, NWS, NOAA, FIRMS, AISStream, OpenSky."},
        ]
    )
    terminal_section_header(st, "Split Probe Scripts", "Suite-specific diagnostics remain nonfatal and dry-run friendly.")
    render_table(st, split_scripts)
    st.caption(f"Probe storage gitignored: {provider_probe_store_is_gitignored()}")
    st.info("Provider probes are lightweight diagnostics. Missing API keys, rate limits, and provider outages may affect availability.")

with tabs[11]:
    terminal_section_header(st, "No-Key / Free Official Sources", "Base-launch providers, free-key providers, OAuth-optional providers, and historical-only sources")
    render_table(st, build_no_key_provider_table())
    st.info("Free public data sources may have rate limits, delayed updates, schema changes, or usage restrictions. Source status and freshness should be verified before relying on outputs.")

with tabs[12]:
    terminal_section_header(st, "Environment", ".env status without exposing secret values")
    render_table(st, build_env_status_table())
    st.warning("An environment file is configured but terminal environment injection is disabled. Enable python.terminal.useEnvFile to use environment variables from .env files in terminals. The app itself also loads .env through python-dotenv at runtime.")

with tabs[13]:
    terminal_section_header(st, "Data Gaps", "Missing keys, unavailable providers, and proxy-only modules")
    render_table(st, provider_gap_report())
    render_table(st, build_live_feed_status())

with tabs[14]:
    terminal_section_header(st, "Setup Guide", "Environment variables and limitations")
    setup_rows = matrix[matrix["env_var"].astype(str).ne("")][["provider_id", "name", "domain", "env_var", "paid_optional", "caveat"]]
    render_table(st, setup_rows)
    render_table(st, list_openbb_required_keys())
    render_table(st, build_free_api_setup_table())
    st.info("Free-mode providers are enough for base launch. Optional paid providers improve coverage but are not required.")
    st.warning("No fake AIS or flight tracking is displayed. Missing optional providers remain visible as explicit data gaps.")

with st.expander("API Contract Payload Preview", expanded=False):
    terminal_section_header(
        st,
        "Contract Surface Readiness",
        "Shared envelopes for Streamlit, optional FastAPI routes, exported fixtures, and future web clients.",
    )
    contract_payloads = [
        build_api_feed_registry_payload(),
        build_api_provider_health_payload(get_recent_results()),
        build_api_layer_runtime_payload(),
        build_api_ai_provider_payload(),
        build_api_route_manifest_payload(fastapi_available=None),
    ]
    render_table(st, contract_collection_rows(contract_payloads))
    st.json(contract_preview(contract_payloads[-1]))

page_footer(st)
