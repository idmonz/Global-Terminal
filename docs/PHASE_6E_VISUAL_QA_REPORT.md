# Phase 6E Visual QA Report

Updated: 2026-07-03

## Evidence

Final online captures:

- `review_workspace/phase6e_visual_live-fresh-final/asset-aapl-desktop.png`
- `review_workspace/phase6e_visual_live-fresh-final/asset-tsla-mobile.png`
- `review_workspace/phase6e_visual_online-no-prefetch/asset-aapl-desktop.png`
- `review_workspace/phase6e_visual_online-no-prefetch/asset-tsla-mobile.png`
- `review_workspace/phase6e_visual_online-no-prefetch/watchlist-advanced-desktop.png`
- `review_workspace/phase6e_visual_online-no-prefetch/asset-unknown.png`

Blocked-network captures:

- `review_workspace/phase6e_visual_offline-proof/asset-aapl-offline-desktop.png`
- `review_workspace/phase6e_visual_offline-proof/asset-tsla-offline-mobile.png`

## Inspection

The first desktop capture exposed chart canvas overflow because the renderer
used a taller responsive height than its CSS container. `FinanceChart` now caps
the renderer at the measured container height. The final desktop x-axis,
attribution, caveat, and disclosure no longer overlap.

Final evidence confirms:

- exact AAPL/TSLA identity and nonblank charts;
- chart in the first practical desktop/mobile workflow;
- no page-level horizontal overflow;
- dense controls remain legible at 390px;
- unknown symbol has no AAPL fallback;
- offline summary remains visible while chart is explicitly unavailable;
- advanced watchlist grouping is scannable and mode changes make zero panel
  requests;
- no unexpected browser console/page errors.

The `live-fresh` run showed the current AAPL `308.63` and TSLA `393.45`
observations through the live-if-available path. The subsequent chart read was
truthfully labeled cached because it reused the just-refreshed exact-symbol
history.
