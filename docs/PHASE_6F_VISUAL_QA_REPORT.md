# Phase 6F Visual QA Report

Updated: 2026-07-03

## Production Matrix

The final Playwright/Chrome run used
`http://127.0.0.1:3052` with the runtime at `http://127.0.0.1:8008`.

| Scenario | Result |
|---|---|
| Desktop saved Catalyst Watchlist | 2 fixture catalysts, no overflow |
| Mobile saved Catalyst Watchlist | selected analysis precedes list, no overflow |
| TSLA exact Catalyst workstation | 7 cached exact rows, no overflow |
| Return to Watchlist | TSLA/catalysts/metric-desc/sector/catalysts restored |
| HTTP 429 | saved snapshot retained with explicit message |
| Runtime blocked/offline | saved snapshot retained with explicit message |

## Accessibility Checks

- 41 interactive Watchlist controls inspected;
- zero duplicate IDs;
- zero controls without an accessible name;
- Watchlist controls show a 2 px visible keyboard focus outline;
- desktop and 390 px mobile have zero horizontal overflow.

## Personal Inspection

The final desktop, mobile, and exact-asset screenshots were inspected. Desktop
keeps identity, event, exact news, materialization health, and source truth in a
dense scan-first layout. Mobile puts the selected catalyst analysis before the
long symbol and operations rails. No clipped control or incoherent overlap was
observed.

Evidence:

- `review_workspace/phase6f_visual/watchlist-catalysts-desktop.png`
- `review_workspace/phase6f_visual/watchlist-catalysts-mobile.png`
- `review_workspace/phase6f_visual/asset-tsla-catalysts.png`
- `review_workspace/phase6f_visual/watchlist-tsla-returned.png`
- `review_workspace/phase6f_visual/provider-failure-lkg.png`
- `review_workspace/phase6f_visual/api-offline-saved-snapshot.png`
- `review_workspace/phase6f_visual/summary.json`

This is strong internal-beta evidence, not a claim of TradingView, OpenBB, or
Bloomberg parity.
