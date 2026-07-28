# Phase 5F External Clean-Room Adoption Plan

Updated: 2026-06-19

## Purpose

External projects are evidence and inspiration, not a hidden product dependency. The commercial implementation must be independently understandable, testable, and replaceable.

## Clean-Room Workflow

1. Write the user-visible behavior without referencing source implementation details.
2. Record public/product evidence and local archive evidence separately.
3. Classify the license and exact path.
4. Decide direct-use, behavior-only, or blocked.
5. Define a first-party JSON contract and acceptance tests.
6. Implement in `lib/` or `apps/web` without importing blocked code/assets.
7. Run security, provenance, no-advice, and regression tests.
8. Compare rendered output to the benchmark behavior, not pixel-copy the visual design.
9. Record attribution when permissive source was directly adapted.

## Adoption Tracks

### Track A: Market And Symbol Workstation

References: TradingView, OpenBB Workspace, Korean terminal image, FinanceDatabase.

Build:

- persistent symbol route;
- price/volume chart and timeframe controls;
- quote, fundamentals, news, related events, and provider truth;
- watchlist staging and recent symbols;
- source-linked research notes.

### Track B: Market Map And Screener

References: Finviz and TradingView heatmaps.

Build:

- provider-backed universe;
- sector/industry hierarchy;
- size/color metric controls;
- hover inspector and click-through;
- ETF/crypto variants after equity proof.

### Track C: Global Intelligence Map

References: WorldMonitor, worldview, osiris.

Build:

- full-bleed MapLibre/Leaflet renderer selected after performance proof;
- clustering, time filter, compare, layer health, marker inspector;
- map-linked news, events, assets, and source links;
- explicit unavailable layers for AIS, flights, sanctions, or paid feeds.

### Track D: Options And Quant

References: optlib, quant-traderr-lab, Gold Quant report, existing first-party options modules.

Build:

- user-supplied or provider-backed chain normalization;
- quality checks, Greeks, IV surface, scenario matrix, historical comparisons;
- GEX only from explicit chain/OI assumptions with caveats;
- no execution or recommendation output.

### Track E: Research OS

References: OpenBB Workspace, Dexter, Supabase, HelixDB.

Build:

- reports, notes, citations, watchlists, alerts, and artifact history;
- local-first persistence before hosted accounts;
- event-asset graph query and evidence links;
- optional Gemini free-first summaries that cannot invent source-free claims.

## Hard Boundaries

- No AGPL, NASA, missing-license, or unclear code/assets copied into the proprietary product.
- No scraping of pages that prohibit it.
- No bulk external datasets without terms review.
- No fake live state.
- No trading execution, personalized recommendation, or broker control.
- No secrets in fixtures, logs, screenshots, or release archives.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
