# Phase 5X Visual QA Report

Updated: 2026-06-30

## Harness

Command:

```powershell
$env:GT_BASE_URL='http://127.0.0.1:3040'; $env:GT_EXPECT_RUNTIME='online'; npm.cmd --prefix apps/web run visual:phase5x
```

Online runtime:

- FastAPI: `http://127.0.0.1:8002`
- Next production: `http://127.0.0.1:3040`
- Runtime chip: `api-importable`, reachable `true`.

Offline command:

```powershell
$env:GLOBAL_TERMINAL_API_BASE_URL='http://127.0.0.1:65534'
$env:NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL='http://127.0.0.1:65534'
npm.cmd --prefix apps/web run start -- --hostname 127.0.0.1 --port 3041
$env:GT_BASE_URL='http://127.0.0.1:3041'; $env:GT_EXPECT_RUNTIME='offline'; npm.cmd --prefix apps/web run visual:phase5x
```

Offline runtime:

- Runtime chip: `runtime-api-offline`, reachable `false`.
- The temporary 3041 process was stopped after capture by matching current repo path and port.

## Online Screenshots

| Route | Screenshot | Result |
| --- | --- | --- |
| Home | `review_workspace/phase5x_provider_breadth_visual/home-online.png` | PASS, runtime online, no overflow |
| AAPL Financials | `review_workspace/phase5x_provider_breadth_visual/aapl-financials-provider-breadth.png` | PASS, Alpha/Finnhub breadth visible in first viewport |
| AAPL News | `review_workspace/phase5x_provider_breadth_visual/aapl-news-provider-breadth.png` | PASS, 11 company/news rows |
| BTCUSDT | `review_workspace/phase5x_provider_breadth_visual/btcusdt-overview.png` | PASS, chart ready, 416 points |
| Unknown symbol | `review_workspace/phase5x_provider_breadth_visual/unknown-symbol.png` | PASS, no fixture substitution |
| AAPL Financials mobile | `review_workspace/phase5x_provider_breadth_visual/aapl-financials-mobile.png` | PASS, provider breadth visible, no horizontal overflow |

## Offline Screenshots

| Route | Screenshot | Result |
| --- | --- | --- |
| Home offline | `review_workspace/phase5x_provider_breadth_visual/offline-home.png` | PASS, runtime offline surfaced |
| AAPL fallback | `review_workspace/phase5x_provider_breadth_visual/offline-aapl-fallback.png` | PASS, fallback chart ready with 125 points |
| Unknown offline | `review_workspace/phase5x_provider_breadth_visual/offline-unknown-symbol.png` | PASS, unknown remains unavailable |

## Manual Inspection

The AAPL Financials desktop screenshot was opened and inspected. The revised layout places core valuation rows and the Alpha Vantage/Finnhub breadth panel side by side, so provider data is visible in the first viewport instead of starting below the fold.

The AAPL Financials mobile screenshot was opened and inspected. The provider breadth panel stacks under the core financial rows, shows Alpha/Finnhub source status and avoids horizontal overflow.

## Remaining Visual Gaps

- Financials still need richer charting for revenue, earnings and margins.
- The map route was not improved in this slice.
- The heatmap route was not improved in this slice.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
