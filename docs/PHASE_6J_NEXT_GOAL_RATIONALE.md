# Phase 6J Next Goal Rationale

Updated: 2026-07-10

## Decision

Proceed with **Phase 6K: Tenant-Owned Research Desk And In-App Alert Inbox**.

## Evidence

Phase 6J proves the minimum identity and isolation boundary, but only the
Analyst Workspace layout is account-owned. Watchlists, saved screens, research
memory, report reviews, change alerts, and notification history remain
local-private islands. Moving directly to email/SMS/payment/cloud claims would
skip ownership, consent, dedupe, retention, and recovery behavior.

## Phase 6K Journey

```text
local watchlist/research state
-> signed-in tenant sees an import preview
-> explicit consent imports selected bounded records
-> account-owned watchlist drives existing exact research/change flow
-> qualifying change creates a tenant-owned in-app inbox item
-> review/acknowledge survives reload and stays isolated from Account B
-> offline mode keeps local research usable without false delivery claims
```

Use current stores and contracts. Add no external email/SMS/push delivery,
checkout, broker action, paid dependency, or hosted-success claim. Supabase
stays optional until real credentials and live RLS/recovery tests exist.
