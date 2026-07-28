# Phase 6E Performance Report

Updated: 2026-07-03

## Before And After

Warm local production, AAPL equity, `1d / 3mo`, cache mode:

| Metric | Phase 6D | Phase 6E | Result |
|---|---:|---:|---|
| direct asset document | 1,071,676 B | 56,112 B | 94.8% lower |
| summary API | 19,427 B | 19,445 B | compact boundary retained |
| chart delivery | 164,614 B | 69,659 B | 57.7% lower |
| direct document p50/p95 | 1,186/1,404 ms | 129.8/162.5 ms | pass |
| summary p50/p95 | 23.7/24.2 ms | 26.3/28.4 ms | pass |
| chart p50/p95 | 222/235 ms | 123.8/147.6 ms | pass |

Chrome useful-chart evidence:

- AAPL desktop: FCP 568 ms, useful chart 753 ms;
- TSLA 390px mobile: FCP 204 ms, useful chart 470 ms;
- final live-if-available: AAPL 772 ms, TSLA 463 ms;
- unrelated background RSC prefetches: 0;
- repeat direct and same-origin conditional chart request: 304, 0 bytes.

The main gain comes from eliminating the full fixture catalog and duplicate
history/indicator serialization, not from hiding provider latency.

## Live Truth Check

An independent current market lookup returned AAPL `308.63` and TSLA `393.45`.
Fresh `live-if-available` chart-core requests returned `308.6300048828125` and
`393.45001220703125` from yfinance, both labeled `live/fresh` with 62 rows.
The daily-bar market observation remains dated 2026-07-02 while retrieval is
dated 2026-07-03; these clocks are intentionally separate.

Cache-mode screenshots retained older values and labeled them `stale-cache`.
Fresh and cached evidence are not conflated.
