# Phase 5T External Evidence Ledger

Updated: 2026-06-24

## Clean-Room Boundary

External projects and famous products were used as behavior benchmarks only. No AGPL, NASA, missing-license, proprietary, or unclear-license source was copied. No external screenshots, datasets, visual assets, fonts, or trade dress were copied into the product.

The external archive inventory remains useful as an index, but full mechanical inventory is not the same as semantic review of every line. Each adoption slice still needs targeted review for the specific behavior being rebuilt.

## Phase 5T References Consulted

| Reference | Evidence used | Clean-room behavior adopted |
|---|---|---|
| TradingView support: watchlists | `https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/` | Product navigation should move from market discovery to instrument workstations without route hunting. |
| TradingView support: heatmaps | `https://www.tradingview.com/support/solutions/43000766446-tradingview-heatmaps-from-global-trends-to-details/` | Broad market views should drill into symbol-specific analysis surfaces. |
| User-provided TradingView reference image | `external (2)/tradingview.PNG` | Dense symbol route expectation: chart/table/financial/earnings/watchlist context should coexist. Used as a benchmark gap, not copied. |
| OpenBB Workspace docs | `https://docs.openbb.co/workspace` | Source-aware widgets should expose provider, parameters, metadata and context boundaries. |
| OpenBB widget interaction docs | `https://docs.openbb.co/workspace/analysts/widgets/interacting-with-data` | Widget-like product panels should make interaction state visible. |
| User-provided OpenBB reference image | `external (2)/openbb.png` | Multi-widget source-aware layout and context selection informed the Options/News panel approach. No visual assets copied. |
| NASA Worldview | `https://www.earthdata.nasa.gov/data/tools/worldview` | Map products should eventually support layer, time, compare and source inspection. Used for the next map phase. |
| User-provided WorldMonitor reference image | `external (2)/worldmonoitor.PNG` | Map/news/live/source co-presence is the next product benchmark for Phase 5U. No AGPL source or UI assets copied. |
| Bloomberg Terminal product page | `https://professional.bloomberg.com/products/bloomberg-terminal/` | Terminal screens should be dense, commandable and multi-panel rather than contract galleries. |
| Bloomberg Charts page | `https://professional.bloomberg.com/products/bloomberg-terminal/charts/` | Charts should remain embedded in the surrounding terminal context. |

## External Archive Notes

`external (2)/external` currently contains the refreshed reference set, including Supabase, Helix, FinanceDatabase, TradingAgents, yfinance, open-design and ruflo archives. The latest targeted review for Phase 5T used these as follows:

- OpenBB: behavior-only source-aware widget panels.
- WorldMonitor/worldview: behavior-only map/news/layer co-presence and timeline/compare standards.
- BB-Terminal/Bloomberg-like references: behavior-only terminal density and command navigation.
- FinanceDatabase/yfinance: taxonomy/provider inspiration only where already represented by first-party contracts and free-first providers.
- TradingAgents: analyst-role decomposition remains relevant to reports; trader/order/target/stop/sizing/execution semantics remain rejected.
- Supabase/Helix: future hosted persistence/graph-readiness references only; no hosted database or graph store was added in Phase 5T.

## Rejected Material

- No AGPL/NASA/missing-license source copied.
- No external screenshots, fonts, visual assets, market datasets or proprietary UI copied.
- No order execution, trader agent, target price, stop-loss, position sizing, broker workflow or autonomous monitoring.
- No fake live news, options, crypto or map provider state.

## Native Phase 5T Adoption

- Phase 5T-A adopted the commercial behavior that first-run routes should degrade honestly instead of showing broken charts.
- Phase 5T-B adopted the commercial behavior that Options and News should open as useful workspaces, not generic contract viewers.
- Phase 5U should adopt the commercial behavior that a War Room map must put events, layers, news, source states and market exposure in the same first working viewport.

Outputs remain research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, autonomous monitoring, or execution instructions.
