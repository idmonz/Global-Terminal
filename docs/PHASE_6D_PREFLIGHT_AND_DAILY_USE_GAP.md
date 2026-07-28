# Phase 6D Preflight And Daily-Use Gap

Updated: 2026-07-02

## Objective

Turn Phase 6C exact-symbol coverage into a daily-use Watchlist Desk with
local-private persistence, bounded materialization, panel-split delivery, visible
refresh health, and fast symbol switching.

## Harness And Skills

The durable goal, `AGENTS.md`, Phase 6D prompt, roadmap, scorecard, every Phase 6C
report, and all six repository skills were read before product edits. Relevant
external agent skills for API/interface design, browser testing, incremental
implementation, observability, performance, security, shipping, and TDD were
also read as process evidence only.

The in-app browser runtime was initialized according to the bundled browser
skill, but the `iab` target was unavailable. Browser discovery showed only the
user Chrome extension, so no unrelated browser backend was substituted. The
repository Playwright/Chrome visual harness remains the controlled fallback.

## Toolchain And Configuration

- Python 3.14.5;
- Node 24.16.0;
- npm 11.13.0;
- collected tests: 883 across 443 files;
- local FastAPI baseline: `127.0.0.1:8004`;
- production Next.js baseline: `127.0.0.1:3045`;
- SEC, Alpha Vantage, Finnhub, Gemini, and OpenSky OAuth key names are present.

Only key presence was checked. No credential value was printed or recorded.

## Baseline Gates

- full Python `-q -x`: passed, with the existing TestClient deprecation and two
  cointegration collinearity warnings;
- compileall: passed;
- smoke imports: passed;
- deterministic fixture export: 27 fixtures;
- web fixture/runtime test: passed;
- ESLint and Next.js production build: passed;
- npm audit: zero vulnerabilities;
- source release: 1,544 entries;
- forbidden release entries: zero.

## External Audit

The deterministic audit was rerun under
`review_workspace/external2_analysis/phase6d`:

- archives: 28;
- file entries: 51,305;
- indexed non-vendored text/code files: 38,623;
- indexed lines: 8,742,912;
- license classes: 18 direct-use, 6 behavior-only, 3 needs-review, 1 blocked;
- archive hash changes from Phase 6C: zero.

No external code, row dataset, visual asset, font, or trade dress is adopted in
this phase. TradingView/OpenBB/Finviz behavior is clean-room benchmark evidence.

## Existing Watchlist State

- local workspace schema: v7;
- active local watchlist rows: zero in the observed default workspace;
- the existing store supports flat item create/update/archive/search/tag;
- Research Memory exposes add/remove but not named lists, reorder, exact dynamic
  identity validation, materialization health, or fast symbol switching;
- `watch_reason` is local-private and must not enter fixtures, URLs, logs, AI
  context, release archives, or public desk payloads.

## Measured Delivery Gap

Warm cache-mode TSLA, seven local HTTP samples:

| Surface | Bytes | p50 | p95 |
|---|---:|---:|---:|
| Full exact API | 215,223 | 346 ms | 826 ms |
| Next SSR document | 1,071,394 | 1,548 ms | 1,894 ms |

The existing `panels` parameter does not split work or payload. `trend`,
`financials`, `news`, `sources`, and the default multi-panel request each return
approximately 215 KB. `_enrich_workstation()` computes financials, news,
derivatives, comparison, technicals, and all chart specs regardless of selected
surface.

Phase 6C cold exact-symbol composition remains approximately 12.8-14.8 seconds.
The current route is therefore exact but not a fast daily switching desk.

## First-Party Acceptance Contract

1. Named local-private watchlists support create, rename, add, archive, reorder,
   and exact selection.
2. Every asset row resolves against the current symbol identity store.
3. Public desk payloads exclude private reasons and local paths.
4. Materialization is explicit, bounded, overlap-protected, and never rebuilds
   the broad universe.
5. Summary/chart delivery does not invoke financial/news providers.
6. Financial/news/source panels are additive exact-symbol requests.
7. Summary API p50 stays below 250 ms and p95 below 500 ms locally.
8. Initial transfer is materially smaller than the 215 KB API / 1.07 MB SSR
   baseline.
9. Online/cache/failure/offline desktop/mobile flows preserve source truth,
   active symbol, order, and origin.
10. Full tests, visual proof, and release gates pass.

