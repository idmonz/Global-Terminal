# Phase 5W Visual QA Report

Date: 2026-06-30

## Method

Final visual proof used the production Next.js server:

```powershell
npm --prefix apps/web run build
python scripts/start_local_product.py --production --wait-seconds 60
$env:GT_EXPECT_RUNTIME='online'; npm --prefix apps/web run visual:phase5w
```

The development server was not used for the final screenshots because Fast Refresh can reload client components while screenshots are being captured.

## Screenshots

- `review_workspace/phase5w_runtime_visual/home-runtime.png`
- `review_workspace/phase5w_runtime_visual/aapl-runtime.png`

Both screenshots were opened and inspected.

## Observed Result

Home route:

- Runtime chip: `online`.
- Runtime state: `api-importable`.
- Route/provider summary: `37 routes / 250 providers`.
- Chart state in harness: `ready`.
- Chart points in harness: `8`.
- Horizontal overflow: none.

AAPL route:

- Runtime chip: `online`.
- Runtime state: `api-importable`.
- Chart state in harness: `ready`.
- Chart points in harness: `184`.
- Direct browser probe: chart state `ready`, canvas count `35`.
- Horizontal overflow: none.

HTTP marker checks:

- `/?view=war-room-map&mode=cache`: HTTP 200, runtime reachable marker true.
- `/?view=asset&symbol=BTCUSDT&assetClass=crypto&interval=1h&range=5d&mode=cache&compare=ETHUSDT`: HTTP 200, runtime reachable marker true.

## Design Notes

- The runtime chip is visible in the top bar but does not dominate the first viewport.
- It makes backend availability explicit before the user inspects provider details.
- It does not promote fixture/cache rows to live.
- The AAPL production screenshot confirms the runtime chip did not push the chart out of usable position.

## Remaining Visual Gaps

- War Map and BTC were marker-checked in Phase 5W rather than screenshot-captured, because this phase focused on local runtime orchestration. Earlier phases hold map and BTC chart visual evidence.
- A dedicated offline screenshot harness should be added next, using a controlled API-offline state without killing unrelated user processes.
- The map still needs richer WorldMonitor/worldview-style layer/news/source co-presence and broader live layer breadth.
