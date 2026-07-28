# Phase 5O API, Provider, And Persistence Contract

Updated: 2026-06-22

## Additive Payload

The existing `market_map_screener` envelope remains additive and gains:

- `discovery_version`;
- `factor_catalog`;
- `rank_models`;
- per-row `factors`, `rank_models`, `financial_snapshot`, `market_clock`, and `data_quality`;
- `filter_options.discovery`;
- `saved_screen_readiness`.

No DataFrame, datetime, Path, provider client, database handle, exception object, secret, or private path crosses the API boundary.

## Runtime Cache

History and batch financial snapshots use separate cache keys and statuses. Cache identity includes universe/version, period, factor version, provider mode, and request family. A current retrieval never converts an old market observation into a current quote claim.

## Saved Screens

Local-private SQLite schema v5 adds `saved_market_screens`.

Stored fields:

- opaque screen ID;
- validated local name;
- schema version;
- bounded public filter definition;
- rank and display mode;
- created and updated timestamps;
- archived state.

Required operations:

- list;
- create;
- load;
- rename;
- delete/archive.

The API returns local-private rows only when the local API is explicitly configured. Static fixtures contain fictional demo definitions only. Release archives exclude the SQLite database and private state.

## Failure Semantics

- batch history failure: stale cache or explicit unavailable;
- financial snapshot failure: technical rows remain usable with valuation fields null and a visible data gap;
- local store unavailable/corrupt: saved-screen controls show unavailable without changing the active public screen;
- invalid filters or names: HTTP 422 and no partial write;
- fixture mode: deterministic rows and fictional screen examples only.

## Security Boundary

All inputs are bounded enums, finite numeric buckets, allow-listed symbols, or length-limited names. SQL uses parameters. CORS remains local-only. Hosted auth, billing, cloud sync, broker actions, and external AI over private screen names are not added in this phase.

