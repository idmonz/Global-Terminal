# Phase 6P External Audit And Benchmark Report

Updated: 2026-07-16

## Full External Audit

The complete requested external directory was mechanically re-indexed after
the Phase 6P implementation:

- archives: 28;
- files: 51,305;
- text candidates: 39,622;
- lines: 10,596,233;
- indexed symbols: 249,590;
- read errors: 0.

Artifacts:

- `docs/PHASE_5F_EXTERNAL_FULL_INVENTORY.csv`;
- `review_workspace/external2_analysis/phase5f/external_full_inventory_summary.json`;
- summary SHA-256:
  `5D37EDC71F42C19D6EF92188A44294631EBDDDDE552694AEBA6BE67464048CEB`.

Mechanical indexing proves coverage, not permission to copy. AGPL, NASA,
missing-license, and unclear-license projects remain behavior-only or blocked.
No external code, visual asset, credential, dataset row, or brand treatment was
copied in Phase 6P.

## Current Official Benchmarks

TradingView's current watchlist workflow combines customizable lists, sorting,
key metrics, news, fundamentals, technical summaries, notes, advanced grouping,
import/export, and per-symbol watchlist alerts. Global drawing synchronization
also depends on explicit synchronization/autosave behavior:

- https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/
- https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/
- https://www.tradingview.com/support/solutions/43000629998-my-drawings-do-not-get-synchronized-across-charts-or-layouts/

OpenBB Workspace currently frames widgets as source-backed analytical units
with metadata, parameters, visualization, parameter linking, searchable
libraries, persistent dashboards, role controls, and app-level workflows:

- https://docs.openbb.co/workspace
- https://docs.openbb.co/workspace/analysts/widgets/overview
- https://docs.openbb.co/workspace/analysts/widgets/ai-generated-widgets

Supabase documents short-lived JWT access tokens, rotating refresh tokens,
session controls, RLS-backed authorization, and the need for Free projects to
create and retain their own logical backups:

- https://supabase.com/docs/guides/auth/sessions
- https://supabase.com/docs/guides/platform/backups
- https://supabase.com/docs/reference/cli/supabase-login

## Adoption Decisions

- Adopt the behavioral expectation that saved research survives a new session,
  conflicts are explicit, and users can export/delete their bounded state.
- Adopt OpenBB-style source/status metadata and parameter/state continuity, but
  keep product-native Python/TypeScript contracts and first-party visuals.
- Adopt Supabase user-JWT/RLS/idempotency/audit semantics without exposing a
  service-role key or accepting client-selected tenant identity.
- Preserve local-first research during outages and make recovery a deliberate,
  observable transition instead of silently replacing local data.
- Keep external delivery disabled. The now-complete account data plane allows a
  separate Phase 6Q hosted-scheduler pilot, but recurring jobs remain disabled
  until that deployed-runtime evidence passes.

## Benchmark Verdict

Phase 6P now has a credible account-continuity implementation and controlled UI
proof, which materially improves the prior local-only product. It still trails
TradingView's mature multi-device continuity and always-on alert operations,
and OpenBB's broad customizable/persistent widget ecosystem. Real Phase 6P
owner-run new-session recovery and hosted latency now pass. Session
revocation/expiry, off-site backup operations, deployed recurring scheduling,
production observability, and production deployment SLOs remain unverified. The
relevant benchmark categories remain score 4, not 5.
