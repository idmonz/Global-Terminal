# Goal 10 Plan

Goal 10 productizes the Goal 9 baseline without rewriting the app or vendoring external projects.

## Scope

- Executive Terminal UX: summary-first global and workspace payloads.
- Command UX: Bloomberg-style function codes implemented in native Python/Streamlit.
- Provider Probe: lightweight diagnostics, dry-run mode, gitignored results.
- No-key/free source layer: SEC, Treasury Fiscal Data, World Bank, SDMX, GDELT, USGS, Open-Meteo, NWS, NOAA AccessAIS, Binance public, DefiLlama, and CoinGecko public fallback.
- Alpha Strategy Workbench: combination search, ensemble builder, regime performance, walk-forward/OOS, risk budgeting, visual lab, and data quality.
- Environment handling: `.env` loaded through python-dotenv, blank `.env.example`, masked status only.

## Exclusions

- No live trading, broker execution, order routing, full MCP/API server, mandatory OpenBB, Finviz scraping, Fincept integration, or copied OpenBB/WorldMonitor/BB-Terminal/OpenAlice source.
