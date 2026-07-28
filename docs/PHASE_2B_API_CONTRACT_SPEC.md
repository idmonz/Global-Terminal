# Phase 2B API Contract Spec

Updated: 2026-06-16

## Objective

Phase 2B adds stable, JSON-safe contracts around the existing Phase 1 and Phase 2A source-backed runtime. Streamlit remains the active UI. The new contract boundary lets a future FastAPI backend or Next.js frontend consume the same Python runtime without accepting internal objects such as pandas DataFrames, Plotly figures, local paths, exception objects, or secret values.

## Contract Rules

- Every response is a dictionary envelope with `contract_version`, `payload_type`, `generated_at`, `data`, `summary`, `source_status`, `unavailable`, `errors`, and `caveats`.
- The current contract version is `phase_2b.v1`.
- Payload fields use existing project snake_case naming to preserve Python runtime compatibility.
- Datetimes are serialized to ISO strings.
- DataFrames and Series are serialized to record lists or dictionaries.
- `DataResult` objects are serialized through their public `to_dict()` status fields.
- Secret-like fields such as `api_key`, `client_secret`, `access_token`, `authorization`, `password`, `secret`, and `token` are redacted if encountered. Environment variable names such as `GEMINI_API_KEY` are allowed because they are labels, not values.
- Payloads may add optional fields later, but existing field meaning should not be changed.
- Missing paid or optional providers must appear as `missing-key`, `unavailable`, `forbidden/subscription-blocked`, or equivalent explicit gap states.
- A row that claims `live/fresh` must include `fetched_at`, `latest_fetched_at`, or response-level `generated_at` metadata.

## Payload Families

### Feed Registry

Builder: `build_api_feed_registry_payload()`

Purpose: expose curated feed metadata from `lib/feed_registry.py` without making network calls.

Required row fields follow `FEED_REGISTRY_SCHEMA`: `feed_id`, `label`, `provider`, `category`, `region`, `source_url`, `source_type`, `tier`, `default_enabled`, `requires_key`, `cadence_seconds`, `credibility`, `source_risk`, `tags`, and `caveat`.

Unavailable rows include optional or disabled feeds such as AIS, OpenSky, and registry-only sanctions.

### Provider Health

Builder: `build_api_provider_health_payload(results=None, ledger=None)`

Purpose: expose the provider health ledger from `lib/provider_health_engine.py`.

Status values include `live/fresh`, `cached`, `stale`, `rate-limited`, `forbidden/subscription-blocked`, `missing-key`, `unavailable`, and `proxy/static`.

Rows include provider/source identity, row count, fetched timestamp when known, cache/freshness fields, warnings, errors, caveats, and recommended action.

### Layer Runtime

Builder: `build_api_layer_runtime_payload(runtime_feeds=None, statuses=None, layers=None, layer_payload=None)`

Purpose: expose map-layer runtime state from `lib/layer_registry.py`.

Rows include layer identity, domain, source/provider, availability, row count, latest fetched timestamp, freshness/source status, key requirements, caveat, and recommended action.

Unavailable optional layers such as AIS, sanctions, and failed OpenSky remain visible as explicit gaps.

### News Dashboard

Builder: `build_api_news_dashboard_payload(items=None, statuses=None, dashboard=None, max_rows=100)`

Purpose: expose the WorldMonitor-style public news dashboard without leaking DataFrames.

Data sections include `normalized_news`, `high_severity_feed`, `timeline`, `impact_matrix`, `regional_cards`, `source_freshness`, `event_rows`, `risk_catalysts`, and `notes`.

News classification remains deterministic and heuristic. Public feeds can be delayed, duplicated, stale, or missing precise coordinates.

### War Room

Builder: `build_api_war_room_payload(state=None, include_default_runtime=False, max_events=100)`

Purpose: expose War Room summary state without Streamlit, Plotly, or DataFrame objects.

Data sections include `header_metrics`, `events`, `event_timeline`, `map_summary`, `layer_runtime_status`, `provider_health_ledger`, `market_impact_summary`, `macro_energy_payload`, `runtime_feeds`, `ai_context`, and `data_gaps`.

`include_default_runtime` defaults to `False` so tests and local route imports do not start network fetches. A caller can opt into keyless runtime fetches.

### AI Provider Status

Builder: `build_api_ai_provider_payload(preferred="auto")`

Purpose: expose free-first AI/provider readiness without exposing keys or making model calls.

The free-first order is Gemini, Groq, Ollama, OpenRouter, Anthropic, then rule-based fallback. `OPENAI_API_KEY` is not required.

Gemini defaults to `gemini-3.1-flash-lite` when configured. `GEMINI_ENABLE_GOOGLE_SEARCH` remains opt-in and is surfaced as a boolean because search grounding may create billable tool usage.

## Optional Backend

FastAPI is optional and not part of base `requirements.txt`.

Optional install:

```bash
python -m pip install -r requirements-api.txt
```

Run locally:

```bash
uvicorn backend.api.app:app --reload
```

Read-only candidate routes:

- `GET /api`
- `GET /api/feeds`
- `GET /api/provider-health`
- `GET /api/layers`
- `GET /api/news`
- `GET /api/war-room`
- `GET /api/ai-providers`

Routes that can fetch public runtime data expose `include_runtime=false` by default. Set `include_runtime=true` only when live keyless fetches are desired.

## Validation

Use `validate_api_payload(payload)` from `lib/api_contracts.py` in tests and future route checks. Validation confirms JSON serialization, rejects DataFrame/DataResult leakage, redacts secret-like fields, and checks live/fresh timestamp metadata.

Focused test:

```bash
python -m pytest tests/test_api_contracts.py -q
```

Full Phase 2B verification should also include the Phase 1/2A, OpenSky, and Gemini test slices named in `docs/NEXT_ROADMAP_EXECUTION_PROMPT.md`.
