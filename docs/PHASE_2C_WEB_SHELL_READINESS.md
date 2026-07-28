# Phase 2C Web Shell Readiness

Updated: 2026-06-16

## Goal

Prepare the future B2C web shell to consume Phase 2B API contracts without requiring Node, npm, Next.js scaffolding, paid APIs, or live providers in this slice.

## Deferred Scaffold

There is no first-party `apps/web` project yet, and this environment does not currently provide Node/npm. Real Next.js setup is deferred until those tools are available. Phase 2C therefore ships static fixtures and a route/component contract that a future React app can adopt.

## Route To Fixture Map

| Future web route | FastAPI route | Static fixture | First shell panels |
|---|---|---|---|
| `/` | `GET /api` plus selected summary routes | `manifest.json` | Route manifest, backend readiness, provider strip. |
| `/war-room` | `GET /api/war-room?include_runtime=false` | `war-room.json` | Risk header, event list, map summary, data gaps, layer status. |
| `/news` | `GET /api/news?include_runtime=false` | `news.json` | Command feed, high-severity feed, source freshness, impact matrix. |
| `/providers` | `GET /api/provider-health` | `provider-health.json` | Health ledger, blocked providers, recommended actions. |
| `/layers` | `GET /api/layers?include_runtime=false` | `layers.json` | Layer table, unavailable layers, row counts, caveats. |
| `/feeds` | `GET /api/feeds` | `feeds.json` | Feed taxonomy, default-enabled feeds, optional keyed feeds. |
| `/ai` | `GET /api/ai-providers` | `ai-providers.json` | Free-first AI readiness, selected provider, grounding flag. |

## Expected Shell Layout

The first web shell should be a product surface, not a marketing page:

- Top command bar with route search and active data mode.
- Left workspace rail for War Room, News, Providers, Layers, Feeds, and AI.
- Central work panel that renders one contract payload at a time.
- Right intelligence rail for caveats, unavailable rows, and source freshness.
- Bottom provider strip that stays visible across routes.

## Fixture Consumption Rules

- Treat fixtures as immutable examples of the API envelope.
- Do not infer live coverage from fixture rows.
- If a payload has `unavailable` rows, render them as visible gaps.
- If a payload has `errors`, render them as recoverable status, not as a broken UI.
- Prefer additive UI fields over assuming hidden internal Python data.
- Do not parse or render raw DataFrames, Plotly figures, Streamlit state, local file paths, or secrets.

## Phase 2D Entry Criteria

Start the real web shell only when Node/npm are available and the team accepts a first-party `apps/web` scaffold. Phase 2D should wire the static fixtures into the initial shell first, then switch selected views to optional FastAPI routes while keeping the fixture fallback.

Recommended Phase 2D first tasks:

1. Create `apps/web` with Next.js, React, TypeScript, and fixture-based route loaders.
2. Add contract TypeScript types generated or hand-written from `phase_2b.v1`.
3. Build War Room, News, Provider Health, and Route Manifest shells from `static/api-fixtures/`.
4. Add one smoke test that loads every fixture and validates the common envelope shape.
