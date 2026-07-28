# Phase 5I External Evidence Ledger

Updated: 2026-06-20

| Reference | Exact evidence | License stance | Observed behavior | Adopted clean-room behavior | Rejected |
|---|---|---|---|---|---|
| FinanceDatabase | `FinanceDatabase-main/LICENSE` | MIT | Copyright and permission verified | License evidence only | No source copied |
| FinanceDatabase | `FinanceDatabase-main/financedatabase/Equities.py` | MIT, direct adaptation possible after review | Multi-field country/sector/industry/currency/exchange/MIC/market-cap selection and option discovery | First-party URL-backed sector/freshness/search/sort filters over project-owned rows | No external database rows, class code, validation text, or compressed assets copied |
| OpenBB | `OpenBB-develop/openbb_platform/core/openbb_core/provider/standard_models/equity_screener.py` | AGPL-3.0, behavior-only | Provider-neutral symbol/name screener model | Provider-separated JSON contract with source register | No model/source import or copied Pydantic definitions |
| OpenBB | `OpenBB-develop/openbb_platform/core/openbb_core/provider/standard_models/index_constituents.py` | AGPL-3.0, behavior-only | Normalized uppercase symbol plus optional name | Canonical uppercase symbol identity | No source copied |
| Finviz | public product behavior benchmark | proprietary behavior-only | Dense sector hierarchy, size/color market map, click-through | First-party flex hierarchy, documented size/color metrics, selected instrument | No screenshot, CSS, branded palette, or proprietary data copied |
| TradingView/Koyfin/Bloomberg | public product behavior benchmark | proprietary behavior-only | Search/sort/compare continuity and compact source-aware workstation flow | URL persistence, compare tray, scatter, selected context | No branded assets, widgets, proprietary data, or distinctive pixel layout copied |

## Acceptance Boundary

The implementation is first-party React/CSS/Python. FinanceDatabase informs filter taxonomy only. OpenBB remains behavior-only. Runtime rows come from the existing yfinance path and local project registry, not external archive datasets.

