# Phase 3 Command Workspace Spec

Updated: 2026-06-17

Phase 3 implements a clean-room command workspace and terminal-actions contract for the Global Macro + Equity + Crypto + Commodity + Geopolitical Risk Terminal.

The workspace turns Phase 2F event-to-asset graph `command_suggestions` into source-backed, provider-gated workstation actions. It does not add market-action execution, auth, billing, hosted persistence, graph databases, paid provider dependencies, or user accounts.

## Delivered Surface

- Python contract builder: `lib/command_workspace.py`
- API envelope builder: `build_api_command_workspace_payload()`
- Optional backend getter/route: `get_command_workspace_payload()` and `GET /api/command-workspace`
- Static fixture: `static/api-fixtures/command-workspace.json`
- Web workstation view: `/?view=command-workspace`
- Focused tests: `tests/test_command_workspace_contracts.py`
- Web fixture validator coverage: `apps/web/scripts/validate-fixtures.mjs`

The payload remains additive under `API_CONTRACT_VERSION = "phase_2b.v1"` with payload type `command_workspace`.

## Contract Shape

The command workspace data object contains:

- `command_workspace_version`: currently `command_workspace.v1`
- `commands`: clean-room command definitions and routing metadata
- `contexts`: active event, asset, region, provider, and graph contexts seeded from Phase 2F
- `command_results`: provider-gated result previews and action contracts
- `history_seed`: deterministic fixture-safe command history examples
- `provider_requirements`: command-to-provider status matrix
- `readiness`: unavailable execution, order-routing, persistence, auth, billing, graph database, and paid-provider capabilities
- `evidence_refs`: Phase 3 and Phase 2F evidence references used as behavior/product sources
- `summary`: compact counts and truth-policy flags

Command records include:

- `command`
- `label`
- `description`
- `accepted_context_types`
- `provider`
- `provider_family`
- `source_status`
- `freshness`
- `fetched_at`
- `implementation_status`
- `requires_provider`
- `result_status`
- `route`
- `workspace_view`
- `caveat`
- `data_gap`
- `not_financial_advice`

Command result records include:

- `available`
- `result_status`
- `provider_requirement`
- `preview`
- `action_contract`
- `allowed_actions`
- `caveat`
- `data_gap`
- `not_financial_advice`

## Command Set

Phase 3 supports these first clean-room command records:

- `NI`: News Intelligence
- `MAP`: War Room Map
- `DES`: Description
- `FA`: Fundamental Analysis
- `GP`: Graph / Price
- `HP`: Historical Price
- `WEI`: Weights / Exposure
- `CURV`: Rates Curve
- `FXC`: FX Crosses
- `CRYPTO`: Crypto Market

## Provider Gating

Provider-required commands are marked available only when matching provider evidence is `live/fresh` or `cached`.

Fixture/static/proxy rows can seed context and previews, but they do not become live command results. In deterministic fixture mode:

- `NI` is `source-backed-preview` because it can inspect fixture event context but does not claim live news.
- `MAP` is `proxy/static` because static/proxy map context is available but live layers are not claimed.
- `DES`, `FA`, `GP`, `HP`, `WEI`, `CURV`, `FXC`, and `CRYPTO` remain unavailable, missing-key, or provider-required until provider evidence is fresh or cached.

Every unavailable result includes the missing provider family, recommended action, caveat, and data gap.

## Safety And Compliance

Phase 3 actions are read-only workstation routes.

Unavailable in this slice:

- `broker_execution`
- `order_routing`
- `hosted_persistence`
- auth
- billing
- graph databases
- paid provider dependencies
- user-specific command state

The command workspace does not produce buy/sell/hold advice, trade approvals, order placement, autonomous market actions, or model-driven directional instructions.

## Evidence And License Boundary

Phase 3 reuses the Phase 2E/2F external audit artifacts rather than re-running archive scans.

Evidence refs included in the payload:

- BB-Terminal: command bar/workstation behavior reference only; direct copying remains blocked.
- OpenBB: provider command-contract mental model only; AGPL source is not copied or vendored.
- WorldMonitor: source/provenance/status/caveat discipline only; AGPL source is not copied.
- Supabase: future persistence/readiness reference only; no hosted dependency is added.
- FinanceDatabase: schema/taxonomy behavior from Phase 2E; external CSV rows are not copied.
- Phase 2F graph evidence refs are preserved for graph-seeded contexts.

## Web Workstation View

The Next.js workstation adds `command-workspace` to fixture definitions.

The view renders:

- Command tape
- Graph-seeded active context
- Unavailable action boundary
- Provider gate matrix
- Result preview cards
- Existing caveat/source rail

The implementation follows the current App Router server-rendered fixture pattern. The project uses Next 16.2.9 and React 19.2.4; the page continues to use the async `searchParams` Page prop and `next/link` navigation pattern documented by Next.js.

## Verification

Implemented test and build coverage:

- `python -m pytest tests/test_command_workspace_contracts.py -q`
- `python -m pytest tests/test_command_workspace_contracts.py tests/test_event_asset_graph_contracts.py tests/test_api_fixture_export.py tests/test_api_backend_routes.py tests/test_api_contracts.py -q`
- `python scripts/export_api_fixtures.py`
- `npm --prefix apps/web test`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/web run build`
- `npm --prefix apps/web audit --audit-level=high`
- `python -m pytest -q`

Visual verification note:

- In-app browser tooling was unavailable in the implementation session.
- Local Playwright was not installed.
- HTTP render-marker fallback checks passed for `/`, `/?view=command-workspace`, `/?view=event-graph`, `/?view=war-room`, `/?view=asset-universe`, and `/?view=provider-health`.

## Remaining Gaps

- Command state is fixture-safe only; user-specific saved tabs, layouts, and history require a later persistence/auth slice.
- Provider-required commands do not call live providers inside the fixture builder. They become available only when upstream provider health evidence says fresh or cached.
- No market-action workflow is present.
- Map-first interaction depth belongs to Phase 4.
