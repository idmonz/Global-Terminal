# Phase 5P Web Implementation Report

Updated: 2026-06-22

## Delivered Journey

`War Map -> capture observed state -> navigate snapshot density -> choose comparison -> inspect event/layer/provider/news/asset changes -> inspect selected source truth`

## Runtime And Persistence

- SQLite schema v6 adds append-only, content-addressed `war_room_map_snapshots`.
- Capture stores bounded normalized markers, layers, providers, news, assets and source register rows.
- Identical normalized input deduplicates to the existing snapshot ID.
- Retention is explicit and bounded from 1 to 365 days; pruning is an explicit operation.
- Historical mode reads only project-captured observations. The public fixture is separately labeled fictional.
- Material diffs ignore fetch-clock-only updates while still preserving the before/after clocks and reporting refresh counts.

## API

- `GET /api/war-room-map-snapshots`
- `POST /api/war-room-map-snapshots`
- `GET /api/war-room-map-replay?time=<id>&compareTo=<id>`

The POST route builds the current map-fusion payload server-side and accepts only bounded mode/retention controls. Arbitrary client snapshot JSON is rejected by design.

## Web Product

- observation density timeline;
- active, comparison and truth clocks;
- local capture and dedupe result state;
- five-domain change strip;
- added/changed/removed marker overlays;
- source-preserving selected event inspector;
- compact tablet/mobile flow and map fallback;
- bounded `time`, `compareTo`, `selected`, `layers`, `severity`, `region`, `mode` and `mapMode` URL state.

AIS, flight, sanctions, hosted sync, auth, billing, alert delivery and broker execution remain unavailable.
