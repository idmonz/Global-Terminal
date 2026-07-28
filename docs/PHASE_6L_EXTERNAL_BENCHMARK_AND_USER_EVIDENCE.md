# Phase 6L External, Benchmark, And User Evidence

Updated: 2026-07-10

## Complete Archive Gate

The deterministic audit covered all required archives:

`agent-skills`, `ai-website-cloner`, `AutoHedge`, `BB-Terminal`,
`bloomberg-terminal`, `dexter`, `FinanceDatabase`, `helix-db`,
`intruth-factcheck`, `Kronos`, `OctoBot`, `open-design`, `OpenAlice`, `OpenBB`,
`OpenStock`, `optlib`, `osiris`, `quant-traderr-lab`, `QuantDinger`, `ruflo`,
`supabase`, `superloopy`, `tensortrade`, `TradingAgents`, `worldmonitor`,
`worldview`, `yfinance`, and `zipline`.

Results:

- 28 archives and 51,305 entries;
- 38,623 indexed non-vendored text files and 8,742,912 lines;
- 24 feature candidates;
- license matrix: 18 direct-use-allowed, 6 behavior-only, 3 needs-review,
  1 blocked;
- feature adoption matrix: 14 direct, 5 behavior-only, 3 needs-review,
  2 blocked.

The audit artifacts are generated under
`review_workspace/external2_analysis/phase6l/`. Mechanical line indexing is not
misrepresented as human semantic review of 8.7 million lines. Relevant
attention, watchlist, alert, cache, state, audit, security, and browser-skill
paths were inspected semantically after the full inventory gate.

## Clean-Room Adoption

- external agent skills informed contract-first TDD, API boundaries, security,
  observability, performance, browser QA, and shipping;
- Supabase informed migration/RLS/auth readiness only;
- WorldMonitor informed cache/circuit/dedupe and multi-source operational
  behavior only;
- OpenBB informed source-aware linked workspace behavior only;
- OpenStock/OpenAlice/OpenBB/WorldMonitor/worldview and blocked/unclear sources
  were not copied;
- no external visual asset, screenshot, dataset, font, model, or trade dress was
  added to the product.

## Current Product Comparison

- TradingView shows that watchlists are most useful when metrics, details,
  notes, news, and alert management remain adjacent:
  <https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/>.
- OpenBB makes provenance and linked parameters part of each analytical widget:
  <https://docs.openbb.co/workspace/analysts/widgets/overview>.
- Koyfin centralizes price, valuation, technical, document, watchlist, and
  portfolio alerts rather than scattering them across pages:
  <https://www.koyfin.com/features/alerts/>.
- WorldMonitor's architecture explicitly tests cache keying, circuit breakers,
  validation, dedupe, health, and layer guardrails:
  <https://github.com/koala73/worldmonitor/blob/main/ARCHITECTURE.md>.

Global Terminal now compares well on dense source truth, exact drilldown,
local-first privacy, explicit unavailable states, and deterministic review. It
still trails on cross-source attention unification, hosted multi-device state,
licensed breadth, always-on workers, and verified map layers.

## User Problem Decision

Observed user pain is not simply "more data needed":

- repeated checking makes small moves feel material and causes users to revisit
  an unchanged thesis;
- jumping between price, news, filings, map events, and notes increases context
  switching;
- raw notifications obscure source degradation and repeated copies;
- users need a reasoned "what changed" view with exact evidence and control over
  review cadence.

Evidence includes recent direct user reports of checking ten or more times per
day and becoming overwhelmed by small moves and abundant data:
<https://www.reddit.com/r/investingforbeginners/comments/1qtv043/started_tracking_my_portfolio_daily_and_realized/>.

Phase 6L responded with Attention ranking and no push noise. Phase 6M will unify
the existing evidence streams into one bounded daily review loop.

