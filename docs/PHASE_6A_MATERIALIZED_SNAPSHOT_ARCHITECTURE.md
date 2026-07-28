# Phase 6A Materialized Snapshot Architecture

Updated: 2026-07-01

## Runtime Path

```text
refresh_market_snapshot.py
-> bounded Phase 5Z composition
-> compact JSON envelope
-> atomic versioned snapshot + latest manifest
-> last-known-good read
-> ETag/Cache-Control API
-> Next.js Market Map
```

The successful web read does not rebuild the universe or call providers.

## Storage Contract

- module: `lib/market_snapshot_store.py`;
- version: `market_snapshot.v1`;
- local root: `data/cache/market_snapshots` by default;
- writes: temporary file plus atomic `os.replace`;
- identity: SHA-256 content hash;
- retention: bounded and deterministic;
- concurrency: process lock plus file single-flight lock;
- failure: prior snapshot remains readable and health becomes `failed`;
- validation: version, manifest name, content hash, JSON shape, secrets, private
  fields, and local paths.

## Read Contract

- `GET /api/market-map-snapshot`;
- `GET /api/market-map-snapshot/{symbol}`;
- `GET /api/market-refresh-health`;
- ETag conditional reads return 304;
- cache policy: `max-age=30, stale-while-revalidate=300`;
- fresh/stale is derived at read time;
- detail lookup is exact-symbol only;
- unknown symbols cannot receive another symbol's fixture identity.

## Observed 2026-07-01

- refresh: 6,517 ms;
- instruments: 137;
- observed provider calls: 2 across 5 provider sources;
- compact response: 746,784 bytes;
- previous response: approximately 1,868,494 bytes;
- warm curl HTTP read p50: approximately 57 ms over seven samples;
- ETag conditional response: 304.

No scheduler, queue, Redis, Supabase, or cloud service is claimed.

