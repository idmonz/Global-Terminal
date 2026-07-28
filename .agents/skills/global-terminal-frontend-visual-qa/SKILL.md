---
name: global-terminal-frontend-visual-qa
description: Render, capture, and inspect Global Terminal desktop and mobile web views. Use whenever UI, charts, maps, navigation, responsive layout, loading states, or benchmark-facing product surfaces change.
---

# Global Terminal Frontend Visual QA

## Workflow

1. Build and start the production Next.js app on an available local port.
2. Capture every route and viewport required by the active phase.
3. Wait for chart/map readiness markers before capture.
4. Assert charts/maps are nonblank using DOM/canvas state or pixel checks.
5. Inspect first viewport, long-page middle/bottom, keyboard focus, loading, empty, stale, unavailable, and error states.
6. Compare observed behavior with the selected benchmarks without pixel-copying them.
7. Record route, viewport, screenshot, pass/fail, defects, and follow-up in the visual QA report.
8. For every phase with a visible change, add or update a versioned
   `apps/web/scripts/capture-phase*.mjs`, expose it as `visual:phase*`, write a
   machine-readable `review_workspace/phase*_visual/summary.json`, and register
   the evidence in `docs/VISUAL_VERSION_REGISTRY.md`.
9. Measure navigation tracks, labels, controls, and long words at desktop and
   390px. A nonblank page with crushed, clipped, overlapping, or overflowing
   text is a visual failure.
10. Personally inspect the generated captures before writing the report.
11. Never convert a failed or missing capture into a pass.
