# Phase 5U Streamlit-To-Web Parity Table

Updated: 2026-06-30

## Purpose

Streamlit remains the internal lab and regression reference. The commercial direction is still Next.js over reusable `lib/` contracts and optional FastAPI routes. Phase 5U updates the visible parity status after the War Map first-viewport rebuild.

| Streamlit/lab concept | `lib/` engine or contract | Web route | Visual status after 5U | Remaining blocker | Priority |
|---|---|---|---|---|---|
| Market overview | market map, symbol, daily brief, provider contracts | `/` | Strong cockpit visible | Downstream depth still uneven | Medium |
| Stock symbol analysis | `symbol_workstation`, `symbol_intelligence` | `/?view=asset&symbol=AAPL&assetClass=equity` | Usable with charts and source context | TradingView-like financials, earnings, estimates, options and watchlist side rail still incomplete | Highest after 5U |
| Crypto symbol analysis | `symbol_workstation`, crypto derivatives context | `/?view=asset&symbol=BTCUSDT&assetClass=crypto` | Cache/provider failure no longer broken | More exchange/source breadth, intervals, derivatives and crypto-specific intelligence | High |
| Options analytics | options quant engines | `/?view=options-quant&symbol=AAPL` | Useful first-view analytics | OPRA-grade provider breadth and richer term/surface interaction | Medium |
| News intelligence | news intelligence, live feeds, map/news fusion | `/?view=news` | Dedicated workspace with clusters/source context | More live public sources and Korean/global desk depth | Medium |
| Global risk map | `war_room_map`, replay, map/news fusion | `/?view=war-room-map` | Improved in 5U: map starts at 391px desktop and 550px mobile; layer/source/inspector/event context visible | More live layers, richer event density, weather/AIS/flight/sanctions and hosted snapshots | Medium |
| Market discovery | market map/screener contracts | `/?view=market-map` | Usable bounded screener/heatmap | Full universe, formulas, richer factors, hosted saved screens | Medium |
| Daily brief | daily brief, claim ledger, source register | `/?view=daily-brief` | Usable MVP with chart panels and source drawer | Delivery and broader macro/rates/commodity/Korean depth | Medium |
| Research memory | local-private notes/watchlists/reports | `/?view=research-memory` | Usable local-first workflow | Hosted sync, auth, alerts, attachments | Later |
| Portfolio risk | portfolio/risk engines | `/?view=portfolio-risk` | Useful fictional demo and risk panels | Arbitrary private input, broker sync, multi-currency cash flows | Later |
| Command terminal | `command_workspace` | `/?view=command-workspace` | Product shell visible | Real command history, multi-window terminal, richer route actions | Medium |
| Provider center | provider health/contracts | `/?view=provider-health` | Useful transparency route | Operational observability and account/provider management | Later |

## Phase 5U Conclusion

The War Map first-viewport layout defect is improved. The next highest user-visible gap is the unified stock/crypto intelligence workstation: the web product still needs the Streamlit-era intelligence, stock analysis and crypto analysis ideas to appear as a richer TradingView/OpenBB-like symbol desk with charts, fundamentals, options, news, event links and source-aware widgets in one route.

Outputs remain research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, autonomous monitoring, or execution instructions.
