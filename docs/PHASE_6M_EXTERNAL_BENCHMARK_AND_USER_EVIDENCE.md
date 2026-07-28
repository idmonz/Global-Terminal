# Phase 6M External, Benchmark, And User Evidence

Updated: 2026-07-13

## Complete Archive Gate

The deterministic audit was run at phase entry and again before release over
all 28 required archives. Final artifacts are under
`review_workspace/external2_analysis/phase6m-final/`.

- 28 archives and 24 feature candidates;
- 18 direct-use-allowed, 6 behavior-only, 3 needs-review, 1 blocked;
- generated inventory, license matrix, line inventory, and feature candidate
  documents were read before the next-phase decision.

AGPL OpenBB, OpenAlice, OpenStock, OctoBot, and WorldMonitor; NASA worldview;
missing-license BB-Terminal; and mixed/unclear paths remain behavior-only or
blocked. No external code, screenshot, dataset, font, or visual asset was copied.

## Current Benchmark Comparison

- TradingView watchlists join sortable symbol context, details, news, and
  watchlist-scoped alerts. Global Terminal now joins saved changes and exact
  evidence, but intentionally keeps external delivery unavailable:
  <https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/>
- OpenBB treats source metadata, parameters, and linked widgets as first-class.
  Attention rows similarly retain source and clocks, but do not yet offer a
  user-composed widget canvas:
  <https://docs.openbb.co/workspace/analysts/widgets/overview>
- Koyfin provides watchlist-wide document alerts and routes notifications to
  the originating document. Global Terminal now matches the exact-evidence
  return behavior locally while reducing delivery pressure:
  <https://www.koyfin.com/help/release-notes/v3-66-desktop-alerts/>
- Finviz discovery emphasizes compact rank/filter signals. Attention applies
  compact deterministic rank factors after materiality and source-health gates:
  <https://finviz.com/help/screener>
- WorldMonitor combines map/news layers, URL state, cache/fallback controls, and
  health truth. Its AGPL source remains behavior-only:
  <https://github.com/koala73/worldmonitor/blob/main/ARCHITECTURE.md>

## User Problem Decision

Current and recurring user evidence reports growing watchlists becoming
information overload, time lost across multiple products, cumbersome alert
logs, repetitive reanalysis, and the need to distinguish market change from a
broken or stale feed:

- <https://www.reddit.com/r/stocks/comments/x7cq4c>
- <https://www.reddit.com/r/TradingView/comments/1stnr1w/>
- <https://www.reddit.com/r/algotrading/comments/1uoo22x/>

The product inference is that one bounded review queue with source health,
checkpoints, dedupe, snooze, and exact return paths is more useful than another
push stream. Phase 6M implements that inference. Phase 6N must improve the truth
and timeliness of the saved observations feeding the queue.

## Harness Evidence

The current official Codex guidance says large prompts should specify Goal,
Context, Output, Boundaries, and verification, and recommends `/plan` before a
persistent `/goal`. The next prompt follows that structure:

- <https://learn.chatgpt.com/docs/prompting#goal-mode>
- <https://learn.chatgpt.com/docs/reference/slash-commands>
