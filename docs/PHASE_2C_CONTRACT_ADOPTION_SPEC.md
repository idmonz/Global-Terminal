# Phase 2C Contract Adoption Spec

Updated: 2026-06-16

## Goal

Phase 2C makes the Phase 2B API-ready payloads actively consumable by the current Streamlit lab, the optional FastAPI backend, static JSON fixtures, and a future web shell. This slice does not introduce a Node dependency, a paid provider dependency, or a real `apps/web` scaffold.

## Contract Boundary

All consumers use the same envelope produced by `lib/api_contracts.py`:

- `contract_version`
- `payload_type`
- `generated_at`
- `data`
- `summary`
- `source_status`
- `unavailable`
- `errors`
- `caveats`

The contract version remains `phase_2b.v1` in this slice. Phase 2C is an adoption layer, not a breaking contract revision.

## Consumers

| Consumer | Source of truth | Phase 2C behavior |
|---|---|---|
| Streamlit War Room | `build_api_war_room_payload()` and related contract builders | Shows compact contract summary and JSON-safe preview beside existing analyst UI. |
| Streamlit News | `build_api_news_dashboard_payload()` | Shows the same news payload future web clients will consume. |
| Streamlit Data Provider Center | feed registry, provider health, layer runtime, AI provider, and manifest builders | Shows backend/web route readiness without exposing internal objects. |
| Optional FastAPI | `backend/api/app.py` route getter functions | Keeps read-only routes import-safe when FastAPI is absent and smoke-testable when installed. |
| Static fixtures | `scripts/export_api_fixtures.py` | Exports deterministic, network-free JSON fixtures for web-shell development. |
| Future web shell | Static fixtures first, optional FastAPI later | Reads the same envelope shape and displays unavailable/error states honestly. |

## Rules

- Streamlit pages may render contract summaries, but business payload assembly stays in `lib/api_contracts.py` or existing `lib/` modules.
- Static fixtures are development fixtures, not claims of live market or OSINT coverage.
- Fixture export defaults to no live network calls and masks optional provider environment variables.
- API payloads must pass `validate_api_payload`.
- New fields must be additive and optional.
- No payload may leak raw DataFrames, raw datetimes, `DataResult` objects, Plotly figures, Streamlit objects, local private paths, or secrets.
- OpenSky remains unavailable unless OAuth credentials and `/states/all` fetch succeed.
- Gemini remains free-first; Google Search grounding remains opt-in.

## Fixture Set

`scripts/export_api_fixtures.py` writes these files to `static/api-fixtures/` by default:

- `feeds.json`
- `provider-health.json`
- `layers.json`
- `news.json`
- `war-room.json`
- `ai-providers.json`
- `manifest.json`

Each file is a complete contract envelope and is safe for a future `apps/web` shell to load directly during early UI development.

## Acceptance

- Existing Streamlit pages still import.
- Fixture export produces valid JSON without live network calls.
- Fixture files pass `validate_api_payload`.
- Optional FastAPI route getters are smoke-tested without requiring FastAPI.
- If FastAPI is installed, read-only route responses pass the same validation.
- Roadmap and next-prompt docs point past Phase 2B and into Phase 2D after this slice.
