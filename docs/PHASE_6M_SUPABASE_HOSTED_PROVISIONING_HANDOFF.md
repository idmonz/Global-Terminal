# Phase 6M Supabase Hosted Provisioning Handoff

Updated: 2026-07-13

## Current Truth

The free project URL and publishable key in `.env` are valid and reachable.
Email Auth is enabled. The ten expected `global_terminal_*` tables are absent.
The CLI is installed but not logged in, Docker is absent, and no DB password or
server/admin key is configured. Public keys cannot safely apply migrations.

## Project-Owner Steps

Choose one supported route. Never paste credentials into chat or commit them.

### Authenticated CLI

```powershell
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

The browser login creates CLI authorization. `YOUR_PROJECT_REF` is the short
project identifier shown in the Supabase dashboard URL. `db push` may request
the database password created with the project.

### Dashboard SQL Editor

Open the project's SQL Editor and apply the reviewed files in filename order
from `supabase/migrations/`, ending with
`20260711234452_phase6m_attention_and_rls_hardening.sql`. Do not selectively paste
policy fragments or run them under an unrelated project.

## Required Proof Before Hosted Status Changes

1. Create two real Auth users, Account A and Account B.
2. Bootstrap each tenant through the reviewed server function.
3. Prove A can CRUD its own preference, watchlist, sync, and Attention rows.
4. Prove B cannot list, read, mutate, export, or delete A rows.
5. Prove optimistic conflicts, session expiry/revocation, outage/recovery,
   bounded export/deletion, cleanup, and audit retention.
6. Record hosted latency separately from local SQLite measurements.
7. Rerun exact-value and release scans before enabling hosted UI claims.

Official references:

- <https://supabase.com/docs/guides/cli/getting-started>
- <https://supabase.com/docs/guides/deployment/database-migrations>
- <https://supabase.com/docs/guides/database/postgres/row-level-security>
