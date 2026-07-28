# Phase 5S Product Exposure Report

Updated: 2026-06-23

## User Critique Accepted

The critique was correct: the project had accumulated many contracts, fixtures, providers, and workstations, but the commercial web surface at `http://127.0.0.1:3000/` still hid too much of the Streamlit-era capability. The visible product needed to show a usable terminal journey, not another contract viewer.

## Architecture Truth

Streamlit is the internal lab and regression reference.

`lib/` is the reusable commercial engine layer: providers, normalization, market intelligence, symbol intelligence, map/news/event contracts, options, portfolio, research memory, daily brief, command workspace, and API-safe envelopes.

FastAPI is the optional local API boundary.

Next.js is the intended B2C/commercial product surface. The goal is to reimplement the useful Streamlit concepts and external-reference behaviors in the web product, while keeping provenance and clean-room licensing boundaries intact.

## Phase 5S Work Completed

- Added a first-viewport Market Terminal Cockpit to the market home.
- Exposed direct journeys to Market Map, Stock Market, Crypto Market, Options, War Map, Daily Brief, Command Workspace, and Research Memory.
- Reframed the left product navigation from hard-coded `AAPL` / `BTCUSDT` labels to market-level `Stock Market` / `Crypto Market` entries, with AAPL and BTCUSDT retained only as default representative workstations.
- Added home summary rows for market pulse, news/risk, discovery, and command tape.
- Changed product navigation so data-heavy pages open with `live-if-available` unless fixture mode is explicitly selected.
- Rebuilt command workspace as a product shell with product navigation, command launch cards, route links, provider boundaries, and command previews.
- Added Phase 5S visual capture harness.
- Added test markers so cockpit/command launchpad regressions are caught by web tests.

## Visual Evidence

Final desktop/mobile visual output:

- `review_workspace/phase5s_final3/home-desktop.png`
- `review_workspace/phase5s_final3/home-mobile.png`
- `review_workspace/phase5s_final3/command-desktop.png`
- `review_workspace/phase5s_final3/aapl-asset-desktop.png`
- `review_workspace/phase5s_final3/war-map-desktop.png`

Final capture summary:

- Home: 12 product nav links, 24 chart cards/renderers, 30 heatmap tiles, 2 news/risk rows, 6 command rows, no horizontal overflow, zero console/page errors.
- Command Workspace: 12 product nav links, 19 command rows, 17 source/boundary rows, product shell active, no contract diagnostics text, zero console/page errors.
- AAPL cache route: chart rows appeared after API cache warmup.
- War Map route: 2 map renderers/fallback surfaces visible.

## Remaining Bottlenecks

- BTCUSDT cache route can still show zero chart rows after cache miss; crypto live/cache/fixture fallback needs a sharper first-run path.
- Options route still exposes contract/chain/quality surfaces more than full visual analytics; IV surface and payoff/chart panels should be more first-class.
- War Map has markers and map rendering, but it still falls short of WorldMonitor/worldview-style event/news/layer interaction density.
- News is visible on home as risk/news context, but the dedicated news workspace still needs a stronger product route.
- Stock/crypto workstations exist, but the first-viewport depth is still below TradingView/Koyfin style multi-panel charting.
- Many Streamlit-era pages are represented by contracts or partial web routes rather than fully polished commercial surfaces.
- External archives are mechanically indexed, but each adopted feature still needs targeted semantic review and clean-room implementation notes.

## Verification

Passed:

```powershell
npm.cmd --prefix apps/web test
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web run visual:phase5s
```

In-app browser bootstrap was unavailable in this session, so repository `playwright-core` plus local Chrome was used for visual QA.

Outputs remain research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, or autonomous execution.
