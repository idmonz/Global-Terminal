# Phase 5P External Evidence Ledger

Updated: 2026-06-22

## Mechanical Audit

- archives: 22;
- files: 45,996;
- text candidates: 35,193;
- counted text lines: 9,561,357;
- indexed symbols: 221,593;
- read errors: 0.

Artifacts are under `review_workspace/phase5p_external_audit/`. This is mechanical indexing, not a claim that every line was manually understood.

## Scoped Semantic Review

| Reference | Exact evidence | License stance | Behavior observed | First-party adoption | Prohibited |
|---|---|---|---|---|---|
| worldview | `worldview-main/e2e/features/compare/timeline-test.spec.js` | NASA-1.3, behavior-only pending legal review | independently selectable A/B times and active comparison time | active and comparison snapshot IDs with bounded URL state | source, assets, imagery, CSS |
| worldview | `worldview-main/e2e/features/compare/permalinks-test.spec.js` | NASA-1.3, behavior-only | comparison state survives permalink navigation | allow-listed `time` and `compareTo` parameters | query format or implementation copying |
| worldview | `worldview-main/e2e/features/timeline/timeline-mobile-test.spec.js` | NASA-1.3, behavior-only | mobile date controls remain reachable | compact responsive snapshot-density strip | date-picker source or styles |
| WorldMonitor | `worldmonitor-main/docs/map-engine.mdx` | AGPL-3.0, behavior-only | shared layer catalog, time windows, URL state, fallback tiles and mobile gestures | layer health, bounded time state, explicit renderer fallback | source, map assets, layer data, branding |
| WorldMonitor | `worldmonitor-main/e2e/map-harness.spec.ts` | AGPL-3.0, behavior-only | deterministic map readiness, nonempty layers and visual baselines | first-party Chrome assertions for tiles, markers, viewports and errors | harness implementation or golden images |
| WorldMonitor | `worldmonitor-main/e2e/mobile-map-popup.spec.ts` | AGPL-3.0, behavior-only | popup remains in viewport and supports compact mobile interaction | stacked mobile evidence inspector | source/CSS copied |
| OpenBB | official Workspace docs, captured 2026-06-22 | public product and AGPL boundary | source-aware widgets and parameter context | provider/layer/source evidence retained across replay | source, branded visuals |

## Official Benchmark Captures

- `review_workspace/phase5p_benchmark/nasa-worldview.png`: HTTP 200, timeline/layers/events visible, zero page errors.
- `review_workspace/phase5p_benchmark/worldmonitor.png`: HTTP 200 public product page, source claims and dashboard preview inspected, zero page errors.
- `review_workspace/phase5p_benchmark/openbb-workspace.png`: HTTP 200 official docs, workspace/widget concepts visible, zero page errors.

No external source, CSS, screenshot, image, brand asset, provider payload or dataset was copied into the product.
