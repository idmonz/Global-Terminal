# OSINT-Aware Watchlist Briefing

## Purpose

OSINT-aware briefing links supplied events/news/provider snapshots to watchlist items using entity aliases, confidence scoring, and dedupe.

## V2 matching dimensions

- symbol
- display name
- asset class
- region
- country
- chokepoint
- provider
- strategy id
- event theme
- tags

## Alias examples

Red Sea, Bab el-Mandeb, Strait of Hormuz, Suez, Panama Canal, Taiwan Strait, Black Sea, Persian Gulf, Ukraine, Russia, Middle East, Korea, China, oil/energy, crypto, FRED, EIA, Binance, CoinGecko, DefiLlama.

## Confidence labels

- exact
- alias
- inferred
- low_confidence
- timeline_only

Low-confidence events remain timeline-only. No precise coordinates are invented.

## Tests

Covered by `tests/test_goal11b_osint_alias_matching.py`.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.
