# Phase 6F Preflight And Provider Budget

Updated: 2026-07-03

## Decision

Phase 6F extends the existing `watchlist_materialization_jobs` workflow. It
does not create another scheduler, queue, or request-time row enrichment path.
The saved job rows become the public normalized Research Snapshot used by the
Watchlist and exact-symbol Catalyst panel.

## Verified Baseline

- `python -m pytest -q -x`: passed across the current suite.
- The existing materialization lock is list- and database-scoped.
- One yfinance multi-symbol history request primes exact-symbol history caches.
- Exact-symbol summary, chart-core, technicals, financials, news, comparison,
  and sources delivery panels already use additive JSON contracts and ETags.
- Alpha Vantage and Finnhub keys are configured by presence check only. No key
  value was printed or copied.
- The deterministic external audit inspected all 28 required archives and
  wrote evidence under `review_workspace/external2_analysis/phase6f`.
- External audit disposition: 18 direct-use-allowed, 6 behavior-only, 3
  needs-review, and 1 blocked. Phase 6F remains clean-room and project-native.

## Provider Inventory

| Need | Existing adapter/cache | Phase 6F use |
|---|---|---|
| Price/history | yfinance `fetch_multi_history`, exact history runtime cache | One bounded batch per list refresh |
| Performance/risk/technicals | `compute_watchlist_advanced_metrics` | Derive from saved exact history; zero provider calls |
| Fundamentals | Alpha Vantage `OVERVIEW`, 6-hour TTL/LKG | One call per selected equity when refresh is allowed |
| Company profile | Finnhub profile, 6-hour TTL/LKG | Not called by the default list job; exact financial panel may use it on demand |
| Earnings | Finnhub earnings calendar, 6-hour TTL/LKG | One call per selected equity |
| Dividends | Alpha Vantage overview dividend and date fields | Reuse the fundamentals call; no extra request |
| Exact news | Finnhub company news, 15-minute TTL/LKG | One call per selected equity with strict symbol evidence |
| SEC facts | Existing SEC EDGAR adapter/cache | Exact financial panel only; no list-level fan-out in this slice |

## Default Hard Budget

For at most five selected symbols:

| Provider/operation | Maximum calls |
|---|---:|
| yfinance multi-history | 1 |
| Alpha Vantage overview | 5 |
| Finnhub earnings calendar | 5 |
| Finnhub company news | 5 |
| **Total** | **16** |

Alpha Vantage documents a standard free limit of 25 requests per day. The
default plan therefore consumes at most five Alpha calls, not the 15 calls that
would result from invoking overview, earnings, and news separately for every
symbol. Finnhub returns HTTP 429 when a plan limit is exceeded and also
documents a platform ceiling; the local job is additionally serialized and
bounded to ten Finnhub calls.

## Cache And Failure Contract

- Read a fresh provider cache before spending a call.
- A stale cache may be retained as last-known-good when refresh fails.
- Never convert `rate-limited`, `provider-error`, `missing-key`, or stale data
  into `live/fresh`.
- Missing values remain `null` with a visible `data_gap`; they are never zero.
- A provider response is untrusted until normalized at the adapter boundary.
- Saved rows contain public normalized fields only. Private watchlist reasons
  remain in their existing local-private table and never enter jobs, URLs,
  logs, fixtures, screenshots, AI context, or release archives.

## Job Observability

The materialization result must expose:

- planned and actual calls by provider and operation;
- fresh cache hits, stale fallback hits, failures, blocked and skipped work;
- requested/completed/failed/skipped symbol counts;
- duration, queue depth, overlap/busy state, and next safe refresh time;
- per-symbol source register, fetched/as-of clocks, confidence, caveat, and
  data gap.

No response body, credential, private reason, or unbounded identifier is a
metric/log label.

## Product Acceptance Target

The five-symbol QA list is AAPL, TSLA, JNJ, TTE, and TMUS. At least four rows
must have price/performance plus one verified fundamental or catalyst in the
successful fixture/live-capable path. UI mode, sort, and group changes read the
saved snapshot and make zero provider requests.

## Primary Evidence

- Alpha Vantage premium/free-limit page:
  https://www.alphavantage.co/premium/
- Finnhub API authentication and rate-limit behavior:
  https://finnhub.io/docs/api/quote
- SEC EDGAR fair-access threshold:
  https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits
- TradingView advanced Watchlist fields and modes:
  https://www.tradingview.com/support/solutions/43000771546-watchlist-advanced-view-mode/
- OpenBB source-aware widget model:
  https://docs.openbb.co/workspace/analysts/widgets/overview

Outputs are research calculations and information displays only. They are not
investment advice, recommendations, broker actions, or execution instructions.
