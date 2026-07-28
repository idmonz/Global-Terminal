# Phase 5E Product System Blueprint

Updated: 2026-06-19

This document is the corrective product blueprint after the user reviewed the current web shell and called out the real gap: the design direction is acceptable, but the product still lacks the visible depth of the existing Streamlit lab, WorldMonitor/worldview map interaction, TradingView-like charting, Bloomberg-like command density, and source-backed daily research value.

## 1. Current Diagnosis

The user's criticism is correct.

What has been built:

- Streamlit remains the internal lab.
- `lib/` contains many useful engines and JSON-safe contract builders.
- `apps/web` is a working Next.js workstation shell.
- 16 `phase_2b.v1` fixtures validate.
- Runtime mode UI exists: `fixture`, `cache`, `live-if-available`.
- Optional runtime API loader exists, but the current local web server was not running at `127.0.0.1:3000` during this diagnosis.
- Leaflet War Map exists and is better than the previous schematic map, but it is still not a WorldMonitor/worldview-level intelligence map.
- Native SVG chart fallback exists, but it is not yet a TradingView/Koyfin-grade finance charting surface.
- A source-bound `research-report` v1 exists, but it is still mostly deterministic fixture/source-register based.

What is still insufficient:

- The web app can still feel like a contract/fixture gallery because most panels are not runtime-backed by default.
- Market, equity, and crypto views show useful structure but not enough real live/cache source-backed analysis.
- Financials and options still do not have dedicated deep product workspaces.
- Screener and portfolio quant are still missing from the web product.
- Map markers, news, timeline, layers, and asset relationships are not yet integrated into a single WorldMonitor-style map desk.
- The command bar routes views but is not yet a Bloomberg-like command workflow over active symbols, context, charts, reports, and history.
- The current report generator is non-advisory and source-safe, but it has not yet become a daily report engine over real market/news/map/provider rows.

Conclusion:

The project is moving toward the intended B2C terminal, but it is not there yet. The next phase must stop adding preview panels and instead build a product operating system: runtime-backed data, credible chart/map renderers, dedicated financial workspaces, and source-bound research workflows.

## 2. External Reference Coverage

The refreshed external archive audit remains the evidence base:

- Archives scanned: 18.
- Zip entries indexed: 32,428.
- Non-vendored text/code files line-indexed: 21,837.
- Indexed non-vendored text/code lines: 4,466,238.
- Feature evidence cards: 24.

License/action boundary:

| Source | License stance | Action |
|---|---|---|
| `agent-skills-main.zip` | MIT / direct-use-allowed | Use methodology directly: spec, plan, build, test, verify, review, ship. |
| `FinanceDatabase-main.zip` | MIT / direct-use-allowed | Use schema/taxonomy ideas; avoid copying large CSV rows into fixtures by default. |
| `osiris-master.zip` | MIT / direct-use-allowed | Use OSINT/provider workflow ideas; prefer native Python/TS implementation. |
| `optlib-master.zip` | MIT / direct-use-allowed | Use option-pricing references only after attribution/review. |
| `supabase-master.zip` | Apache-2.0 / direct-use-allowed | Use future persistence/status/admin patterns; no hosted auth yet. |
| `worldmonitor-main.zip` | AGPL / behavior-only | Recreate map/news/provider-health behavior clean-room. |
| `OpenBB-develop.zip` | AGPL / behavior-only | Recreate provider registry/finance hierarchy behavior clean-room or use optional installed package separately. |
| `OpenAlice/OpenStock` | AGPL / behavior-only | No source copy. Use only broad workflow ideas. |
| `worldview-main.zip` | NASA-1.3 / behavior-only | Recreate timeline/compare/layer interaction patterns clean-room. |
| `BB-Terminal-main.zip` | missing license / blocked | Recreate command grammar and dense UX clean-room only. |
| `bloomberg-terminal-main.zip`, `dexter-main.zip` | README-only MIT / needs-review | Concept-only unless full license notice review is completed. |
| `helix-db-main.zip` | mixed Apache/AGPL / needs-review | Graph concepts only until path-level review. |

## 3. Product Benchmark Takeaways

Checked product/docs references on 2026-06-19:

- OpenAI prompt guidance: outcome/context/constraints/tasks/acceptance/testing style, avoiding noisy legacy over-specification when unnecessary.
- TradingView: the user expectation is rich charting, screeners, heatmaps, options chains, volatility/greeks/theoretical pricing, and customizable views.
- Bloomberg Terminal: the user expectation is integrated data, research, news, charts, portfolio analytics, command-style workflows, and professional density.
- Koyfin: the user expectation is portfolio analytics, reports, dashboards, screeners, financial analysis, alerts, and clear research outputs.
- OpenBB Workspace: the user expectation is bring-your-own data, widgets, AI on governed data, auditability, portfolio analytics, crypto, macro scenarios, and alternative data.
- TradingView Lightweight Charts: acceptable chart foundation if used client-side, with TradingView attribution and Apache-2.0 license compliance.

Design implication:

The app must become a workstation, not a site and not a contract catalog. Each screen should answer a real user question, expose source truth, and support a next action.

## 4. Target System Shape

Final product shape:

- Streamlit: internal lab/admin/regression surface.
- `lib/`: reusable provider, normalization, scoring, contract, report, and quant engines.
- Optional FastAPI: local/prod API boundary for runtime envelopes.
- `apps/web`: commercial B2C workstation.
- Static fixtures: deterministic demos/tests only, never the default truth for live product claims.
- Runtime cache: shared TTL/stale/error semantics.
- AI: Gemini/free-first source-bound summarization with deterministic fallback; no source-free claims.
- Future persistence: Supabase-style local contract first, hosted auth/billing only after product workflows stabilize.

Required workspaces:

1. Today / Daily Brief
2. Market Intelligence
3. War Map / World Monitor
4. Equity Intelligence
5. Financial Statements
6. Options / GEX / Volatility
7. Crypto Intelligence
8. Screener
9. Portfolio Quant
10. Event Graph
11. News / OSINT Feed
12. Research Reports
13. Command Terminal
14. Provider/Data Center

Every workspace must show:

- provider
- source_url
- fetched_at
- freshness
- source_status
- confidence
- caveat
- data_gap
- unavailable/missing-key/rate-limit/subscription states where applicable

## 5. Product Slice Order

### Phase 5E.1: Runtime API And Chart Renderer Proof

Goal:

- Prove the optional runtime API path for one major workspace.
- Replace distorted/minimal finance charts with a real chart renderer foundation.

Targets:

- Market Intelligence first.
- Then Equity and Crypto chart specs.

Acceptance:

- `runtime-api` success state is visible when backend is reachable.
- `runtime-fallback` is visible when backend is absent, failing, or invalid.
- TradingView Lightweight Charts or equivalent renders client-only charts without SSR errors.
- Native SVG remains fallback.
- Desktop/mobile screenshots prove nonblank, non-overlapping charts.

### Phase 5E.2: Map-News-Event Fusion

Goal:

- Make War Map behave more like WorldMonitor/worldview.

Targets:

- Marker clustering or grouped marker states.
- Map-linked news list.
- Timeline filters that visibly change markers.
- Layer source health rail.
- Event-to-asset links in marker detail.

Acceptance:

- Map, news, layers, and event graph are one workflow.
- AIS/flight/sanctions remain unavailable/missing-key unless real provider succeeds.

### Phase 5E.3: Dedicated Equity/Financial/Options Workspaces

Goal:

- Stop aliasing financials/options over the same shallow equity payload.

Targets:

- `financial_statement_workspace`.
- `options_quant_workspace`.
- Option chain readiness, IV/RV/skew/term-structure/GEX proxy with caveats.
- Statement tables/charts/availability heatmap.

Acceptance:

- No fake financial statements.
- No dealer-positioning claims without source.
- Options output is research context, not execution advice.

### Phase 5E.4: Screener And Portfolio Quant

Goal:

- Bring the missing Streamlit lab value into the web product.

Targets:

- `screener_workspace` with filters, rankings, heatmap, scatter, watchlist staging.
- `portfolio_quant_workspace` with holdings, exposure, drawdown, attribution, stress, correlation.

Acceptance:

- No brokerage/account connection.
- Local-only demo portfolios are labeled local/proxy.

### Phase 5E.5: Daily Brief And Research Memory

Goal:

- Give the product daily return value.

Targets:

- `daily_brief` contract.
- Source-bound "what changed" rows.
- Local snapshot memory.
- Report v2 using runtime rows when available.

Acceptance:

- AI unavailable -> deterministic rule-based brief.
- No source-free generated claims.

## 6. Engineering Process From Agent Skills

Use the MIT `agent-skills-main` methods as execution discipline:

- `spec-driven-development`: write the exact user-visible acceptance criteria before coding.
- `planning-and-task-breakdown`: split runtime, chart, map, data, and UI into independently testable slices.
- `source-driven-development`: inspect current files and official docs before implementation.
- `api-and-interface-design`: contracts first, page code second.
- `frontend-ui-engineering`: inspect actual rendered screens at desktop and mobile widths.
- `test-driven-development`: focused tests/validators first, broad regression after.
- `debugging-and-error-recovery`: when a render/runtime check fails, reproduce, isolate, fix, and rerun.
- `code-review-and-quality`: review correctness, readability, architecture, security, performance.
- `security-and-hardening`: no secrets, no raw `.env`, no unreviewed external source, no fake live, no advice/execution path.

## 7. Immediate Decision

The next coding prompt should not ask for another planning-only pass. It should execute Phase 5E.1:

1. Prove runtime API success/fallback for Market Intelligence.
2. Add client-only financial chart renderer using `lightweight-charts` if dependency/license review is accepted.
3. Update Market/Equity/Crypto chart panels.
4. Verify desktop/mobile screenshots.
5. Report data truth honestly.

