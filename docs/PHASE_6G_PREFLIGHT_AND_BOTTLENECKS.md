# Phase 6G Preflight And Bottlenecks

Updated: 2026-07-03

## Baseline

- Durable goal, Phase 6G prompt, root/web agent rules, workflow, checklist, all
  six repository skills, and the relevant external process skills were read.
- `906 tests collected`; `python -m pytest -q -x` passed.
- Compileall, import smoke, fixture validation, web lint, production build, and
  npm audit passed; npm reported zero vulnerabilities.
- Baseline release contained 1,581 entries and zero `.env`, external,
  `review_workspace`, `node_modules`, private-data, cache, or database paths.
- Alpha Vantage, Finnhub, SEC User-Agent, and Gemini variables are configured in
  `.env` by presence-only inspection. No value was printed.
- The in-app browser connection was unavailable. The repository production
  Chrome/Playwright harness is the required fallback.

## External And Benchmark Gate

The deterministic Phase 6G audit inspected all 28 supplied archives:

| Disposition | Count |
|---|---:|
| Direct-use-allowed | 18 |
| Behavior-only | 6 |
| Needs exact-path review | 3 |
| Blocked | 1 |

It indexed 51,305 archive entries and produced 24 candidate behavior rows under
`review_workspace/external2_analysis/phase6g`. No external source or visual
asset will be copied.

Observed benchmark behavior:

- TradingView advanced Watchlists combine scan-first metrics, earnings,
  dividends, news, grouping, and list-wide alert conditions.
- TradingView Alert Manager exposes active/triggered/manual-stop/expired states
  and sortable event history.
- OpenBB widgets keep source metadata and parameters attached to the visual
  object; linked parameters synchronize a workflow.
- Bloomberg's public Enterprise Console description emphasizes one operations
  view for events, acknowledgements, messages, schedules, health, and alerts.
- Finviz reference imagery reinforces dense scan-first hierarchy, not decorative
  dashboard cards.

Adopt the behavior contract, not code, imagery, fonts, datasets, or trade dress.

## Current Bottleneck

Phase 6F stores complete normalized rows and provider budgets in
`watchlist_materialization_jobs.rows_json`, but the product reads only the latest
job. Users cannot answer:

1. What materially changed since the prior successful refresh?
2. Did source quality improve or degrade?
3. Is refresh manual, eligible, busy, disabled, failed, or stale?
4. Would a change produce a new notification, a duplicate, or a cooldown skip?

## Architecture Decision

- Keep schema v8. Existing job records already contain list ID, job ID,
  timestamps, public rows, and provider ledger.
- Add a pure `research_snapshot_diff.v1` engine with deterministic IDs and zero
  provider I/O.
- Query the latest attempt separately from the latest two successful jobs.
- Reuse `alert_rules`, `alert_events`, expiry, cooldown, and local-private DB
  boundaries; extend the allowed scope to `watchlist_change`.
- Notification delivery remains `preview-only`. No email, SMS, push, webhook,
  cloud, broker, or AI action is added.
- Background refresh remains disabled by default and is never described as an
  installed service. Existing manual refresh remains the safe action.

## Acceptance Budgets

- Five-symbol diff p95 below 100 ms.
- Diff payload below 100 KB.
- Watchlist initial HTML below 100 KB.
- Change filtering, sorting, selection, and preview inspection make zero
  provider calls.
- Existing Phase 6E/6F exact-symbol and chart budgets must not regress.

## Primary Official Evidence

- https://www.tradingview.com/support/solutions/43000771546-watchlist-advanced-view-mode/
- https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/
- https://www.tradingview.com/support/solutions/43000595311-manage-alerts/
- https://docs.openbb.co/workspace/analysts/widgets/overview
- https://www.bloomberg.com/professional/products/data/data-connectivity/enterprise-console/
