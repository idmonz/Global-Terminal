# Phase 6H Synchronized Analyst Workspace Contract

Updated: 2026-07-03

## `analyst_workspace.v1`

The workspace manifest is a compact composition contract for one exact symbol.
It does not contain full chart history, financial rows, news bodies, or
duplicated source registers. One separately selected exact saved `chart-core`
envelope supplies useful first paint; runtime panels remain behind existing
exact panel delivery routes.

Top-level data includes:

- `identity`: exact symbol, normalized symbol, asset class, name, exchange, and
  compatibility state;
- `context`: synchronized interval, range, focused panel, layout preset, safe
  origin/return state, quote clock, market clock, and source clock;
- `quote`: compact same-symbol quote summary;
- `panels`: deterministic panel manifest and exact endpoint references;
- `layouts`: validated desktop/mobile presets and local persistence boundary;
- `change_context`: optional exact saved-change evidence;
- `actions`: verified internal research routes and safe external source links;
- `request_plan`: bounded delivery, provider-call, cache, and mobile-lazy truth;
- `readiness`, `evidence_refs`, and `not_financial_advice`.

## Panel Manifest

Required panel IDs are:

- `chart-core`
- `technicals`
- `financials`
- `catalysts`
- `news`
- `sources`
- `comparison`

Every panel entry declares:

- exact symbol and compatibility;
- delivery status and endpoint;
- cache/ETag identity;
- provider/source status, fetched/as-of clock, confidence, caveat, and data
  gap;
- desktop visibility and mobile lazy-delivery state;
- whether interval/range changes apply to that panel.

Missing is never converted to zero. An incompatible panel remains visible as an
explicit gap and never substitutes another symbol.

## Synchronization Rules

- Symbol changes create a new exact workspace contract and invalidate panel
  bodies from the prior symbol.
- Interval/range changes update chart-compatible panels only. Other panels keep
  the same exact symbol and state why the timeframe does not apply.
- One in-flight key is
  `(symbol, panel, interval, range, compare, delivery_version)`.
- Concurrent equal keys share one request.
- ETag `304` reuses the exact cached body.
- A failed refresh retains only a previously loaded body with the same identity
  key and labels the latest attempt separately as failed/stale.

## Change Inbox Mapping

| Change type | Focused panel |
|---|---|
| event or exact news | `catalysts` |
| fundamental | `financials` |
| price or performance | `chart-core` |
| source-status | `sources` |
| other | `chart-core` |

The return URL preserves list, type/severity/status filters, selected change,
layout, focused panel, symbol, interval/range, and origin after allowlist
validation.

## Layout And Privacy Boundary

Allowed local layout fields are preset, bounded split value, panel order,
visibility, focus, symbol, interval, range, and safe origin state. Storage keys
are versioned and symbol-independent where practical.

The contract and local state must reject:

- credentials, bearer tokens, provider response bodies, or secret-like values;
- private notes, local absolute paths, SQLite rows, or arbitrary URLs;
- broker/order actions, autonomous AI actions, or hosted synchronization
  claims.

## Delivery Plan

- Initial SSR: workspace manifest plus one exact saved `chart-core` envelope;
  duplicate `chart_specs` and unused capability rows are removed.
- Desktop: load `chart-core` plus at most three visible complementary panels.
- Mobile: load only the focused panel until explicit user action.
- Secondary panels reuse current exact delivery routes, TTL/LKG behavior, ETags,
  cache partitions, and provider budgets.
- No RSC route prefetch, broad watchlist refresh, or universe fan-out.
