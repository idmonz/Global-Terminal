# Phase 5F Streamlit To Web Parity Matrix

Updated: 2026-06-19

Status vocabulary:

- `covered`: the main workflow is visible and usable on the web.
- `partial`: a web surface exists but important workflow or runtime data is absent.
- `schema-only`: contract/fixture/readiness exists without the real workflow.
- `missing`: no equivalent commercial web workflow.

| Streamlit source | Lab capability | Current web target | Status | Primary gap |
|---|---|---|---|---|
| `app.py` | Executive overview/navigation | Market Intelligence | partial | No useful daily home composition |
| `pages/1_Market_Pulse.py` | Cross-asset pulse | Market Intelligence | partial | Fixture-heavy, shallow live breadth |
| `pages/2_Stock_Analyzer.py` | Price, technical, fundamentals, scenarios, news | Equity Intelligence | partial | No URL symbol state; incomplete live runtime |
| `pages/3_ETF_Analyzer.py` | ETF comparison/analysis | none | missing | Dedicated ETF universe and holdings |
| `pages/4_Macro.py` | Macro series/regime/rates | Market Intelligence | partial | No dedicated macro chart workspace |
| `pages/5_Portfolio.py` | Portfolio state/optimization | none | missing | Holdings workflow and persistence |
| `pages/6_News.py` | News intelligence and impact | News / Map Fusion | partial | Weak entity drilldown and daily ranking |
| `pages/7_Global_Heatmaps.py` | Cross-asset heatmaps | Market heatmap | partial | Synthetic fixture, no live universe |
| `pages/8_Crypto_Intelligence.py` | Spot, derivatives, on-chain, scenarios | Crypto Intelligence | partial | Limited symbol state and live history |
| `pages/9_Energy_Geopolitics.py` | Energy/chokepoints/news/map | Map Fusion | partial | Mostly static/proxy shipping context |
| `pages/10_Scenario_Lab.py` | Scenario analysis | Research Report fragments | schema-only | Interactive scenario authoring absent |
| `pages/11_Risk_Lab.py` | Risk/stress analysis | none | missing | Dedicated risk workstation |
| `pages/12_Data_Quality.py` | Data quality diagnostics | Provider Health | partial | Product-level lineage drilldown absent |
| `pages/13_Screener.py` | Filters/ranking/results | Screener Drilldown | partial | No live screener/filter engine in web |
| `pages/14_War_Room.py` | Events, layers, map, reports | War Map / Map Fusion | partial | Sparse data, weak timeline/compare, weak visual proof |
| `pages/15_Financial_Terminal.py` | Company overview/statements/charts | Financial/Fundamentals | partial | Proxy metrics; full statements/provider absent |
| `pages/16_Portfolio_Quant_Lab.py` | Backtest, attribution, factors, stress | none | missing | Largest unported analytical surface |
| `pages/17_Data_Provider_Center.py` | Provider registry/health | Provider Health/Layers/Feeds | covered | Needs operational telemetry and retry controls |
| `pages/18_OpenBB_Data_Hub.py` | Optional provider/catalog workflow | Providers/Commands | schema-only | Optional OpenBB runtime not productized |
| `pages/19_Research_Workspace.py` | Research artifacts/workflows | Research Report | partial | No saved multi-document workspace |
| `pages/20_Watchlist_Alerts.py` | Watchlists and alerts | none | missing | User state, rules, notifications |
| `pages/21_Report_Inbox.py` | Report list/review/export | Research Report | partial | No inbox, history, search, persistence |
| `pages/22_Strategy_Decision_Log.py` | Decision/strategy history | none | missing | User research journal and audit trail |
| `pages/23_Research_Tool_Center.py` | Tool routing/actions | Command Workspace | partial | Mostly provider-gated/read-only outputs |
| `pages/24_Options_Quant_Model_Lab.py` | Pricing, Greeks, chains, surfaces, cases | Options/Quant | partial | Calculator works; live chain/GEX/surface workflow absent |

## Quantified Result

| Classification | Count |
|---|---:|
| covered | 1 |
| partial | 16 |
| schema-only | 2 |
| missing | 6 |
| total assessed surfaces | 25 |

This matrix supersedes the older `product-parity.json` summary, which predates Phase 5E.3 and only inventories nine Streamlit pages.

## Migration Priority

1. Market Home to Symbol Intelligence vertical journey.
2. Map-News-Event fusion with real map render proof and richer source-backed layers.
3. Portfolio Quant web workstation.
4. Watchlist, alerts, report inbox, and local research memory.
5. ETF, macro, scenario, and risk dedicated workspaces.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
