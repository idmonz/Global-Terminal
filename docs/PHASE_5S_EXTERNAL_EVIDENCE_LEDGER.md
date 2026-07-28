# Phase 5S External Evidence Ledger

Updated: 2026-06-23

## Clean-Room Rule

External repositories and famous products are references for behavior and product expectations. Source, visual assets, proprietary layouts, datasets, screenshots, fonts, and trade dress are not copied unless exact licensing allows it and attribution/notice is handled.

## Product Benchmarks Used

- OpenBB Workspace: source-aware widgets as self-contained analysis units.
  Source: `https://docs.openbb.co/workspace` and `https://docs.openbb.co/workspace/analysts/widgets/overview`
- TradingView: symbol-first chart/watchlist workflow and dense market navigation.
  Source: `https://www.tradingview.com/features/`, `https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/`, and `https://www.tradingview.com/support/solutions/43000771546-watchlist-advanced-view-mode/`
- Koyfin: dashboard, watchlist, portfolio, and report-oriented research workflow.
  Source: `https://www.koyfin.com/help/topic/functionality/`, `https://www.koyfin.com/help/mywatchlists/`, and `https://www.koyfin.com/for-financial-advisors/investment-research-teams-cio/`
- Bloomberg Terminal: dense launchpad/command/workspace mental model.
  Source: `https://professional.bloomberg.com/products/bloomberg-terminal/` and `https://professional.bloomberg.com/products/bloomberg-terminal/charts/`
- WorldMonitor/worldview: map, event, layer, timeline, and source-context behavior.

## Adopted Behaviors In Phase 5S

| Reference | Adopted behavior | Native implementation |
|---|---|---|
| Bloomberg-like terminals | Command launchpad and compact terminal cockpit | `MarketTerminalCockpit`, `CommandLaunchpad`, product nav links |
| OpenBB Workspace | Data panels with source/freshness boundaries | Existing `phase_2b.v1` envelopes and source rails |
| TradingView/Koyfin | Market home to instrument workstation navigation | Product nav and canonical asset links |
| WorldMonitor/worldview | Map/news/risk should be visible from home | News/Risk cockpit card and War Map route link |
| Streamlit lab | Stock, crypto, options, map, news, daily brief concepts | Web product surfaces and route composition |

## Rejected Or Deferred

- No AGPL, NASA, unclear-license, or proprietary source copied.
- No external images, screenshots, fonts, templates, or product UI assets copied.
- No broker execution, trading commands, target prices, stop-losses, position sizing, or order routing.
- AIS, verified flights, sanctions, and premium layers remain unavailable unless a verified provider succeeds.

## Phase 5T Required Evidence

Phase 5T must add targeted semantic line-level notes for the exact external features being reimplemented:

- map interaction and event/news linking;
- chart and symbol workstation interaction;
- options analytics visualization;
- terminal command routing and history;
- Streamlit page-to-web parity gaps.
