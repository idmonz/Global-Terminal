# Phase 5V Visual QA Report

Updated: 2026-06-30

## Method

The browser skill was read and `node_repl` was made available. The actual visual capture used repository `playwright-core` plus local Chrome against the production Next.js server.

Command:

```powershell
npm.cmd --prefix apps/web run visual:phase5v
```

Screenshots and report:

- `review_workspace/phase5v_visual/phase5v-browser-report.json`
- `review_workspace/phase5v_visual/aapl-equity-desktop.png`
- `review_workspace/phase5v_visual/msft-equity-desktop.png`
- `review_workspace/phase5v_visual/spy-etf-desktop.png`
- `review_workspace/phase5v_visual/btcusdt-crypto-desktop.png`
- `review_workspace/phase5v_visual/ethusdt-crypto-desktop.png`
- `review_workspace/phase5v_visual/aapl-equity-mobile.png`
- `review_workspace/phase5v_visual/btcusdt-crypto-mobile.png`
- `review_workspace/phase5v_visual/aapl-options-surface.png`
- `review_workspace/phase5v_visual/unknown-symbol.png`

## Before-State Baseline

Baseline report:

`review_workspace/phase5v_before/baseline-report.json`

| Route | Before chart top | Before comparison | Before source ledger | Before context cards |
|---|---:|---:|---:|---:|
| AAPL desktop | 696px | 0 | 0 | 3 |
| MSFT desktop | 678px | 0 | 0 | 3 |
| SPY desktop | 678px | 0 | 0 | 3 |
| BTCUSDT desktop | 696px | 0 | 0 | 3 |
| ETHUSDT mobile | 976px | 0 | 0 | 3 |

The old `visual:phase5n` harness also failed because AAPL/SPY comparison overlap was missing in the visible web fallback path.

## Final Visual Results

| Route | Status | Chart top | Chart width | Rows | Compare | Context cards | Source ledger | Special check |
|---|---|---:|---:|---:|---:|---:|---:|---|
| AAPL desktop | fixture | 549px | 1096px | 48 | 48 | 6 | 1 | equity options bridge present |
| MSFT desktop | fixture | 549px | 1096px | 48 | 48 | 6 | 1 | line chart state preserved |
| SPY desktop | fixture | 549px | 1096px | 48 | 48 | 6 | 1 | no crypto derivatives leakage |
| BTCUSDT desktop | fixture | 549px | 1096px | 48 | 48 | 6 | 1 | crypto derivatives card present |
| ETHUSDT desktop | fixture | 549px | 1096px | 48 | 48 | 6 | 1 | crypto derivatives card present |
| AAPL mobile | fixture | 770px | 351px | 48 | 48 | 6 | 1 | no horizontal overflow |
| BTCUSDT mobile | fixture | 770px | 351px | 48 | 48 | 6 | 1 | no horizontal overflow |
| AAPL options surface | fixture | n/a | n/a | 48 | 48 | 1 | 0 | OPRA/no-execution boundary visible |
| Unknown symbol | unknown-symbol | n/a | n/a | 0 | 0 | 0 | 0 | no fixture substitution |

Browser console errors: zero.  
Page errors: zero.  
Horizontal overflow: none in checked desktop/mobile routes.

## Live Runtime Probe

After starting FastAPI on `127.0.0.1:8000`, AAPL `live-if-available` produced:

- status: `cached`;
- market status: `latest-session`;
- 63 OHLCV rows;
- 63 comparison rows vs SPY;
- 3 exact-symbol news rows;
- chart top: 549px;
- chart width: 1096px.

Evidence:

- `review_workspace/phase5v_live_probe/aapl-live.png`
- `review_workspace/phase5v_live_probe/aapl-live-report.json`

## Verdict

Phase 5V materially improves the symbol workstation and fixes the static fallback comparison defect. It still does not complete benchmark parity. The next blocker is runtime orchestration: users should not have to remember to start both Next.js and FastAPI to see source-backed rows.
