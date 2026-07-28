# Phase 6G Implementation Report

Updated: 2026-07-03

## Outcome

Phase 6G turns the Phase 6F Research Snapshot into a daily saved-change review
workflow. It does not recompute providers while comparing or filtering.

Implemented:

- `lib/research_snapshot_diff.py`
  - deterministic `research_snapshot_diff.v1`;
  - refresh operations and local alert readiness contracts;
  - stable fingerprints, opt-in, dedupe, cooldown, expiry, acknowledgement, and
    kill-switch behavior.
- `lib/watchlist_desk.py`
  - latest attempt is separate from latest and previous successful snapshots;
  - failed attempts do not replace saved last-known-good rows;
  - job metadata no longer duplicates complete snapshot rows in the web payload.
- `lib/api_contracts.py` and `backend/api/app.py`
  - ETag-enabled private change read route;
  - preview-rule, preview-event, and acknowledgement actions.
- `apps/web/src/components/WatchlistDesk.tsx`
  - dense Change mode, type/severity/status filters, before/after evidence,
    source ledger, exact panel drilldown, stateful return, and alert preview
    controls.
- `scripts/run_watchlist_refresh_scheduler.py`
  - one-shot by default;
  - loop mode requires explicit enablement;
  - refresh kill switch and five-symbol cap;
  - existence is not represented as installation.
- `.env.example`
  - documents optional background/kill-switch settings without values or keys.

## Product Boundary

- Alert delivery is local `preview-only`.
- Background service installation, email, SMS, push, webhook, broker actions,
  hosted identity, and billing are not claimed.
- Fixture changes are fictional and labeled.
- Private reasons remain excluded from API payloads, URLs, logs, fixtures, AI
  context, screenshots, and release archives.

## Live Provider QA

Presence-only `.env` inspection confirmed configured Alpha Vantage and Finnhub
keys without printing values. A bounded AAPL check on 2026-07-03 observed:

| Provider operation | Status | Rows |
|---|---|---:|
| Alpha Vantage overview | live/fresh | 20 fields |
| Finnhub earnings calendar | cached | 2 |
| Finnhub company news | live/fresh | 8 |

The Change Inbox itself used saved rows and made zero provider calls.

## Clean-Room Result

The deterministic audit covered all 28 supplied archives and 51,305 entries.
Benchmark and external material informed behavior only. No external code,
dataset, image, font, or trade dress was copied.

