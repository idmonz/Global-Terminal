# Phase 6O Preflight And Reuse Map

Updated: 2026-07-15

## Reproduced Limitation

The existing alert surface is not a coherent commercial Alert Manager:

- `lib/alert_*` provides deterministic comparison, expiry, cooldown, and local
  event helpers, but its legacy tables are not tenant-qualified.
- `tenant_alert_rules` stores one material-change preview rule per Watchlist.
  It cannot represent multiple symbol rules, schedules, evaluation runs, or a
  trigger history with separate clocks.
- Watchlist routes expose local `preview-only` change events. No due planner or
  bounded worker evaluates Phase 6N stored observations.
- Watchlist Desk can configure/preview/acknowledge fragments, but users cannot
  create, pause, resume, inspect, or audit a complete rule lifecycle.

Preflight evidence:

- agent harness: pass;
- smoke imports: pass;
- focused legacy alert and Phase 6N tests: pass;
- Phase 6N hosted observation RLS: 27/27 pass, zero provider calls;
- Phase 6O alert persistence, scheduling, and hosted conformance: not yet
  verified and therefore unavailable.

## Reuse And Retirement Decisions

| Existing path | Decision | Phase 6O role |
|---|---|---|
| `alert_rules.py` | reuse | Scope/operator validation remains compatible. |
| `alert_evaluator.py` | reuse through adapter | Deterministic comparisons and missing-data behavior; Phase 6O supplies validated stored observations. |
| `alert_state_machine.py` | reuse | Expiry, cooldown, and transition semantics. |
| `alert_deduper.py` | retire from new writes | Legacy SQL `LIKE` dedupe remains compatibility-only; Phase 6O uses stable tenant-qualified fingerprints. |
| `alert_store.py` legacy tables | compatibility-only | Existing Streamlit/lab tests continue to work; commercial account writes use tenant-qualified Phase 6O tables. |
| `tenant_alert_rules` / `tenant_inbox_items` | compatibility input | Existing material-change preview remains readable and is labeled legacy preview. It is not the Phase 6O rule store. |
| Phase 6N observation runs/snapshots/quota | reuse | Sole source of saved observations, source clocks, LKG truth, and bounded provider accounting. |
| Attention exact-evidence routing | reuse/extend | Trigger rows link to Analyst, News, Brief, and Map and return to the same manager state. |
| Watchlist preview routes | deprecate visibly | Kept for backward compatibility; new UI and account routes use the manager contract. |

## Clean-Room Benchmark Decisions

- Adopt TradingView behavior: independent per-symbol evaluation, explicit
  frequency/session/expiration, active/stopped/expired reasons, compact
  management controls, and a separate trigger log.
- Adopt World Monitor behavior only: make newly triggered and reviewed items
  distinguishable while preserving source-aware activity history.
- Adopt Supabase Cron architecture only: schedules and run history are separate
  records. Hosted scheduling is unavailable until migration, RLS A/B, and
  recovery evidence pass.
- No external source, visual asset, notification channel, broker action, or
  opaque AI condition is copied or introduced.

Official evidence checked on 2026-07-15:

- https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/
- https://www.tradingview.com/support/solutions/43000763312-learn-how-to-configure-alerts/
- https://www.tradingview.com/support/solutions/43000595311-manage-alerts/
- https://supabase.com/docs/guides/cron
- https://www.worldmonitor.app/docs/features

## Product Slice

The first complete journey is:

```text
saved Watchlist -> create rule -> due plan -> evaluate stored Phase 6N snapshot
-> dedupe/cooldown -> in-app trigger -> inspect exact evidence -> return
```

Page reads, filtering, review, export, and navigation must make zero market
provider calls. The optional local worker is disabled until explicit opt-in.

