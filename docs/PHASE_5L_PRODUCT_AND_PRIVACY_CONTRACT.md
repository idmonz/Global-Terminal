# Phase 5L Product And Privacy Contract

Updated: 2026-06-22

## Daily Workflow

The Research Memory workspace supports five linked surfaces: Inbox, Watchlists, Notes, Reports and Sources. A user can save local research, locate it with bounded private search, inspect immutable provenance, verify period/model compatibility, return to an originating workstation and preview a sanitized export.

Canonical route:

`/?view=research-memory&collection=demo-research&surface=inbox&mode=demo`

Allowed URL state is limited to opaque collection/origin IDs and non-private enum filters. Private note text and private search terms use request bodies or client state.

## Privacy Classes

| Class | Allowed location | Forbidden location |
|---|---|---|
| fictional demo | static fixture, tests, release screenshots | live claims |
| local-private | SQLite below `data/private`, local API/browser session | fixtures, source control, logs, screenshots, telemetry, external AI, ZIP |
| sanitized metadata | explicit export preview | note title/body, symbols/watchlist, holdings, attachments, account IDs, local paths |

External AI, cloud sync, hosted auth, notification delivery, broker actions and autonomous monitoring are unavailable in this phase.

## Failure States

First-run/empty is useful and writable. Old schema migrates additively. Corrupt or inaccessible SQLite returns `corrupt-or-unavailable`. Missing origins remain visible without fabricating a link. Stale provider rows remain stale. Demo state is always labeled fictional fixture.

## Advice Boundary

Research Memory stores and retrieves user research records. It does not generate recommendations, approve trades, size positions, connect brokers or place orders.

