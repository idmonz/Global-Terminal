# Phase 5Z Universe And Taxonomy Contract

Updated: 2026-07-01

## Contract

`market_map_screener.v2` separates four evidence layers:

1. `membership`: official listing identity from Nasdaq Trader directories.
2. `observation`: delayed Yahoo screener market state.
3. `history`: existing batched yfinance history and derived factors.
4. `taxonomy`: reviewed local sector/industry reference metadata.

These layers must not be collapsed into one generic `live` claim.

## Membership Fields

Each verified listing can expose:

- stable symbol and normalized name;
- exchange and MIC;
- security type and ETF flag;
- listing status where supported;
- provider, source URL, source status, and source as-of;
- caveat that listing identity is not index membership.

`authoritative_index_membership` remains false.

## Taxonomy Fields

Taxonomy rows expose sector, industry, source, status, confidence, caveat, and data
gap independently. Unmatched rows use `Unclassified` and `unavailable`; they are not
assigned to a fabricated sector.

## Observation And History

The broad snapshot supplies price, one-day change, market cap, volume, average
volume, and relative volume when the provider returns them. The bounded history
set supplies one-month return, volatility, drawdown, RSI, trend, and ranking
components. Missing history makes a row ineligible for affected ranks but does not
remove it from the default heatmap.

## Runtime Rules

- at most one broad Yahoo screener request per cold composition;
- one existing batched history request, never per-symbol request fan-out;
- two Nasdaq directory files fetched concurrently with TTL, stale fallback, and
  single-flight cache;
- cache mode does not refresh providers;
- all payloads remain JSON-safe and secret-free.

## Observed 2026-07-01 State

- Yahoo observations screened: 250;
- official-listing matched observations: 131;
- excluded unverified observations: 119;
- final visible official-listed rows after history merge: 137;
- local taxonomy coverage: 60;
- unclassified rows: 77;
- ranked/history-capable rows: 60.

Counts are observed evidence, not hard-coded guarantees.
