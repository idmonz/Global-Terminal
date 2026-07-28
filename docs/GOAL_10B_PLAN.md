# Goal 10B Plan

Goal 10B hardens the existing Goal 10 implementation into a modern Global Intelligence Terminal. It keeps the project-native Python, Streamlit, and Plotly architecture and does not copy or integrate external source trees.

## Scope

- Modern visual system: reusable tokens, summary-first cards, keyword chips, source freshness, confidence, and click-next affordances.
- Heatmap system: internal treemap/tile engines, modern color buckets, rich tooltips, drilldown command suggestions, provider/source/portfolio/War Room/Energy heatmap payloads, and optional TradingView embeds labeled as external visual supplements only.
- Command UX: top command bar payloads, shortcut registry/help, refresh state, source freshness indicators, command history compatibility, and no trade execution language.
- Relative Market Intelligence and Global Volatility Monitor: relative scores, z-scores, drawdowns, risk states, and overview-ready boards.
- Map-first intelligence: War Room, Energy Geopolitics, News, OSINT layers, marker payloads, event clustering, geospatial tooltips, and truthful live/proxy/historical labels.
- Provider probes: split scripts for OpenBB runtime, provider matrix, macro/energy, crypto, and news/OSINT sources, with missing keys treated as nonfatal.
- Documentation and tests: module-level tests, compliance guards, smoke imports, release hygiene verification, and Goal 10B final reporting.

## Exclusions

- No Bloomberg clone visual style.
- No Finviz, Fincept, OpenStock, WorldMonitor, OpenBB, OpenAlice, Bloomberg-terminal, or BB-Terminal source integration.
- No live trading, broker execution, order routing, automatic rebalancing, mandatory paid APIs, or full MCP/API server.
- No fake live AIS, flight, liquidation, provider, or official feed claims.
