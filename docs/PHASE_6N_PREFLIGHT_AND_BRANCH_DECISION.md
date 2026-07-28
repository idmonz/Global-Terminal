# Phase 6N Preflight And Branch Decision

Updated: 2026-07-13

## Decision

Phase 6N proceeds on the **local-first, account-contract-ready** branch. The
configured Supabase project is reachable, email Auth is enabled, and the 14
Phase 6J-6M product endpoints are present. Historical Phase 6M evidence records
successful basic tenant bootstrap, CRUD, and A/B RLS isolation. The current
environment still has only a project URL and publishable key: there is no
Management access token, project ref, database password/URL, server secret,
service-role key, authenticated CLI session, Docker-compatible runtime, or
current A/B test identity set.

The publishable key must not be used for DDL or administrative provisioning.
The publishable key cannot deploy the Phase 6N migration. Hosted observation
persistence therefore remains `unavailable`. Phase 6N will prove the complete
tenant-qualified observation-run lifecycle with SQLite, provide a reviewed RLS
migration for the four additional hosted tables, and retain the hosted
conformance handoff until project-owner access exists.

## Baseline

- agent harness: valid, six repository skills, exactly one active plan;
- Python: 1,007 tests collected and the full suite passed;
- existing warnings: one Starlette/httpx deprecation and two cointegration
  collinearity warnings;
- web: fixture/runtime validators, ESLint, TypeScript, and Next.js production
  build passed;
- Node/npm/npx: available from the existing Phase 2D+ toolchain;
- Supabase CLI: 2.109.1, installed but unauthenticated;
- Docker-compatible runtime: unavailable;
- Supabase Auth settings: HTTP 200, email enabled, phone disabled;
- Alpha Vantage and Finnhub keys: present; values were not printed;
- Supabase URL and publishable key: present; secret/admin values absent.

## Provider And Quota Branch

Alpha Vantage's current official support page states that the free service is
limited to 25 requests per day. Finnhub's official API introduction documents
HTTP 429 for exceeded limits and a 30 calls/second ceiling across plans, but it
does not establish this key's exact plan allowance. Phase 6N will therefore:

- cap one observation run at five saved symbols;
- plan at most one batched history call, five Alpha Vantage overview calls,
  and ten Finnhub earnings/news calls;
- account for actual network attempts separately from cache and skipped work;
- use a conservative local Finnhub run budget and stop on 429 without blind
  retries;
- expose next-safe timing and quota-deferred capabilities;
- make no provider call from Attention compose, filter, review, checkpoint,
  policy, snooze, return navigation, or page load.

Official evidence:

- <https://www.alphavantage.co/support/>
- <https://finnhub.io/docs/api/introduction>

## External And Visual Gate

The deterministic Phase 6N entry audit indexed all 28 required archives under
`review_workspace/external2_analysis/phase6n-start/`:

- 18 direct-use allowed;
- 6 behavior-only;
- 3 needs review;
- 1 blocked;
- 24 feature candidates;
- complete zip inventory and non-vendored text/code line inventory.

All supplied Finviz, TradingView, OpenBB, WorldMonitor, newsroom, terminal,
heatmap, and War Room images were inspected together with the final Phase 6M
Attention and Watchlist captures. The current Attention surface already has a
strong dense review queue and evidence rail. Its visible commercial gap is the
absence of an explicit, understandable observation-run control surface showing
last success, source/session truth, quota, progress, cancellation, partial/LKG
recovery, and the resulting material changes.

TradingView's current official watchlist documentation reinforces the product
need for list-wide monitoring, symbol-level independence, session choice, and
clear status/history. Phase 6N adopts those user behaviors clean-room while
preserving source clocks and avoiding external push delivery:

- <https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/>
- <https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/>

No external source, screenshot, font, dataset, response body, or trade dress
will be copied. AGPL/NASA/blocked/unclear sources remain behavior-only.

## Implementation Branch

The existing synchronous `materialize_watchlist()` remains a compatible local
engine. Phase 6N will add a tenant-scoped run coordinator around existing
symbol resolution, runtime cache, Alpha Vantage, Finnhub, yfinance history,
research snapshot, diff, provider-health, and Attention normalization modules.
The new boundary will provide:

1. stable idempotent run identity and single-flight per saved list;
2. explicit queued/running/partial/completed/cancelled/failed transitions;
3. bounded capability/session/quota planning before any provider request;
4. atomic validated snapshot commits with last-known-good preservation;
5. stored material diffs consumed by Attention with zero additional calls;
6. server-derived tenant ownership, CSRF/origin/rate/body bounds, and audit;
7. a compact first-viewport run strip in the commercial Next.js product;
8. deterministic fixtures plus controlled live/cache/stale/offline evidence.

Supabase RLS follows the official fail-closed guidance: exposed tables require
RLS, ownership predicates use `auth.uid()`, and tenant/user columns are indexed.
Hosted success will not be claimed until real Account A/B Auth and RLS negative
tests pass: <https://supabase.com/docs/guides/database/postgres/row-level-security>.
