# Phase 6C Dynamic Identity And Capability Contract

Updated: 2026-07-02

## Identity Resolution

`symbol_workstation.v2` resolves a requested equity in this order:

1. validate normalized symbol and asset-class syntax;
2. look up the current atomic `market_snapshot.v2` identity;
3. reconcile the materialized Nasdaq/SEC identity with reviewed local taxonomy
   when present;
4. retain exchange, MIC, CIK, security/listing type, source URLs, classification
   origin, conflict state, and snapshot clock;
5. use the old static registry only as additive reviewed metadata, never as a
   cross-symbol fallback.

The materialized identity index is cached against the current manifest
mtime/size. The runtime directory contains 363 unique rows: 333 current
materialized equities, 10 reviewed ETFs, and 20 reviewed crypto identities.
Deterministic fixture export intentionally retains the static directory.

## Capability Plan

`build_symbol_capability_plan()` creates a selected-symbol plan before any
provider work. It records:

- normalized symbol, asset class, interval, and range;
- requested panels;
- selected comparison symbol;
- maximum provider-call budget;
- cache-only or live-if-available mode;
- identity, chart, financial, SEC, news, and comparison capability;
- `broad_rebuild=false`.

Unsupported interval/range combinations receive a zero provider budget and an
explicit unavailable state.

## Fetch And Cache Rules

- cache keys include symbol, asset class, interval, range, and panel contract;
- only the selected symbol and explicit comparison may be fetched;
- cached repeat calls perform no broad Market Map rebuild;
- a provider failure may use only the same symbol's stale/LKG record;
- no stale record means explicit unavailable, not generated OHLCV;
- a delayed Market Map quote may remain visible as a separately labeled market
  observation when exact history is unavailable;
- fixture history is limited to explicit fixture mode;
- unknown, malformed, traversal, and mismatched symbols cannot receive AAPL or
  any other identity's payload.

## Source Truth

Every workstation retains separate source rows for:

- official listing and SEC identity;
- reviewed/local or provider classification;
- delayed market observation;
- OHLCV history;
- calculated technical/risk/comparison metrics;
- financial and SEC company facts;
- exact-symbol/company news.

The UI exposes identity origin, MIC, CIK, classification method/conflict,
provider budget, freshness, caveat, and data-gap state. It does not claim
official realtime, official GICS, execution, targets, or recommendations.

## HTTP Contract

- `GET /api/symbol-workstation?symbol=...` remains compatible;
- `GET /api/symbol-workstation/{symbol}` is the exact additive route;
- stable exact payloads return an ETag;
- matching `If-None-Match` returns 304;
- unknown exact symbols return a 404 JSON envelope;
- responses use private short cache control with stale-while-revalidate;
- payload validation rejects secrets, private paths, non-JSON objects, and
  identity mismatches.

