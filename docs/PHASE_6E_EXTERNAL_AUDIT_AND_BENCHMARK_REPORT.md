# Phase 6E External Audit And Benchmark Report

Updated: 2026-07-03

## External Boundary

The deterministic audit covered all 28 required archives and wrote evidence to
`review_workspace/external2_analysis/phase6e`.

- license disposition: 18 direct-use allowed, 6 behavior-only, 3 needs review,
  1 blocked;
- external code, screenshots, datasets, fonts, and trade dress were not copied;
- AGPL, NASA, and unclear-license references remain behavior-only.

## Official Benchmark Review

- TradingView advanced watchlists:
  https://www.tradingview.com/support/solutions/43000771546-watchlist-advanced-view-mode/
- TradingView watchlist workflow:
  https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/
- OpenBB linked widget parameters:
  https://docs.openbb.co/workspace/analysts/widgets/interacting-with-data
- OpenBB widget model:
  https://docs.openbb.co/workspace/analysts/widgets/overview
- Next.js lazy loading:
  https://nextjs.org/docs/app/guides/lazy-loading
- Next.js server/client components:
  https://nextjs.org/docs/app/getting-started/server-and-client-components

## Clean-Room Behaviors Adopted

| Reference behavior | Phase 6E implementation |
|---|---|
| Symbol summary before deep analysis | compact server summary plus client panel delivery |
| Price/Performance/Risk/Financial/Technical list modes | cache-only Watchlist view modes |
| Sort and group without changing list order | temporary client sort/group state |
| Linked ticker/timeframe context | URL-backed exact symbol, interval, range, panel, compare |
| Self-contained source-aware widget | every panel retains provider/status/time/gap |
| Lazy optional analysis | chart-core first; technicals/financial/news/source on selection |

No benchmark-grade claim is made. TradingView drawing/alert breadth, OpenBB
arbitrary widget composition, and Bloomberg-class data depth remain open.

## Further Clean-Room Use

- OpenStock and yfinance: provider/cache behavior and failure classification;
- FinanceDatabase: taxonomy and identifier schema, never copied dataset rows;
- zipline: event-clock and point-in-time testing behavior;
- OctoBot: provider health and bounded task-state behavior, not execution;
- superloopy/agent-skills: evidence-driven implementation/review loops;
- OpenBB: linked parameters and source-aware widget metadata, behavior-only
  where the archive license boundary requires it.

Phase 6F should convert these behaviors into one bounded research snapshot,
rather than creating another visual shell.
