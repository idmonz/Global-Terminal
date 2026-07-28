# Phase 5P Snapshot And Replay Contract

Updated: 2026-06-22

## User Journey

`War Map -> capture current observation -> capture/read another observation -> choose active and comparison times -> inspect added/removed/changed events, layers, providers, news and assets -> open evidence -> return with bounded URL state`

## Historical Truth

- A historical row is shown only when it was captured by this project or belongs to the clearly fictional deterministic demo fixture.
- Capture time, provider fetch time, event occurrence time, market observation time and retrieval time remain separate.
- The product does not synthesize past states from current rows.
- Missing records remain missing and do not imply resolution, causality or market impact.

## Snapshot Shape

Each schema-versioned snapshot stores bounded normalized collections:

- markers;
- layer health;
- provider health;
- linked news;
- connected asset context;
- source register;
- provider/layer summaries;
- capture/runtime/retention metadata;
- a deterministic content hash.

Secrets, clients, exceptions, browser state, paths, arbitrary binaries and raw provider payloads are prohibited.

## Persistence

- SQLite local-private scope;
- append-only rows;
- deterministic hash deduplication;
- bounded record and text limits;
- configurable retention metadata and explicit pruning only;
- empty local first run;
- fixture/demo snapshots are fictional and never written to the local store by fixture export;
- local database and snapshot contents are excluded from releases.

## Diff Semantics

- `added`: stable identity exists only in the active snapshot;
- `removed`: stable identity exists only in the comparison snapshot;
- `changed`: stable identity exists in both and source-preserving material fields differ;
- `unchanged`: identity and compared material fields match.

The diff preserves both before and after evidence. It covers events, layers, providers, news and assets. Approximate graph relationships remain inferred/proxy.

## Failure States

- empty store: useful capture prompt, no invented history;
- duplicate capture: return the existing snapshot ID with `deduplicated=true`;
- missing snapshot: 404/API-safe unavailable state;
- stale/cache capture: persisted with its original source status;
- unavailable AIS, flight and sanctions: remain unavailable in snapshots and diffs;
- storage failure: explicit local-persistence error, never a fake success.

## URL Contract

Only bounded allow-listed values may appear:

`view`, `mode`, `layers`, `time`, `compareTo`, `selected`, `severity`, `region`, `mapMode`.

Snapshot content, source URLs, private notes, local paths, raw provider payloads and credentials never enter the URL.

## Non-Advisory Boundary

Replay is a research and provenance surface. It does not produce forecasts, recommendations, target prices, broker actions, order routing or autonomous monitoring.
