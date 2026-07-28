# Phase 5P API, Provider And Persistence Contract

Updated: 2026-06-22

## API

The existing `phase_2b.v1` envelope is extended additively with:

- `GET /api/war-room-map-snapshots`;
- `POST /api/war-room-map-snapshots`;
- `GET /api/war-room-map-replay?time=<id>&compareTo=<id>`.

The capture endpoint accepts only bounded runtime mode and normalized current map-fusion data built server-side. It does not accept arbitrary snapshot JSON from the browser.

## Provider Boundary

Snapshot capture preserves each row's provider, source URL, fetched time, freshness/source status, confidence, coordinate method, caveat and data gap. A capture does not upgrade cache, stale, fixture, proxy or unavailable data to live.

OpenSky, AIS and sanctions remain unavailable until successful provider evidence exists. Paid providers are not introduced.

## Database

SQLite schema version 6 adds one append-only map snapshot table and indexes for capture ordering, content deduplication and retention. Read APIs return sanitized JSON values and never expose the database path or connection.

## Security And Privacy

- payloads are bounded before hashing and storage;
- URL and ID validators reject arbitrary strings;
- no `.env` value is serialized or logged;
- local snapshot content is excluded from deterministic fixtures and release ZIPs;
- CORS remains restricted to loopback product origins on ports `3000-3999`;
- no hosted synchronization, tenant identity or cloud backup is implied.

## Deterministic Fixture

The fixture exporter may publish a fictional replay fixture with explicit `fixture` and `fictional-demo` labels. It must not read the user's local snapshot database.
