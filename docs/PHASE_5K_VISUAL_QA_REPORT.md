# Phase 5K Visual QA Report

Updated: 2026-06-21

## Browser Path

The mandatory in-app Browser bootstrap was attempted first and failed because the environment did not provide the required browser sandbox metadata. QA then used the repository-pinned `playwright-core` with installed production Chrome, as allowed by the phase contract.

The unstable Next 16 development Turbopack process produced repeated HMR panics during URL-tab interaction. This was not treated as a product pass. QA switched to a clean production build and `next start`; all final interaction checks passed there.

## Final Captures

- `review_workspace/phase5k_visual/portfolio-live-overview-desktop.png`
- `review_workspace/phase5k_visual/portfolio-live-correlation-desktop.png`
- `review_workspace/phase5k_visual/portfolio-live-stress-desktop.png`
- `review_workspace/phase5k_visual/portfolio-live-overview-tablet.png`
- `review_workspace/phase5k_visual/portfolio-live-overview-mobile.png`
- `review_workspace/phase5k_visual/portfolio-fixture-factors.png`

## Observed Evidence

- Desktop 1600x1000: seven holdings, 249 live/cache performance points, nonblank performance and drawdown polylines, visible allocation and risk context.
- Correlation: 36 rendered cells for six history assets, each with 249 pairwise samples.
- Stress: nine rendered rows, split into two historical replays and seven deterministic hypothetical scenarios.
- Tablet 768x1024: 567px product content, no horizontal overflow; runtime diagnostics are collapsed so analysis owns the first viewport.
- Mobile 390x844: 321px safe content width inside existing product gutters, 390px document width, nonblank charts, KPI/controls/tabs visible, no overlap.
- Fixture factors: four public proxy rows and model-fit context.
- Keyboard focus: visible solid outline.
- Browser console errors: zero.

## Defects Corrected

1. Unknown portfolio route fell through to Market contract diagnostics.
2. Correlation diagonal selected duplicate DataFrame columns.
3. React lint rejected render-time donut offset mutation.
4. Tablet runtime banner dominated the first viewport.
5. Initial mobile assertion mistook intentional safe gutters for overflow.
6. Signed formatting made volatility/allocation magnitudes look like returns.
7. Stale refresh cause was not promoted to the main data-gap list.
8. Development Turbopack HMR was unstable; production-server QA became authoritative.

## Verdict

Visual QA passed for production Next. The product is dense, readable, source-aware and responsive, but it is an internal beta rather than benchmark-grade portfolio software.

