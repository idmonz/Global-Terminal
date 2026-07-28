# Phase 5F Web Terminal Product Blueprint

Updated: 2026-06-19

## Product Promise

Global Terminal is a commercial, source-transparent market intelligence workstation for individual investors and serious researchers. It connects global markets, equities, crypto, options, macro, commodities, news, and geopolitical events without pretending that unavailable or proxy data is live.

## Product Roles

- **Streamlit**: internal lab, rapid model validation, provider diagnostics, and regression reference.
- **`lib/`**: reusable provider, normalization, scoring, quantitative, report, and contract engines.
- **FastAPI boundary**: optional local backend now; deployable API service later.
- **Next.js web**: final B2C experience.
- **Fixtures**: deterministic development and failure fallback, never the commercial default claim.

## Canonical Information Architecture

| Route | User job | Primary objects |
|---|---|---|
| `/` | Understand what changed today | market tape, heatmap, events, news, watchlist |
| `/map` | Explore global events spatially | map, layers, timeline, news, assets |
| `/asset/[symbol]` | Research an equity/ETF/index | quote, chart, fundamentals, filings, news, scenarios |
| `/crypto/[symbol]` | Research a crypto asset | spot, derivatives, on-chain, scenarios, news |
| `/options/[symbol]` | Inspect option risk | chain, IV, Greeks, surface, quality, scenarios |
| `/screener` | Discover and compare assets | filters, ranked table, heatmap, scatter |
| `/portfolio` | Understand portfolio exposure | holdings, performance, risk, attribution, stress |
| `/war-room` | Monitor geopolitical/commodity risk | map, event tape, linked assets, source health |
| `/reports` | Read and manage research | inbox, report reader, sources, notes, exports |
| `/terminal` | Navigate quickly by command | command palette, context, read-only results |

## Core User Journeys

### Daily Open

1. Open Home.
2. See live/cached market status and last update.
3. Scan heatmap, top events, watchlist, and important news.
4. Open an asset or map event.
5. Save a source-linked note or report.

### Symbol Research

1. Search or click a symbol.
2. URL and global context update.
3. Price/volume chart renders first.
4. Fundamentals, news, related events, and provider gaps load progressively.
5. User changes timeframe without losing context.
6. Research report captures exact source timestamps and caveats.

### Event Research

1. Select a map marker or event tape row.
2. Map, news, timeline, and asset graph synchronize.
3. The user inspects sources and confidence.
4. Related assets open in the same workspace context.

## Runtime Architecture

```text
public/free providers
  -> provider adapters
  -> timeout/cache/single-flight/stale fallback
  -> normalized domain rows
  -> scoring and research calculations
  -> JSON-safe contract envelopes
  -> API service
  -> Next.js server/client components
```

Runtime modes:

- `live`: successful provider fetch with timestamp and source URL.
- `cached`: valid cache used within policy.
- `stale`: expired cache used after provider failure, visibly labeled.
- `fixture`: deterministic development/demo row.
- `proxy/static`: approximation or reference row.
- `unavailable`: no usable data.
- `provider-required`: provider/key/package must be configured.
- `error/rate-limited/forbidden`: explicit operational states.

## Canonical Schemas

### Provenance

Required fields: `provider`, `source`, `source_url`, `fetched_at`, `freshness`, `source_status`, `confidence`, `caveat`, `data_gap`, `license_stance`, `not_financial_advice`.

### Chart Spec

Required fields: `chart_id`, `symbol`, `series`, `interval`, `timezone`, `chart_type`, `units`, `events`, `provider`, `source_status`, `freshness`, `data_gap`.

### Heatmap

Required fields: `universe`, `group`, `symbol`, `size_metric`, `size_value`, `color_metric`, `color_value`, `label`, `provider`, `source_status`, `as_of`.

### Map Layer And Marker

Required fields: `layer_id`, `marker_id`, `latitude`, `longitude`, `coordinate_method`, `event_time`, `severity`, `provider`, `source_url`, `source_status`, `confidence`, `linked_assets`, `caveat`.

### Research Report

Required fields: `report_id`, `subject`, `as_of`, `sections`, `source_register`, `calculation_register`, `assumptions`, `data_gaps`, `confidence`, `disclosure`.

### Provider Health

Required fields: `provider`, `capability`, `status`, `last_success`, `last_attempt`, `latency_ms`, `row_count`, `cache_age`, `error_class`, `recommended_action`.

### Command Result

Required fields: `command`, `context`, `result_type`, `rows`, `provider_requirements`, `source_status`, `data_gap`, `read_only`, `not_financial_advice`.

## Commercial Architecture

### Initial Release

- Next.js web service.
- Python API service.
- Redis-compatible cache optional after local cache proof.
- PostgreSQL/Supabase-compatible persistence only for user state and research artifacts.
- object storage for exports and user attachments.
- background jobs for scheduled refresh and alerts.

### Entitlements

- Free: delayed/keyless data, limited watchlists, local reports.
- Plus: more saved workspaces, alerts, longer research history.
- Pro: premium provider connectors supplied by the user or licensed by the service.

No tier changes the provenance or safety rules.

## Success Metrics

- time to first useful market object under 2 seconds from cache;
- chart/map nonblank render rate above 99.5%;
- provider status visible within two interactions;
- symbol-to-report workflow completion;
- day-7 return rate and weekly active researchers;
- zero secret/private-path leakage and zero fake-live claims.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
