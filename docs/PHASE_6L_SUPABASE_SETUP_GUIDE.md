# Phase 6L Free Supabase Setup Guide

Updated: 2026-07-10

This is preparation only. Adding values does not mark hosted sync verified.

## Option A: Free Development Project

1. Create a separate development project at <https://supabase.com/dashboard>.
2. Open the project's **Connect** dialog or **Settings > API Keys**.
3. Copy the project URL into `SUPABASE_URL`.
4. Copy a publishable key into `SUPABASE_PUBLISHABLE_KEY`. The legacy anon key
   can use `SUPABASE_ANON_KEY`, but current Supabase guidance prefers the new
   publishable key.
5. Only if a future server adapter explicitly requires administrative work,
   place the secret key in `SUPABASE_SECRET_KEY`. Never use a `NEXT_PUBLIC_*`
   name, browser code, screenshot, fixture, log, or commit. Legacy
   `SUPABASE_SERVICE_ROLE_KEY` is compatibility-only.
6. Keep the project development-only and create disposable Account A/B users.
7. Do not use real customer records during conformance.

Official key guidance:
<https://supabase.com/docs/guides/getting-started/api-keys>.

## Option B: Local Stack

Current official prerequisites are Node, Supabase CLI, and a Docker-compatible
container runtime. From the repository root:

```powershell
npm install --save-dev supabase
npx supabase init
npx supabase start
```

The current repository already has migrations, so review them before applying.
Use `npx supabase db lint` and `npx supabase test db` once pgTAP tests exist.
Official guides:

- <https://supabase.com/docs/guides/local-development>;
- <https://supabase.com/docs/guides/local-development/cli/testing-and-linting>.

## Evidence Required Next

The next hosted-proof run must show real Auth A/B sessions, RLS negative tests,
CRUD/conflict/export/delete, session expiry/revocation, outage/recovery,
backup/restore, cleanup, measured latency, and a secret scan. Until then the UI
must continue to show Hosted unavailable.

