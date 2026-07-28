# Phase 5T Streamlit-To-Web Parity Table

Updated: 2026-06-24

## Purpose

Streamlit remains the internal lab and regression reference. The commercial product direction is Next.js over reusable `lib/` contracts and optional FastAPI routes. This table tracks whether Streamlit-era concepts are now actually visible and useful in the web product.

| Streamlit/lab concept | `lib/` engine or contract | Web route | Visual status after 5T-B | Remaining blocker | Priority |
|---|---|---|---|---|---|
| Market overview | market map, symbol, daily brief, provider contracts | `/` | Strong cockpit visible; final QA shows 12 nav links and 24 chart surfaces | Downstream routes still uneven | Medium |
| Stock symbol analysis | `symbol_workstation`, `symbol_intelligence` | `/?view=asset&symbol=AAPL&assetClass=equity` | Usable with charts and source context | TradingView-like financials/earnings/estimates/options/news side rail still incomplete | High after map |
| Crypto symbol analysis | `symbol_workstation`, crypto derivatives context | `/?view=asset&symbol=BTCUSDT&assetClass=crypto` | Improved in 5T-A; cache miss and provider error no longer look broken | Broader intervals, more exchange/source breadth, deeper derivatives panels | Medium |
| Options analytics | `options_quant_contract` and related quant engines | `/?view=options-quant&symbol=AAPL` | Improved in 5T-B; first view shows IV smile, Greeks, exposure and payoff/scenario panels on desktop/mobile | OPRA-grade provider breadth, richer term/surface interaction and licensed quote timestamps | Medium |
| News intelligence | news intelligence, live feeds, map/news fusion | `/?view=news` | Improved in 5T-B; dedicated product workspace with filters, clusters, source rail, selected row, impact matrix and honest empty state | More live public sources, stronger Korean/global desk depth and map/asset routing | Medium |
| Global risk map | `war_room_map`, historical replay, map/news fusion | `/?view=war-room-map` | Map visible; final QA shows 2 map surfaces | WorldMonitor/worldview-style first-viewport map/news/layer/source co-presence | Highest for 5U |
| Market discovery | market map/screener contracts | `/?view=market-map` | Usable bounded screener/heatmap | Full universe, formulas, richer factors, hosted saved screens | Medium |
| Daily brief | daily brief, claim ledger, source register | `/?view=daily-brief` | Usable MVP with chart panels and source drawer | Delivery, broader macro/rates/commodity/Korean depth | Medium |
| Research memory | local-private notes/watchlists/reports | `/?view=research-memory` | Usable local-first workflow | Hosted sync, auth, alerts, attachments | Later |
| Portfolio risk | portfolio/risk engines | `/?view=portfolio-risk` | Useful fictional demo and risk panels | Arbitrary private input, broker sync, multi-currency cash flows | Later |
| Command terminal | `command_workspace` | `/?view=command-workspace` | Product shell visible with 19 command rows | Real command history, multi-window terminal, richer route actions | Medium |
| Provider center | provider health/contracts | `/?view=provider-health` | Useful transparency route | Operational observability and account/provider management | Later |

## Phase 5T-B Conclusion

The most visible 5T-A route defects are now closed:

- BTCUSDT first-run cache/provider failure no longer creates a broken chart.
- Options no longer opens as only a weak table/contract route.
- News no longer opens as a generic fixture viewer.

The next highest-value work is the War Map, because the user explicitly expects WorldMonitor/worldview-style map/news/layer interaction and the current map route still does not match that density.

Outputs remain research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, autonomous monitoring, or execution instructions.
