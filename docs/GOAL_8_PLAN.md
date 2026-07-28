# Goal 8 Plan

## Objective

Build an optional OpenBB backend bridge that strengthens the Financial Terminal, Portfolio Quant Lab, Screener, Provider Center/Data Quality, and safe AI context without replacing native providers.

## Scope

- Add lazy OpenBB bridge modules under `lib/`.
- Add `pages/18_OpenBB_Data_Hub.py`.
- Add `requirements-openbb.txt` and `.env.example`.
- Keep yfinance, FRED, EIA, Binance, CoinGecko, DefiLlama, and native modules active.
- Add source modes: Auto, Native only, OpenBB preferred, OpenBB only.
- Add Strategy Research Engine v2 modules for candidate backtests, combinations, walk-forward/OOS validation, correlations, and report cards.

## Guardrails

- No OpenBB source code is copied into runtime modules.
- OpenBB is not required for base launch.
- Missing OpenBB or keys returns visible data gaps and warnings.
- Paid provider access is never implied.
- AI remains button-triggered and receives compact summaries only.
