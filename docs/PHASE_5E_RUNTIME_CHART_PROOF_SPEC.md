# Phase 5E.1 Runtime And Chart Proof

Date: 2026-06-19

## Decision

Phase 5E.1 is a correction slice, not a final product milestone.

The user-visible issue was valid: the web workstation looked better than Streamlit, but too many views still behaved like contract/fixture previews instead of a serious cross-asset terminal. This slice therefore focused on two concrete proof points:

- prove that `apps/web` can consume an optional runtime API envelope and honestly fall back when the API is absent or invalid;
- replace the weakest native chart presentation for Market, Equity, and Crypto with the first credible finance-chart renderer foundation.

## Source Review

Official/source evidence reviewed:

- OpenAI prompt guidance: prompts should define outcome, context, constraints, expected shape, and verification gates.
- Lightweight Charts docs: client-side chart creation uses `createChart`, supported series types include Area, Histogram, and Line, and data is supplied through `setData`.
- Lightweight Charts license: Apache License 2.0.
- Lightweight Charts attribution docs: public pages should credit TradingView as the product creator and link to TradingView.

Dependency decision:

- Adopt `lightweight-charts` for the web finance-chart renderer foundation.
- Keep native SVG as fallback.
- Do not add broker execution, paid data dependency, auth, billing, hosted persistence, or live claims.

## Implemented

Runtime proof:

- Added `apps/web/scripts/validate-runtime-api-smoke.mjs`.
- The script starts a deterministic local mock API that serves the existing `market-intelligence` fixture envelope.
- It starts Next production mode against that API and verifies `/?view=market-intelligence&mode=live-if-available` renders `runtime-api`.
- It starts a second production-mode pass against a bad API base and verifies the page renders `runtime-fallback`.
- FastAPI is still optional. The current Python environment does not have `fastapi` installed, so this slice did not pretend to prove a real backend runtime server.

Chart renderer:

- Added `apps/web/src/components/FinanceChart.tsx`.
- The component is client-only and dynamically imports `lightweight-charts` to avoid SSR `window` failures.
- It supports line/area series and histogram/bar-style series where current chart specs are compatible.
- It supports synthetic time mapping for category-based fixture charts.
- It displays `TradingView Lightweight Charts renderer active` and `Charts by TradingView`.
- It keeps source status, caveat, data gap, and native SVG fallback visible in the surrounding chart panel.

Web integration:

- `apps/web/src/app/page.tsx` now renders `FinanceChart` for Market, Equity, and Crypto chart specs and keeps native SVG under a fallback disclosure.
- `apps/web/src/app/globals.css` adds stable chart shell, attribution, category strip, fallback, and responsive chart styling.
- `apps/web/scripts/validate-runtime-ui.mjs` now fails if the finance renderer, dynamic import, TradingView attribution, or fallback hooks are removed.

## Data Truth

Current truth after this slice:

- Market, Equity, and Crypto charts are rendered by a real finance chart library in fixture mode.
- Fixture mode remains deterministic and network-free.
- The runtime smoke proves the UI boundary can show `runtime-api` and `runtime-fallback`.
- The smoke API uses a deterministic local mock, not live market data.
- FastAPI remains `optional/off` unless `requirements-api.txt` is installed and a real local backend is started.
- No fixture/proxy/static row is relabeled as live/fresh.
- No chart is financial advice.

## Visual Verification

In-app Browser was unavailable in this session. Headless Microsoft Edge was used as the local render fallback.

Screenshots:

- `dist/phase5e-runtime-chart-screenshots/market-desktop.png` - 1440 x 1200
- `dist/phase5e-runtime-chart-screenshots/market-mobile.png` - 390 x 1200
- `dist/phase5e-runtime-chart-screenshots/market-mobile-tall.png` - 390 x 3000
- `dist/phase5e-runtime-chart-screenshots/market-mobile-chart-depth.png` - 390 x 6000
- `dist/phase5e-runtime-chart-screenshots/equity-desktop.png` - 1440 x 1200
- `dist/phase5e-runtime-chart-screenshots/equity-mobile-tall.png` - 390 x 3000
- `dist/phase5e-runtime-chart-screenshots/crypto-desktop.png` - 1440 x 1200
- `dist/phase5e-runtime-chart-screenshots/crypto-mobile.png` - 390 x 1200
- `dist/phase5e-runtime-chart-screenshots/crypto-mobile-tall.png` - 390 x 3000

Findings:

- Desktop Market, Equity, and Crypto render nonblank Lightweight Charts panels with TradingView attribution.
- Mobile rendering works, but the left workspace rail and summary stack push charts too far down the page on narrow widths.
- The next web UX slice should collapse or tab the mobile workspace navigation so analysis content appears earlier.

## Verification

Passed:

```powershell
python -m py_compile app.py lib/api_contracts.py lib/research_report_workstation.py backend/api/app.py scripts/export_api_fixtures.py
python -m pytest tests/test_research_report_workstation.py tests/test_api_fixture_export.py tests/test_api_contracts.py tests/test_api_backend_routes.py tests/test_market_intelligence_contracts.py tests/test_equity_intelligence_contracts.py tests/test_crypto_intelligence_contracts.py -q
python scripts/export_api_fixtures.py
npm.cmd --prefix apps/web test
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web run test:runtime-api
npm.cmd --prefix apps/web audit --audit-level=high
```

Audit result:

- `npm audit --audit-level=high`: `0 vulnerabilities`.

## Remaining Gaps

This slice improves rendering and runtime boundary confidence, but it does not complete the commercial terminal.

Remaining high-priority gaps:

- Real FastAPI-backed runtime mode for major workspaces.
- Real source-backed Market/Equity/Crypto rows in the web runtime path.
- Map-news-event fusion comparable to WorldMonitor/worldview behavior.
- Dedicated screener, portfolio quant, financial statement, options chain/GEX, and watchlist workspaces.
- Mobile workstation navigation and content prioritization.
- Persistent research memory, watchlists, alerts, accounts, billing, and hosted storage.

## Next Slice

Recommended next slice: Phase 5E.2 Map-News-Event Runtime Fusion.

Purpose:

- make War Map stop behaving like a separated map panel;
- connect map markers, news rows, event graph links, provider health, and market impact context in one source-bound workspace;
- improve mobile navigation so the primary analysis content is visible sooner.
