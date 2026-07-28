# Phase 5L Persistence, API And Data Contract

Updated: 2026-06-22

## Persistence

Schema v4 adds:

- `research_memory_items`: normalized metadata, local-private body, origin ID, compatibility labels, links, tags and archive state;
- `research_source_history`: append-only provider/source/freshness/confidence/caveat/gap snapshots.

Existing migrations remain additive. Queries are parameterized, result limits are bounded to 100 and ordering is stable by timestamp then opaque ID.

## Domain Contract

`research_memory.v1` contains items, watchlists, report metadata, source history, origin registry, filters, export preview, readiness, privacy and summary. It uses only JSON primitives at the API boundary.

Comparison is allowed only when memory type, period and model labels match exactly. Missing labels produce an incompatible result rather than an inferred comparison.

## API Boundary

- `GET /api/research-memory`: demo or local metadata view; no private search query.
- `POST /api/research-memory/search`: private query in JSON body.
- `POST /api/research-memory/items`: explicit local save.
- `GET /api/research-memory/items/{opaque_id}`: local detail with explicit private flag.
- `DELETE /api/research-memory/items/{opaque_id}`: soft archive.
- `POST /api/research-memory/source-snapshots`: append-only source observation.
- `POST/DELETE /api/research-memory/watchlists`: existing watchlist store adapter.
- `POST /api/research-memory/export`: sanitized metadata by default.

Static fixtures always use deterministic fictional rows. Local-private bodies never enter fixture export.

## Export Boundary

Sanitized export omits title, private body, summary, linked symbols, watchlist symbols, holdings, attachments, account data and local paths. Full workspace export remains a separate explicit local operation under the existing private export directory and is excluded from release packaging.

