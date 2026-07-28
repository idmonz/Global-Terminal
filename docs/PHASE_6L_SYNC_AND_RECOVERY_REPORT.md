# Phase 6L Sync And Recovery Report

Updated: 2026-07-10

## Queue And Reconciliation

- first sync requires explicit boolean consent and an 8-128 character
  idempotency key;
- one snapshot is limited to 25 resources and 30KB;
- active offline queue is limited to 100 mutations and replay batch to 10;
- retries use bounded exponential delay and stop at five attempts;
- same-version identical rows dedupe;
- local-newer and remote-newer remain named review actions;
- equal-version content differences remain conflict;
- local or remote deletion remains an explicit deletion decision;
- retry and cancellation are shown only when backed by a real action.

## Failure Proof

The deterministic adapter exercised offline -> retrying -> applied and
same-version conflict. Production uses the blocked Supabase adapter, so replay
returns offline and leaves the local queue and Account Research usable. It does
not imply that a background worker will later upload the record.

The browser harness blocks every `/api/account/**` request and proves that the
local five-symbol Watchlist, chart, tabs, refresh controls, and materialization
health remain present. Separate screenshots capture the account failure state
and the retained local research surface.

## Hosted Gate

`configured` means URL plus publishable/legacy anon key are present. It still
means `contacted=false`, `successful=false`, and `hosted_verified=false` until
the full live conformance matrix passes.

