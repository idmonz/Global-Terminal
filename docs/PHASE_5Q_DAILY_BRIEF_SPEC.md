# Phase 5Q Daily Brief Specification

Updated: 2026-06-23

## Outcome

Phase 5Q turns the existing source-aware runtime into a daily research workflow:

`Market Home -> Daily Brief -> claim ledger -> source drawer -> local capture/review -> return`.

The route is `/?view=daily-brief`. The API boundary is additive under the existing `phase_2b.v1` envelope:

- `GET /api/daily-brief`
- `GET /api/daily-brief/captures`
- `POST /api/daily-brief/captures`
- `PATCH /api/daily-brief/captures/{brief_id}/review`

## Contract

`lib/daily_briefing.py` owns the native contract:

- `daily_brief_version`: `daily_brief.v1`
- `period`: `morning`, `midday`, `close`, or `weekly`
- `runtime_mode`: `fixture`, `cache`, `live-if-available`, or `local`
- `headline`
- `claims`
- `sections`
- `source_register`
- `coverage`
- `comparison`
- `review`
- `ai`
- `caveat`
- `not_financial_advice`

Every material claim carries:

- `claim_id`
- `claim_kind`
- `section_id`
- `statement`
- `source_ids`
- `provider`
- `source_status`
- `freshness`
- `fetched_at`
- `observed_at`
- `confidence`
- `severity`
- linked symbols, regions and events
- `caveat`
- `data_gap`
- `privacy_scope`
- `not_financial_advice`

## Source Truth

The brief composes from current first-party contracts only:

- market intelligence;
- War Room map state;
- WorldMonitor-style news dashboard rows;
- provider health and optional source status rows;
- local Research Memory watchlist context.

Missing, stale, proxy, rate-limited, missing-key, unavailable, and configured-but-unverified rows become explicit gap claims. As of this spec, configured OpenSky/AIS credentials are not treated as live until the corresponding provider has supplied verified rows for the brief.

## Persistence

SQLite schema v7 adds `daily_brief_captures` as a local-private append-only table. Capture rows include:

- `brief_id`
- `capture_version`
- `content_hash`
- `period`
- generated and captured timestamps
- observation window
- runtime mode
- source status
- retention metadata
- review status and reviewed time
- claim, section, source-register and coverage JSON
- comparison JSON
- linked symbols and regions

Identical normalized content deduplicates even when only volatile fetch clocks change.

## AI Boundary

The deterministic rule-based brief is the default product. Optional Gemini drafting may only receive the public-sanitized claim/source subset. It must not receive local notes, watchlist reasons, holdings, account data, private paths, credentials, raw provider payloads or SQLite content. Any AI draft is untrusted and must pass claim-ID, source-coverage and no-advice validation before display or storage.

## Non-Goals

Phase 5Q does not add:

- investment advice or target prices;
- broker actions;
- alert delivery;
- email or push scheduling;
- hosted sync;
- multi-user tenancy;
- production auth or billing;
- automatic Google Search grounding;
- live OpenSky/AIS rows without a successful provider fetch.

Outputs are research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, autonomous monitoring or execution instructions.
