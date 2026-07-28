# Multi-Domain Watchlist System

## Purpose

The watchlist tracks assets, crypto, commodities, equities, ETFs, indexes, FX/rates, regions, countries, chokepoints, ports, providers, strategies, portfolios, event themes, and report topics.

## Data model

Watchlist items include type, symbol, display name, asset class, exchange, region, country, tags, watch reason, default command, default page, source, active state, and metadata.

## Main functions

- `enrich_watchlist_item()` / `enrich_watchlist_items()`
- `build_watchlist_context_bundle()`
- `build_watchlist_heatmap_payload()`
- `build_watchlist_rmi_payload()`
- `build_watchlist_volatility_payload()`
- `build_watchlist_page_payload()`

## Real context wiring

Goal 11B adds route-based enrichment:

- Market items consume supplied UDL/market rows and expose latest value, change, volatility, source status, freshness, and confidence.
- Provider items consume stored/supplied provider snapshots.
- Region/chokepoint items consume OSINT event matches.
- Strategy items consume supplied strategy commit context.

## Fallback policy

When no data is supplied, rows remain labeled unavailable/missing. Metadata fallback is explicit.

## Tests

Covered by `tests/test_goal11b_watchlist_enrichment_integration.py` and `tests/test_goal11b_osint_alias_matching.py`.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.
