# Phase 6H Visual QA Report

Updated: 2026-07-03

## Production Evidence

Production Chrome was run against `http://127.0.0.1:3053`.

Evidence directory:

`review_workspace/phase6h_visual/`

Key captures:

- `analyst-workspace-desktop.png`: 1600x1000, useful chart plus three
  simultaneous complementary panes and change/action rail.
- `analyst-workspace-live-aapl.png`: revalidated 62-row yfinance chart,
  financial metrics, stale catalyst truth, and source ledger.
- `analyst-workspace-mobile.png`: 390x844, one selected panel and one
  user-triggered secondary request.
- `analyst-layout-restored.png`: local split restored to 64%.
- `analyst-symbol-timeframe-synchronized.png`: AAPL to TSLA exact switch and
  one linked chart request for the interval change.
- `change-to-analyst-workspace.png` and
  `analyst-returned-change-inbox.png`: exact saved-change round trip.
- `analyst-unknown-symbol.png`: no AAPL leakage.
- `analyst-panel-lkg.png`: failed refresh retains exact saved chart.
- `analyst-slow-secondary-stable.png`: slow financial request causes no chart
  pane movement.

## Assertions

- useful chart nonblank: passed;
- four simultaneous desktop evidence panes: passed;
- no document horizontal overflow: passed;
- no console or page errors: passed;
- duplicate IDs: zero;
- unlabeled controls: zero;
- visible focus: passed;
- mobile hidden-panel requests before action: zero;
- background RSC prefetch: zero;
- source/freshness/caveat visible: passed;
- exact identity maintained through symbol/timeframe/change journeys: passed.

The first desktop screenshot exposed an unbounded 1,865px grid row and narrow
source-text overlap. The final layout constrains the research deck to 600px in
the measured viewport, scrolls panels internally, and wraps provenance text.
An early live screenshot was also taken before secondary panes settled; the
final harness waits for every default pane to reach ready or LKG state.

