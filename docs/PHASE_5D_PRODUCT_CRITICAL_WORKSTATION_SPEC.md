# Phase 5D Product-Critical Workstation Spec

Updated: 2026-06-19

Phase 5D starts the product-critical correction after the user called out that the web shell still felt too much like a fixture gallery. This slice implements the first source-bound research report contract and web surface inspired by the supplied Gold Quant report structure, while keeping the output non-advisory and source/status-labeled.

## Implemented In This Slice

### Source-Bound Research Report Contract

Files:

- `lib/research_report_workstation.py`
- `lib/api_contracts.py`
- `backend/api/app.py`
- `scripts/export_api_fixtures.py`
- `static/api-fixtures/research-report.json`

Added:

- `research_report_workstation.v1` native contract builder.
- `build_api_research_report_payload()` envelope with payload type `research_report`.
- Optional API getter and route: `/api/research-report`.
- Deterministic fixture export for `research-report.json`.
- Source register built from Market, Equity, Crypto, and Provider Health rows.
- Eight required report sections:
  - Executive Summary
  - Market Snapshot
  - Macro And Cross-Asset Context
  - News And Geopolitical Risk
  - Technical And Market-Structure Observations
  - Options, GEX, And Volatility Readiness
  - Scenario Matrix
  - Data Sources, Confidence, Caveats, And Gaps

### Gold Quant Adaptation Boundary

The supplied Gold Quant report is used as a structure reference only.

Allowed adoption:

- Section ordering and source checklist thinking.
- Market snapshot, macro, news/geopolitical, technical, options/GEX readiness, scenario matrix, and source-confidence structure.
- Explicit data gaps when source rows are missing.

Blocked or rewritten language:

- Trade permission
- Recommended leverage / maximum leverage
- Long or short entry language
- Stop-loss and take-profit instructions
- Position sizing advice
- Final action to trade
- Broker/account/order pathway language

Replacement language:

- Research readiness
- Risk exposure context
- Evidence zone
- Invalidating evidence
- Scenario objective area
- Risk budget context
- Final research stance
- Account-action pathway disabled

### Web Surface

Files:

- `apps/web/src/lib/contracts.ts`
- `apps/web/src/lib/fixtures.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/scripts/validate-fixtures.mjs`

Added:

- Workspace key: `research-report`.
- Fixture definition and route metadata.
- Report reader view with:
  - report command strip,
  - source-bound section cards,
  - evidence mini rows,
  - scenario matrix,
  - policy boundary,
  - source register table.

## Current Data Truth

This slice does not claim new live market data.

- `research-report`: deterministic fixture by default.
- Source rows inherit status from existing Market/Equity/Crypto/provider contracts.
- Fixture/proxy/provider-required/unavailable states remain visible.
- News/geopolitical integration is represented as a v1 data gap rather than invented live analysis.
- Options/GEX is readiness-only unless provider-backed chain/surface data exists.

## Verification

Passed on 2026-06-19:

```powershell
python -m py_compile app.py lib/api_contracts.py lib/research_report_workstation.py backend/api/app.py scripts/export_api_fixtures.py
python -m pytest tests/test_research_report_workstation.py tests/test_api_fixture_export.py tests/test_api_contracts.py tests/test_api_backend_routes.py -q
python scripts/export_api_fixtures.py
npm.cmd --prefix apps/web test
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web audit --audit-level=high
```

Results:

- 16 `phase_2b.v1` fixtures validated.
- Research report focused tests passed.
- Optional FastAPI smoke remains optional and may skip when dependency is unavailable.
- Next.js production build passed.
- `npm audit --audit-level=high` found 0 vulnerabilities.

## Visual Verification

In-app Browser was unavailable because no `node_repl js` tool was exposed in this session.

Fallback verification used local Next production server on:

- `http://127.0.0.1:3012/?view=research-report&mode=fixture`

Markers verified in HTML:

- `Research Report`
- `Source-Bound Report`
- `Research Sections`
- `Scenario Matrix`
- `Source Register`

Screenshots:

- `dist/phase5d-product-critical-screenshots/research-report-desktop.png`
  - 1440x1200
  - sampled unique colors: 35
  - 184,271 bytes
- `dist/phase5d-product-critical-screenshots/research-report-mobile.png`
  - 390x1200
  - sampled unique colors: 24
  - 32,671 bytes

The local verification server was stopped after screenshots were captured.

## Remaining Phase 5D Work

Still not complete:

1. Runtime API success path proof for at least one major workspace.
2. Dedicated finance chart renderer adoption, preferably after TradingView Lightweight Charts docs/license review and dependency approval.
3. Market/equity/crypto chart surface upgrades beyond native SVG fallback.
4. Report v2 ingestion of live/news/map/provider rows instead of v1 readiness placeholders.
5. Screener, portfolio quant, financial statement, and options/GEX dedicated workspaces.

## Non-Goals

Not added in this slice:

- Broker/account execution.
- Auth, billing, accounts, hosted persistence.
- Paid provider lock-in.
- Dealer positioning claims without source data.
- Trading advice or account-action recommendations.
- External source-code copy from AGPL/NASA/missing-license references.
