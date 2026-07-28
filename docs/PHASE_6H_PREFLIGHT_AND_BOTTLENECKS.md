# Phase 6H Preflight And Bottlenecks

Updated: 2026-07-03

## Baseline

- The durable objective, Phase 6H prompt, root and web agent rules, workflow,
  review checklist, all six repository skills, and the relevant external
  process skills were read before product edits.
- Python 3.14.5, Node 24.16.0, npm/npx 11.13.0, and 28 required external
  archives are present.
- `914 tests collected`; the full fail-fast suite passed. Compileall, import
  smoke, fixture validation, web tests, lint, production build, and npm audit
  also passed. npm reported zero high-severity vulnerabilities.
- The baseline release has 1,593 entries and includes `apps/web`, `backend`,
  `lib`, and `docs`. It excludes plaintext `.env`, external archives,
  `review_workspace`, databases, and `node_modules`; `.env.example` is the only
  environment template.
- Alpha Vantage, Finnhub, and Gemini variables are configured by presence-only
  inspection. No credential value was printed or persisted.
- The in-app browser connection is unavailable. The repository
  Playwright/Chrome production harness is the required visual-QA fallback.

## External And Benchmark Gate

The deterministic Phase 6H audit inspected all 28 supplied archives:

| Disposition | Count |
|---|---:|
| Direct-use-allowed | 18 |
| Behavior-only | 6 |
| Needs exact-path review | 3 |
| Blocked | 1 |

The audit produced 24 feature candidates plus archive, license, and line
inventories under `review_workspace/external2_analysis/phase6h`. No external
source, dataset, font, image, or visual asset is copied.

Personally inspected user references reinforce these behaviors:

- OpenBB: source-aware widgets with one shared ticker context and independent
  widget controls;
- TradingView: chart-first synchronized symbol, interval, and range context;
- Bloomberg-like terminal references: dense simultaneous research context and
  fast verified actions;
- Finviz and Korean terminal references: scan-first hierarchy and compact
  metrics, not decorative dashboard filler;
- WorldMonitor/worldview and War Room references: map/event context is useful
  only when evidence and coordinates are exact and inspectable.

Official current evidence:

- OpenBB widgets combine source, metadata, presentation, and parameters; linked
  parameters synchronize widgets:
  https://docs.openbb.co/workspace/analysts/widgets/overview
- TradingView multi-chart layouts synchronize symbol, interval, time, and date
  range:
  https://www.tradingview.com/support/solutions/43000629992-how-to-sync-the-charts-of-my-layout/
- Bloomberg Launchpad describes dynamic monitors, alerts, charting, and news in
  a customized workspace:
  https://www.bloomberg.com/professional/products/bloomberg-terminal/

Adopted behavior is reimplemented with project-native contracts and styling.
AGPL, NASA, missing-license, unclear-license, mixed-license, and blocked
archives remain behavior-only unless an exact-path review later permits use.

## Current Bottlenecks

Phase 6E proves exact progressive symbol delivery, and Phase 6G proves a saved
Change Inbox, but the user still crosses isolated routes to answer one research
question. The present workstation shows only one analytical panel at a time.

The concrete bottlenecks are:

1. Chart, financial, catalyst/news, source, and saved-change evidence are not
   simultaneously visible.
2. Symbol, interval, range, panel, and return state do not have one explicit
   synchronization contract.
3. Client requests have ETag caching but no shared in-flight deduplication.
4. A refresh error can discard a previously loaded same-symbol panel instead of
   retaining it as last-known-good evidence.
5. Mobile must avoid fetching hidden panels while desktop still needs useful
   complementary evidence in the first viewport.
6. Layout state needs a bounded local-only persistence contract with no private
   note, credential, provider body, or unsafe path leakage.

## Architecture Decision

- Add a compact project-native `analyst_workspace.v1` composition contract.
  It references existing exact panel deliveries instead of copying chart rows,
  source registers, or provider adapters.
- Add one exact-symbol workspace route and preserve the existing asset route as
  a regression-safe single-panel surface.
- Server-render identity, quote/source clocks, layout manifest, endpoint
  references, and one exact saved primary chart. The client independently
  revalidates that chart in cache/live modes and progressively loads secondary
  exact panel payloads.
- Desktop may request the primary chart and at most three visible secondary
  panels. Mobile requests only the focused panel until the user selects
  another.
- Deduplicate equal in-flight requests, reuse ETags, and retain same-symbol
  last-known-good panel data when a later request fails.
- Persist only validated layout preset, bounded split, panel visibility/order,
  focus, symbol, interval/range, and safe origin state in URL/local storage.
- Map and command actions are links to verified product routes. No broker,
  order, alert-delivery, hosted-sync, or AI-action claim is introduced.

## Acceptance Budgets

- Compact workspace manifest below 30 KB.
- Initial analyst workspace HTML below 100 KB.
- Primary useful-chart timing and roughly 69.8 KB chart-core payload do not
  materially regress from Phase 6E.
- Cached secondary-panel p95 below 250 ms on the local QA machine.
- Zero hidden-mobile full-panel requests before user action.
- Equal exact panel requests are deduplicated.
- No broad watchlist/universe fan-out and no increase to the existing
  five-symbol/16-call refresh ceiling.
