# Phase 5F Implementation Plan

Updated: 2026-06-19

## Sequencing Principle

Build vertical user journeys, not more horizontal schemas. Each slice must end with a useful URL, real/cache/stale/failure behavior, tests, and visual proof.

## Phase 5G: Market Home To Symbol Intelligence

Outcome: a user can open the product, understand the market, choose AAPL or BTCUSDT, inspect a real/cached chart and source-bound context, and keep symbol state in the URL.

Includes:

- canonical home and symbol routes;
- symbol/timeframe query propagation;
- free-first runtime wiring for equity and crypto;
- quote/chart/news/fundamentals/provider composition;
- heatmap/screener click-through;
- rendered desktop/mobile proof.

## Phase 5H: Global Map Intelligence

Outcome: WorldMonitor/worldview-style map, news, layers, timeline, and event-to-asset links form one reliable workflow.

Includes:

- nonblank map renderer gate;
- clustering and marker density;
- real USGS/news/weather layers;
- OpenSky only when OAuth succeeds;
- timeline and compare URL state;
- layer health drawer.

## Phase 5I: Screener And Market Map

Outcome: provider-backed equities/ETF/crypto discovery.

Includes:

- filter model;
- ranked table;
- hierarchical heatmap;
- scatter/comparison;
- symbol drilldown;
- delayed/source disclosure.

## Phase 5J: Options And Quant Workstation

Outcome: a complete research-only options workflow from supplied/provider chain to quality, Greeks, IV surface, and scenarios.

Includes:

- chain ingestion and validation;
- expiration/strike filters;
- IV and Greeks;
- surface and historical comparison;
- GEX only with explicit OI/dealer assumptions;
- no trade/execution output.

## Phase 5K: Portfolio And Risk

Outcome: the main Streamlit portfolio lab value reaches the web.

Includes holdings, performance, drawdown, factors, attribution, correlation, stress, and report capture.

## Phase 5L: Research Memory

Outcome: watchlists, alerts, reports, notes, and evidence history create daily return value.

Start local-first. Add hosted Supabase/PostgreSQL only after schema, migration, privacy, and deletion workflows pass.

## Phase 6: Commercial Platform

Includes auth, billing, entitlements, observability, background jobs, email/push alerts, security review, privacy controls, backups, and deployment SLOs.

## Per-Slice Done Criteria

1. Existing `lib/` and Streamlit source inspected.
2. Contract documented and additive.
3. Real/cache/stale/unavailable behavior tested.
4. Fixture remains deterministic and secret-safe.
5. Desktop/mobile rendered screens inspected.
6. Chart/map nonblank assertion passes when applicable.
7. Accessibility, security, license, and no-advice review passes.
8. Narrow tests, full tests, web test/lint/build/audit, and release hygiene pass.

## Explicitly Deferred

- autonomous trading;
- broker/order execution;
- personalized trade recommendations;
- unlicensed data redistribution;
- paid provider lock-in before measured need;
- wholesale external source or visual copying.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
