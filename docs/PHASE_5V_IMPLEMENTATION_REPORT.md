# Phase 5V Implementation Report

Updated: 2026-06-30

## Objective

Respond to the visible product critique that the asset route still felt like a chart plus hidden contracts rather than a TradingView/OpenBB/Bloomberg-like symbol intelligence workstation.

This slice improves the visible `/?view=asset` route while preserving:

- Streamlit as internal lab/reference;
- `lib/` as reusable provider, quant and contract logic;
- optional FastAPI as local API boundary;
- Next.js as the commercial B2C surface;
- free-first provider policy;
- source/freshness/caveat/data-gap truth;
- no advice, no execution and clean-room external boundaries.

## Implemented

### Symbol Workstation UI

- Added `Options` as an equity-only symbol surface.
- Added a compact `SymbolDeskStrip` before the chart with:
  - desk mode;
  - source and market status;
  - OHLCV row count;
  - comparison overlap;
  - exact-symbol news count;
  - financial/options or derivatives status.
- Added source-aware right rail content with `SourceMiniLedger`.
- Added overview context cards for:
  - financial availability or crypto derivatives;
  - exact-symbol news;
  - comparison;
  - news/event/War Map links;
  - equity options bridge, crypto derivatives card or ETF fund boundary;
  - source posture.
- Added `OptionsBridgeSurface` so equity symbols can open an options-specific tab without claiming OPRA-grade completeness, broker execution or recommendations.
- Added ETF-specific fund/profile card so ETFs do not receive company-only or crypto-only context.

### Runtime/Fallback Behavior

- Moved asset runtime diagnostic banners below the workstation. Users now see the product surface first, while fallback truth remains inspectable.
- Added static-catalog comparison recomputation in the Next.js fallback path. If the backend is unavailable but both selected and comparison symbols exist in the deterministic catalog, the route builds a timestamp inner-join comparison labeled `fixture-route-join`.
- Preserved unknown-symbol protection: unsupported symbols still do not substitute AAPL, BTCUSDT or any other fixture.

### Visual Harness

- Added `apps/web/scripts/capture-phase5v.mjs`.
- Added `npm.cmd --prefix apps/web run visual:phase5v`.
- Added tests in `tests/test_phase5v_symbol_workstation_depth.py`.

## Changed Files

- `apps/web/src/components/SymbolWorkstation.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/scripts/capture-phase5v.mjs`
- `apps/web/package.json`
- `tests/test_phase5v_symbol_workstation_depth.py`
- `docs/PHASE_5V_PREFLIGHT_AND_BOTTLENECKS.md`
- `docs/PHASE_5V_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5V_VISUAL_QA_REPORT.md`
- `docs/ROADMAP.md`
- `docs/GOAL_MASTER_PRODUCT_PARITY_STATUS.md`
- `docs/NEXT_ROADMAP_EXECUTION_PROMPT.md`

## Runtime Probe

When only Next.js is running, the route honestly falls back to deterministic fixture/catalog rows. After starting the optional FastAPI backend on `127.0.0.1:8000`, `live-if-available` AAPL rendered cached/latest-session runtime data with:

- 63 OHLCV rows;
- 63 SPY comparison overlap rows;
- 3 exact-symbol news rows;
- financial availability;
- source ledger showing live/cache/fixture/gap split.

The captured runtime screenshot is:

`review_workspace/phase5v_live_probe/aapl-live.png`

## Remaining Gaps

- A user must currently run both Next.js and FastAPI to see source-backed runtime rows in the web product.
- Full earnings, estimates, calendar and SEC panels remain bounded by available free providers and are not benchmark-grade.
- Crypto derivatives coverage remains source-bounded and does not include liquidation/account positioning.
- Watchlist side rail and multi-monitor terminal composition remain shallow compared with TradingView/OpenBB/Bloomberg.
- Hosted auth, billing, background refresh, alert delivery and observability remain future commercial-platform work.

## Safety

No external source, screenshot, asset, dataset, font or trade dress was copied. TradingView/OpenBB/Finviz/WorldMonitor/Bloomberg-like references were used as clean-room behavior evidence only.

Outputs remain read-only research displays, not investment advice, broker actions, trade approvals, order routing or execution instructions.
