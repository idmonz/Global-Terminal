# Phase 6M Preflight And Branch Decision

Updated: 2026-07-13

## Decision

Phase 6M starts with a **hosted project reachable, schema not provisioned**
branch. The product must continue to report hosted persistence as unavailable.
This is not the former missing-project state, but it is also not hosted proof.

Post-phase reconciliation (2026-07-14): this entry condition was superseded
during Phase 6M. `PHASE_6M_HOSTED_CONFORMANCE_EVIDENCE.md` records 14 deployed
tables and basic Auth/CRUD/A-B RLS checks, and a current endpoint probe confirms
the 14 endpoints remain present. Full hosted verification is still withheld.

Environment presence was checked without printing values:

- `SUPABASE_URL`: present with a hosted project URL shape;
- `SUPABASE_PUBLISHABLE_KEY`: present with the current publishable-key shape;
- legacy anon key: absent;
- server secret/service-role key: absent;
- Management access token, project ref, DB URL, and DB password: absent;
- Supabase CLI 2.109.1: installed but not authenticated;
- Docker-compatible runtime: absent;
- Node 24.16.0 and npm 11.13.0: available.

The Auth settings endpoint returned HTTP 200 and email auth is enabled. Direct
PostgREST probes reached the project boundary, but all ten expected
`global_terminal_*` tables returned HTTP 404. No migration, test identity, or
product record has been created in the hosted project.

The publishable key is intentionally insufficient for DDL or administrative
user setup. Applying schema through an elevated browser key would be unsafe.
The supported next hosted action is either an authenticated Supabase CLI plus
database password or a reviewed SQL Editor application by the project owner.

## Security Stop Found Before Provisioning

The Phase 6J workspace-preference policies contain an unqualified
`tenant_id` inside a membership subquery. PostgreSQL name resolution can bind
that reference to the inner membership relation, reducing the intended tenant
join to a tautology. The migrations will not be pushed until a regression test
and a fully qualified replacement policy are present.

The tenant bootstrap path is also not yet represented in the migration set.
Hosted conformance therefore cannot honestly create Account A/B memberships
with only the public client key.

## Baseline

- deterministic external audit: 28 archives, 24 feature candidates;
- license matrix: 18 direct-use allowed, 6 behavior-only, 3 needs review, 1 blocked;
- `python -m pytest -q -x`: passed at 100 percent;
- warnings: one existing Starlette/httpx deprecation and two existing
  cointegration collinearity warnings;
- current Phase 6L screenshots were inspected, including the 168px Watchlist
  Research rail and mobile Attention queue;
- supplied Finviz, TradingView, OpenBB, WorldMonitor, newsroom, and terminal
  references were inspected under clean-room rules.

## Phase 6M Continuation

Missing administrative Supabase credentials do not block the local-first
Attention Desk. Phase 6M proceeds against stored observations and keeps all
compose, filter, review, snooze, and return navigation at zero market-provider
calls. Hosted status may change only after migrations, real Auth A/B sessions,
RLS negative tests, CRUD/conflict/export/delete, expiry/revocation, outage and
recovery, cleanup, latency, and secret scans all pass.

Official references:

- <https://supabase.com/docs/guides/getting-started/api-keys>
- <https://supabase.com/docs/reference/cli/supabase-orgs-list>
- <https://supabase.com/docs/guides/database/postgres/row-level-security>
- <https://supabase.com/docs/guides/local-development/testing/overview>

## Final Hardening Result

The ambiguous policy and missing bootstrap path were corrected before any
hosted push in `20260711234452_phase6m_attention_and_rls_hardening.sql`. Qualified
tenant predicates, a security-definer bootstrap with empty search path,
`auth.uid()` identity, advisory locking, Attention tables, grants, RLS, and
policies are now represented and tested locally. The project-owner CLI/SQL
authorization gate remains, so hosted state is still unavailable. See
`docs/PHASE_6M_SUPABASE_HOSTED_PROVISIONING_HANDOFF.md`.
