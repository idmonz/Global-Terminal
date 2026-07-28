# Phase 6D Watchlist And Materialization Contract

Updated: 2026-07-02

## Public Contract

`watchlist_desk.v1` is JSON-safe and contains:

- `collections`, `active_list`, ordered public `items`, and `selected`;
- row identity, quote/change, source/freshness, capability, and refresh state;
- latest materialization job, limits, readiness, privacy declarations, and caveat;
- no `watch_reason`, secret, local path, AI context, or execution instruction.

The deterministic fixture contains AAPL, TSLA, JNJ, TTE, and TMUS identity
metadata but no current quote. It is explicitly `fictional-demo`/`fixture`.

## Persistence

Workspace schema v8 adds:

- `watchlist_collections`;
- list and stable position fields on `watchlist_items`;
- `watchlist_materialization_jobs`.

The migration is additive. Existing flat watchlist rows remain readable. Local
private reasons are accepted only as write input and never returned by the desk.

## Materialization Limits

- explicit user action only;
- maximum 8 symbols per job;
- list maximum 50 symbols and 20 lists;
- one batched history provider call where supported;
- metadata declares maximum concurrency 2;
- overlapping same-list jobs are rejected;
- interval/range/cache keys remain symbol scoped;
- no broad-universe rebuild and no installed background service claim.

## Routes

- `GET /api/watchlist-desk`
- `POST /api/watchlist-desk/lists`
- `PATCH|DELETE /api/watchlist-desk/lists/{list_id}`
- `POST /api/watchlist-desk/lists/{list_id}/items`
- `PATCH /api/watchlist-desk/lists/{list_id}/order`
- `DELETE /api/watchlist-desk/lists/{list_id}/items/{item_id}`
- `POST /api/watchlist-desk/lists/{list_id}/materialize`
- `GET /api/symbol-workstation/{symbol}/summary`
- `GET /api/symbol-workstation/{symbol}/panels/{panel}`

Unknown or asset-class-mismatched identities never fall back to AAPL or another
symbol. Duplicate items return conflict; invalid exact identities return a
client error; provider failure retains same-symbol cache or an explicit gap.

