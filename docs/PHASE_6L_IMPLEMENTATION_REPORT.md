# Phase 6L Implementation Report

Updated: 2026-07-10

## Delivered

- Fixed Watchlist Desk's full ProductNav from a 58px track to the established
  10.5rem product rail. The measured rail is now 168px with no text overflow.
- Added `lib/tenant_research_persistence.py` and
  `lib/tenant_research_sync.py` for repository, adapter, snapshot, queue,
  reconciliation, audit, retry, cancellation, and hosted gate behavior.
- Upgraded workspace schema to v12 with local queue/audit tables.
- Added account sync FastAPI routes, API manifest descriptors, and strict
  same-origin Next proxy allow-list entries.
- Added a compact Research Sync console to Account Research with local,
  pending, conflict, offline, and Hosted unavailable truth.
- Added deterministic `Attention queue` ranking by review state, severity, and
  source degradation. It is in-app triage, not a recommendation or push alert.
- Added modern Supabase publishable/secret environment aliases while preserving
  legacy anon/service-role compatibility. Secret-class values remain server-only.
- Added the visual version registry, Phase 6L capture harness, deterministic QA
  seed, and Phase 6L performance harness.

## Product Journey

```text
local Watchlist remains useful with zero account request
-> user opens Account Research
-> explicit import creates tenant-owned exact identities
-> saved observations produce source-aware material changes
-> Attention queue shows what deserves review first
-> user reviews an 8-record private-field-free sync plan
-> explicit consent queues one local offline intent
-> hosted state remains unavailable because no verified endpoint exists
-> account API outage leaves the local Watchlist/chart workflow intact
```

## Honest Limits

No hosted auth, live RLS, cross-device sync, external notification, background
worker, billing, broker route, or autonomous action was added. The Supabase
adapter deliberately fails closed.

