# Phase 6M Attention Contract

Updated: 2026-07-13

## Boundary

`attention_desk.v1` composes previously stored observations. Compose, filter,
review, acknowledge, snooze, checkpoint, policy, and return navigation never
contact a market provider. Provider refresh remains a separate explicit job.

Inputs are Watchlist changes, catalysts, exact-symbol news, Daily Brief claim
changes, provider-health degradation, and War Map event-to-asset evidence.

## Item Contract

Every normalized item carries:

- stable SHA-derived fingerprint and exact origin identity;
- subject identity, change kind, materiality, severity, and review state;
- observation and retrieval clocks kept as separate fields;
- provider, source URL/status, confidence, caveat, and data gap;
- exact drilldown URL and bounded Attention return state;
- deterministic rank score, rank factors, and a non-advisory explanation.

Supported material kinds are `market-change`, `new-evidence`,
`source-degradation`, `stale-evidence`, and `resolved`. `fetch-refresh` is
retained for audit truth but cannot enter the material queue by itself.

Cross-surface copies merge by stable evidence identity while preserving a
source register. Distinct sources are not erased. Ranking is deterministic and
uses severity, unreviewed state, recency, and source-health context. It does not
generate trade, target, recommendation, causal-impact, or urgency claims.

## Private Review State

`AttentionReviewStore` stores tenant-scoped review state, policy, checkpoint,
and bounded generic audit rows. Mutations use optimistic versions and one
SQLite transaction. Supported forward states are review, acknowledge, bounded
snooze, expiry recovery, and safe undo. Provider clocks never move when a user
changes review state.

The public route exposes source evidence only. Account routes derive tenant
identity from the server session and add private review state:

- `GET /api/attention-desk`
- `GET /api/account/attention-desk`
- `PATCH /api/account/attention-desk/items/{fingerprint}`
- `PUT /api/account/attention-desk/policy`
- `POST /api/account/attention-desk/checkpoint`
- `GET /api/account/attention-desk/audit`

## Readiness Truth

The deterministic fixture is demonstrative, not live. Runtime rows may be
live, cached, stale, degraded, static/proxy, or unavailable, and retain their
original source status. External email, SMS, push, webhook, broker action, and
autonomous delivery remain unavailable.
