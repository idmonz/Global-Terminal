# Phase 5E.3 Web-Native Market Workstations

Updated: 2026-06-19

## Outcome

Phase 5E.3 turns the missing Streamlit-era market intelligence tabs into visible web-native workstations. This is a product correction slice: the web app should stop looking like a contract gallery and start exposing the useful equity, crypto, financial, options, and screener workflows that already existed in Streamlit and `lib/`.

## Current Product Role

- Streamlit remains the internal lab and regression surface.
- `lib/` remains the reusable runtime, normalization, scoring, and contract layer.
- `backend/api` remains optional and import-safe without FastAPI as a base dependency.
- `apps/web` is the commercial B2C workstation surface.
- Static fixtures remain deterministic, network-free, secret-safe, and source-labeled.

## Implemented Slice

### Dedicated Contracts

Added `lib/web_market_workstations.py` with:

- `build_financial_fundamentals_contract()`
- `build_options_quant_contract()`
- `build_screener_drilldown_contract()`

These contracts reuse existing engines instead of duplicating business logic:

- `lib/equity_intelligence.py`
- `lib/market_intelligence.py`
- `lib/options_lab_page_layout.py`
- `lib/options_provider_capabilities.py`
- `lib/heatmap_drilldown_engine.py`

### API Envelopes

Added `phase_2b.v1` payload builders:

- `build_api_financial_fundamentals_payload()`
- `build_api_options_quant_payload()`
- `build_api_screener_drilldown_payload()`

Payload types:

- `financial_fundamentals`
- `options_quant`
- `screener_drilldown`

Optional API routes:

- `GET /api/financial-fundamentals`
- `GET /api/options-quant`
- `GET /api/screener-drilldown`

### Deterministic Fixtures

Added fixtures:

- `static/api-fixtures/financial-fundamentals.json`
- `static/api-fixtures/options-quant.json`
- `static/api-fixtures/screener-drilldown.json`

The web fixture validator now expects 20 fixtures.

### Web Views

Added dedicated Next.js workstations:

- `FinancialFundamentalsWorkspace`
- `OptionsQuantWorkspace`
- `ScreenerDrilldownWorkspace`

Financial/Fundamentals and Options/Quant are no longer aliases over `equity-intelligence.json`.

Visible user surfaces now include:

- company profile and statement-style metrics,
- valuation/data-quality checks,
- source register and provider gaps,
- options provider capabilities,
- Greeks snapshot,
- options scenario surface,
- explicit live chain/GEX/dealer-positioning boundary,
- screener tile drilldown targets,
- sector summaries,
- heatmap tile link into the drilldown workspace.

## Data Truth

Financial/Fundamentals:

- Current fixture state is source-labeled profile/metric context.
- Full statements, estimates, filings, and premium fundamentals remain provider-required or unavailable when not backed by a provider.

Options/Quant:

- Manual calculator and model rows may be supplied in fixture mode.
- Live option chain, GEX, dealer positioning, and institutional flow are not claimed.
- Provider-required rows remain visible in `source_register` and `unavailable_sources`.

Screener/Drilldown:

- Heatmap drilldown is based on fixture-labeled Market Intelligence heatmap rows.
- Live screener universe, market caps, returns, and fundamentals remain provider-required until a verified provider is wired.

All new rows preserve:

- provider/source status,
- freshness or explicit fixture/provider-required state,
- caveat,
- data gap,
- non-advisory marker.

## External Reference Policy

This slice uses external references as behavior evidence only:

- Finviz/TradingView heatmaps for tile-to-context behavior.
- Bloomberg/BB-Terminal style for dense command-like workstation organization.
- OpenBB for finance workflow hierarchy and provider-gated contracts.
- FinanceDatabase for asset taxonomy thinking.

No external source, CSS, assets, or datasets were copied.

## Verification

Required checks:

- Python compile for changed API/contract/export modules.
- Focused contract/backend/fixture tests.
- Full pytest suite.
- Web fixture validation.
- Next lint and production build.
- Runtime API smoke.
- High-severity npm audit.
- Desktop/mobile screenshots for changed routes.

## Remaining Gaps

The web terminal is improved, but still not final B2C quality:

- A live provider-backed screener universe is not wired.
- Financial statements/filings are still fixture/provider-required unless optional providers are configured.
- Options chains, volatility surface, dealer positioning, and unusual flow remain provider-required.
- Symbol-specific route parameters are still shallow in the web shell.
- Map/news/event fusion exists, but richer worldmonitor/worldview-style map interactivity and data density remain future work.
- Portfolio quant, alerts, accounts, persistence, and billing remain future phases.

## Next Recommended Slice

Phase 5E.4 should wire free-first runtime data into the web workstations:

- symbol query state,
- market/equity/crypto runtime API calls,
- provider-backed screener rows where possible,
- explicit yfinance/free-provider diagnostics,
- options/fundamentals provider setup guidance,
- richer symbol drilldown navigation without fake live claims.
