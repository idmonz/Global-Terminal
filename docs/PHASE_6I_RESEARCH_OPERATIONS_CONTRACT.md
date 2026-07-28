# Phase 6I Research Operations Contract

Updated: 2026-07-04

## Contract

`research_operations.v1` is a compact, JSON-safe operational view over one
exact analyst workspace. It does not duplicate chart history, financial
statements, news bodies, raw provider responses, or private logs.

## Exact Identity

Every contract is scoped by:

- normalized symbol and asset class;
- interval and range;
- requested panel allowlist;
- deterministic request identity;
- workspace and panel delivery versions.

Unknown symbols and panels fail closed. LKG may be retained only when symbol,
panel, interval/range applicability, and delivery version match.

## Panel Freshness

Each panel row contains:

- panel ID and exact symbol;
- provider and safe source URL;
- source status;
- retrieval clock;
- market/event observation clock;
- retrieval age and observation age;
- target freshness seconds;
- `within-slo`, `aging`, `stale`, `unavailable`, or `not-applicable`;
- last attempt and last successful/LKG clocks;
- caveat and data gap.

Fresh retrieval does not make an old market/event observation current. Missing
clocks remain `null`, never zero.

Initial SLO policy:

| Panel | Target |
|---|---:|
| chart-core | 15 minutes |
| technicals | 15 minutes |
| comparison | 15 minutes |
| financials | 24 hours |
| catalysts | 15 minutes retrieval, event clock kept separately |
| news | 15 minutes |
| sources | 15 minutes |

The policy is versioned and may later become market-session aware.

## Provider Observation

An operational provider row distinguishes:

- configured;
- contacted;
- successful;
- cached;
- stale;
- rate-limited;
- forbidden/subscription-blocked;
- missing-key;
- unavailable;
- proxy/static.

Configured is not contacted. Contacted is not successful. Cached is not live.
The public row contains only provider, panel, status, safe source URL, bounded
clock/count fields, caveat, and data gap.

## Refresh Budget

The default exact-workspace request is:

- `chart-core`: at most 1 provider refresh;
- `financials`: at most 7 provider operations;
- `catalysts`: cache/LKG only, 0 provider calls;
- `sources`: composition only, 0 provider calls.

The hard exact-workspace ceiling is 8 provider operations. The budget is
computed before execution and includes planned, actual, cache, stale, failed,
rate-limited, and skipped counts. Actual counts use the project-defined
operation accounting boundary and never exceed the planned ceiling.

This does not change the existing five-symbol Watchlist ceiling of 16 calls.

## Job State

Allowed states:

- `queued`
- `running`
- `completed`
- `partial`
- `rate-limited`
- `failed`
- `cancelled`
- `overlap`

Each job exposes a bounded event history, progress counters, last attempt, last
success, next safe retry, retry reason, and overlap state. Equal active
requests return the same job. A different active request for the same symbol is
rejected as overlap. No blind retry loop exists.

## Persistence And Runtime Truth

Only bounded operational metadata is stored in local-private SQLite. Public
responses redact private fields and never contain local paths.

- process-local worker: available while the FastAPI process is running;
- installed background service: false;
- hosted scheduler: false;
- notification delivery: false;
- remote cancellation/control: false;
- kill-switch readiness: true;
- broker execution: false;
- autonomous AI action: false.

## API

- `GET /api/analyst-workspace/{symbol}/operations`
- `POST /api/analyst-workspace/{symbol}/refresh`
- `GET /api/research-operations/jobs/{job_id}`

GET responses support stable ETags. POST validates symbol, panel allowlist,
interval, range, and idempotency identity. The Next.js same-origin proxy
forwards only these allowlisted methods and paths.

## UX

The analyst workspace shows:

- one compact operations strip;
- exact provider/freshness/SLO state per visible panel;
- one `Refresh exact workspace` action with estimated maximum calls;
- progress and terminal state through a polite status region;
- last attempt, last success/LKG, and next retry separately;
- stale/LKG evidence remains visible;
- mobile selected-panel state and refresh action before history.

The operations surface remains secondary to the chart and research panels.

Outputs are research calculations and information displays only. They are not
investment advice, recommendations, trade approvals, broker actions,
autonomous actions, or execution instructions.
