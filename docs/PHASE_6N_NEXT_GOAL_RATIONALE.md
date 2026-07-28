# Phase 6N Next Goal Rationale

Updated: 2026-07-14

## Decision

Select **Phase 6O: Watchlist Alert Rules And Scheduled In-App Monitoring**.

Phase 6N-V is closed. The next highest-value step is to turn the existing
saved-Watchlist observation engine and dormant `lib/alert_*` capabilities into
one visible, tenant-safe Alert Manager journey. This is a product-depth phase,
not a broad platform rewrite.

## Evidence

- Phase 6N now has 23 inspected screenshots, a passing independent visual
  verifier, 1,038 passing tests, zero high-severity npm vulnerabilities, a
  passing runtime smoke, and a secret-clean 1,749-entry release.
- Explicit observation runs are useful, but a user must still remember to run
  them and there is no commercial web Alert Manager with active/paused/
  triggered/expired state and an auditable trigger log.
- The repository already contains `lib/alert_engine.py`, `alert_rules.py`,
  `alert_evaluator.py`, `alert_store.py`, `alert_state_machine.py`, watchlist
  alert helpers, scheduler scripts, preview-only API routes, and substantial
  tests. Phase 6O must consolidate and adopt these before adding modules.
- TradingView treats one watchlist alert as per-symbol evaluations, exposes
  frequency/expiration, and provides active/stopped status plus a trigger log:
  [watchlist alerts](https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/),
  [configuration](https://www.tradingview.com/support/solutions/43000763312-learn-how-to-configure-alerts/), and
  [management](https://www.tradingview.com/support/solutions/43000595311-manage-alerts/).
- Finviz now pairs one-click chart alerts with alert management, while its
  commercial feature set includes push alerts:
  [chart alerts](https://finviz.com/blog/one-click-chart-alerts-are-now-live-for-finviz-members/) and
  [Finviz FAQ](https://finviz.com/help/faq).
- World Monitor combines custom keyword monitors, per-panel new-item state,
  automatic seen tracking, and periodic snapshots; these are behavior-only
  references under the AGPL clean-room boundary:
  [World Monitor features](https://www.worldmonitor.app/docs/features).
- Supabase Cron offers recurring jobs with durable run history and recommends
  bounded concurrency/duration. It is the hosted architecture reference, not a
  readiness claim:
  [Supabase Cron](https://supabase.com/docs/guides/cron).

## Product Gap To Close

The product should support this single journey:

```text
Watchlist Desk
-> create a transparent bounded rule
-> enable, pause, resume, expire, or delete it
-> evaluate it only from a due observation run
-> record a deduplicated in-app trigger with source and clocks
-> review it in Alert Manager / Attention
-> open exact evidence and return
```

Initial rule scope should stay small: price above/below, bounded percent move,
material saved change, and source degradation. Multi-condition scripting,
broker actions, recommendations, email/SMS/push/webhooks, and opaque AI signals
are outside Phase 6O.

## Branch Truth

- **Current executable branch:** local-first, explicit opt-in schedules,
  deterministic fake clock/worker tests, bounded provider quota, in-app-only
  delivery, and manual-run fallback.
- **Hosted branch:** use the existing Supabase adapter/migration path only when
  owner deployment access and real Account A/B Auth/RLS/recovery conformance
  are available. Otherwise show `hosted-unavailable` and continue locally.
- No phase may claim always-on hosted monitoring merely because a schedule
  contract or migration exists.

## Prompt Construction

The next prompt follows the repository next-goal skill and current OpenAI Codex
guidance: state the desired behavior, point to exact code and reproduction
context, preserve constraints, and name verification. It asks for an audit and
one self-contained vertical slice before implementation breadth:
[OpenAI Codex prompting guidance](https://learn.chatgpt.com/docs/prompting#prompting-codex).

## Success Threshold

Phase 6O is complete only when one real local-first watchlist rule can be
created, evaluated from a bounded observation, surfaced in a source-aware
trigger log, reviewed through exact drilldown/return, and proven on desktop and
390px with failure, quota, conflict, offline, and Account A/B states. Contracts
or fixtures alone do not count.
