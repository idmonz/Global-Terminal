# Goal 11 External Reference Research Report

## External folder inventory

Actual inspected `external/` entries:

- `BB-Terminal-main.zip`
- `OpenAlice-master.zip`
- `OpenBB-develop.zip`
- `OpenStock-main.zip`
- `agent-skills-main.zip`
- `bloomberg-terminal-main.zip`
- `optlib-master.zip`
- `osiris-master.zip`
- `quant-traderr-lab-main.zip`
- `worldmonitor-main.zip`
- extracted `worldmonitor-main/worldmonitor-main/`
- `worldmonitor/`

## License / usage risk table

| Reference | License finding | Goal 11 boundary decision |
|---|---:|---|
| OpenStock-main.zip | AGPL-3.0 | Reference-only for watchlist, alert, quick-add, TradingView visual supplement, report workflow concepts; no source copied; Mongo/Auth/Finnhub/email automation rejected. |
| bloomberg-terminal-main.zip | No LICENSE found in archive during inspection | Reference-only for compact market table, shortcut help, source freshness, RMI/vol panels; simulated/random data and React code rejected. |
| BB-Terminal-main.zip | No LICENSE found in archive during inspection | Reference-only for command bar/function registry/scorecard patterns; no source copied. |
| worldmonitor-main.zip / extracted worldmonitor-main/ | AGPL-3.0 | Reference-only for map/event/news/chokepoint/provider caveat patterns; no UI/source copied. |
| osiris-master.zip | MIT, but bundled node_modules present | Reference-only for map-first OSINT/event feed/view preset concepts; node_modules and scraped/live feeds rejected. |
| OpenAlice-master.zip | AGPL-3.0 | Reference-only for inbox/workspace/guard/review and Trading-as-Git concept translated to Strategy-as-Git; broker/execution rejected. |
| OpenBB-develop.zip | AGPL-3.0 repository; desktop subfolder MIT | Reference-only for provider catalog/capability metadata; OpenBB remains optional. |
| optlib-master.zip | MIT | Future Goal 12 hook only: option analysis attachment placeholder; formulas not implemented. |
| quant-traderr-lab-main.zip | MIT | Future Goal 12 hook only: quant model snapshot placeholder; model library not implemented. |
| agent-skills-main.zip | MIT | Process-governance reference only: spec/plan/build/test/review/ship gates; no runtime dependency or hooks copied. |

## Inspected files/modules

The inspection covered archive inventories and, where present, `README.md`, `LICENSE`, `AGENTS.md`, `package.json`, `requirements.txt`, `pyproject.toml`, `setup.py`, `API_DOCS.md`, `ARCHITECTURE.md`, source-tree top-level directories, `src/`, `app/`, `components/`, `lib/`, `api/`, `docs/`, `scripts/`, `tests/`, `commands/`, `agents/`, `skills/`, `references/`, and hooks/plugin folders. The extracted WorldMonitor tree was also inspected beyond README through its AGENTS, ARCHITECTURE, API/source directory layout, docs, tests, scripts, and data-oriented folders.

## Useful concepts retained

- Multi-domain watchlist records that can represent assets, regions, chokepoints, providers, strategies, portfolios, and report topics.
- Alert center with manual evaluation, source status, freshness, and missing-data handling.
- Report inbox as durable local research memory.
- Strategy-as-Git decision log derived conceptually from Trading-as-Git, but scoped to research records only.
- OSINT watchlist linker that maps events/news/regions/providers to watchlist items with confidence and inferred labels.
- Command palette/function registry patterns for research workflow actions.
- Optional TradingView visual supplement with strict disclaimer and no use in calculations.
- Provider capability and quality snapshot patterns.

## Rejected concepts

- AGPL source reuse from OpenStock, WorldMonitor, OpenAlice, and OpenBB.
- MongoDB/Auth migration.
- React/Next.js/Tauri/Vite frontend migration.
- Live trading, broker connection, order routing, or approval-to-trade workflow.
- Mandatory OpenBB or paid provider dependency.
- Email automation, push notifications, background daemons, or scheduler services.
- Scraped/public-preview feeds presented as official live data.
- External plugin installation or vendoring.
- Full Options Lab or Quant Model Library implementation.

## Mapping to Goal 11

- OpenStock -> watchlist model, alert UX, quick add, TradingView supplement, report workflow inspiration.
- bloomberg-terminal -> compact research cards, market table UX, keyboard help, RMI/volatility and source freshness cards.
- BB-Terminal -> command palette and function registry vocabulary.
- WorldMonitor -> OSINT/event/chokepoint/country/provider caveat patterns.
- OSIRIS -> event feed, intel feed, map-first linking and view preset concepts.
- OpenAlice -> workspace/inbox/guard/review and Strategy-as-Git concept translation.
- OpenBB -> optional provider metadata and Provider Health Report memory.
- optlib -> future option snapshot attachment schema only.
- quant-traderr-lab -> future quant model snapshot attachment schema only.
- agent-skills-main -> engineering governance gates only.

## No source-code-copy statement

No external source code was copied into Goal 11. All Goal 11 modules are original Python/Streamlit/SQLite implementations written for this project. External repositories remain reference-only and are excluded from release packages.

## Implementation decisions derived from research

1. Use local SQLite under `data/private/research_workspace.db` rather than MongoDB/Auth/cloud storage.
2. Use manual/button-triggered alert/report generation only.
3. Treat TradingView as optional visual supplement, never as a data source for calculations, reports, data-quality scoring, or backtests.
4. Store source snapshots, provider gaps, freshness, and confidence in reports and alert events.
5. Keep Strategy-as-Git as a research decision log with guard results, not a trade approval system.
6. Keep future Options/Quant Lab hooks as lightweight attachment schemas only.

