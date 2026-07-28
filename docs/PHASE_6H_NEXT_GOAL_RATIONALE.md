# Phase 6H Next Goal Rationale

Updated: 2026-07-03

## Decision

Proceed with **Phase 6I: Live Research Operations, Freshness SLOs, And Bounded
Refresh Queue**.

## Evidence

Phase 6H proves a complete composed research journey and live panel delivery.
The next daily-use bottleneck is operational truth:

- the live workspace can show yfinance/SEC data while the global Runtime Health
  chip reports zero providers;
- the chart can be current/cached while catalyst evidence is stale;
- users can revalidate one pane but cannot see a bounded exact-workspace refresh
  plan, quota impact, job state, or next safe retry;
- local schedulers exist, but installation or hosted always-on operation is not
  proven.

Adding another analytical screen would hide this operational gap. The next
slice should make freshness, quota, failures, LKG, and manual bounded refresh
observable and actionable without pretending a local loop is a commercial
hosted service.

## Deferred

- Auth, billing, and tenant isolation remain after operational contracts are
  trustworthy.
- Email, SMS, push, webhook, and broker delivery remain unavailable.
- More provider breadth should follow measured SLO and quota controls.
- External source or visual copying remains prohibited.

## Phase 6I Journey

```text
Analyst Workspace
-> inspect panel freshness and provider budget
-> start one exact bounded refresh
-> observe queued/running/completed/partial/rate-limited state
-> retain same-symbol LKG during failure
-> see corrected provider health and next safe retry
-> return to the same synchronized layout
```

