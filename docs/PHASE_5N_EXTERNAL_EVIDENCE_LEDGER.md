# Phase 5N External Evidence Ledger

Updated: 2026-06-22

## Audit Boundary

The full external archive audit was rerun into `review_workspace/phase5n_external_audit`:

- 22 archives;
- 45,996 files and 55,061 file/directory entries;
- 34,197 indexed non-vendored text/code files;
- 8,077,122 indexed lines;
- license stance: 13 direct-use-allowed, 5 behavior-only, 3 needs-review, 1 blocked.

Mechanical inventory is evidence coverage, not semantic clearance. Phase 5N semantically inspected only the paths needed for symbol intelligence.

## Adoption Decisions

| Reference | Exact evidence | Stance | Observed behavior | First-party decision |
| --- | --- | --- | --- | --- |
| OpenAlice | `OpenAlice-master.zip` / `src/domain/analysis/indicator/calculator.ts`; AGPL-3.0 | behavior-only | formulas retain data-range/provider provenance and separate data access from calculation | Project-native Python calculations publish formula version, minimum observations, and verified-history source rows; no source copied |
| bloomberg-terminal | `bloomberg-terminal-main.zip` / `components/bloomberg/views/news-view.tsx`; archive license needs review | behavior-only | compact source/time/link hierarchy and explicit loading/error/empty news states | First-party exact-title matching, provider time, source link, and empty state; no source/CSS copied |
| OpenBB/OpenAlice provider models | existing Phase 5F inventory; AGPL | behavior-only | source-aware financial/news panel composition | Existing provider/normalization/API separation retained; no provider source copied |
| TradingView public product | `docs/PHASE_5F_WEB_BENCHMARK_RESEARCH_REPORT.md` | behavior-only | chart-first hierarchy, intervals, candlesticks, volume, overlays, synchronized panes, persistent state | Existing MIT Lightweight Charts dependency generalized with first-party contracts and CSS |
| Finviz public product | existing benchmark report | behavior-only | compact symbol facts and source-linked symbol news | First-party metric tape, exact-title news, and discovery links |
| FinanceDatabase | `FinanceDatabase-main.zip`; MIT taxonomy evidence | schema behavior only | explicit equity/ETF/crypto identity | No external dataset row imported |
| yfinance archive/package | `yfinance-main.zip`; installed package path reviewed separately | dependency/public-adapter use | delayed OHLCV, public profile/statements/news access | Installed dependency used through project-native adapters; no external source copied |

## Prohibited Material

No external source, CSS, prompt, screenshot, brand asset, proprietary indicator default, dataset row, telemetry, paid payload, or market-data entitlement was copied. BB-Terminal remains blocked for direct use. External archives, audit output, caches, and screenshots remain excluded from release.

