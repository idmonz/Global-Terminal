# Phase 5F Design System Specification

Updated: 2026-06-19

## Design Read

Reading this as a high-frequency research workstation for serious individual investors, with a quiet institutional terminal language, high information density, strong source truth, and restrained motion.

Design dials:

- Design variance: 4/10
- Motion intensity: 2/10
- Visual density: 8/10

## Principles

1. The market object is always the first-viewport signal.
2. Provenance is visible but does not consume the main analytical canvas.
3. Dense does not mean crowded: each region has one job.
4. Color encodes state or market movement, not decoration.
5. Charts, maps, tables, and reports are real components, not fake preview rectangles.
6. Every loading, empty, stale, unavailable, and error state is designed.

## Semantic Tokens

```css
--bg-app: #0b0d10;
--bg-panel: #12161b;
--bg-elevated: #191f26;
--line-subtle: #29313a;
--text-primary: #f1f5f9;
--text-secondary: #9ba8b7;
--accent: #22c7b8;
--positive: #3ecf8e;
--negative: #f05d6c;
--warning: #e5ad45;
--info: #5aa7ff;
--unavailable: #7e8792;
```

Status colors and return colors are separate token families. Do not use red/green for unrelated UI decoration.

## Typography

- UI: system sans or one licensed neutral sans.
- Numeric/data: tabular numerals; monospace only for commands, IDs, timestamps, and compact status rows.
- Page title: 20-28px; panel title: 13-18px; table/data: 11-14px.
- Letter spacing: 0; no negative tracking.
- Numbers align by decimal or tabular width where comparison matters.

## Layout

Desktop shell:

- 44-52px top command/context bar;
- 56-72px icon workspace rail or 180-220px expanded rail;
- flexible primary canvas;
- 300-380px contextual rail when needed;
- optional bottom status tape.

The current permanent text-heavy left rail should evolve into grouped icon navigation with labels/tooltips and a workspace switcher. Long contract inventories move to Settings/Diagnostics.

## Component Inventory

- Symbol search and command palette.
- Context bar with symbol, exchange, as-of, runtime, and provider.
- Watchlist table.
- Market tape.
- Finance chart with timeframe/indicator controls.
- Heatmap with metric switcher and inspector.
- Full-bleed map with layer/timeline controls.
- News/event tape with source and age.
- Fundamentals table and compact KPI strip.
- Options chain/surface/Greeks panels.
- Provider health drawer.
- Research report reader and source register.

Cards are used only for repeated entities or genuinely framed tools. Page sections use bands, split panes, tables, and dividers.

## Visualization Rules

### Charts

- Stable height and aspect constraints.
- Wait for renderer readiness before visual success.
- Source, interval, timezone, as-of, units, and delayed/stale state visible.
- Crosshair and tooltip values must fit narrow viewports.
- Native fallback must be nonblank and semantically equivalent.

### Heatmaps

- Area and color metrics explicitly labeled.
- Neutral midpoint and accessible legend.
- Hover/focus inspector; keyboard-accessible tiles.
- Click preserves symbol and universe context.

### Maps

- Map is full-bleed inside the analytical pane, not a decorative card.
- Layer controls use checkboxes/toggles and counts.
- Markers cluster by zoom and expose source/confidence.
- Timeline changes visible markers; compare state is permalinkable.
- Base map attribution remains visible.

## Interaction

- Commands and direct manipulation lead to the same canonical routes.
- URL contains selected symbol, timeframe, tab, and map state where practical.
- Loading uses layout-shaped skeletons.
- Provider failure never silently swaps to fixture; fallback state is visible.
- Motion is limited to feedback, state transitions, and live-update emphasis.

## Responsive Behavior

- Under 768px, primary content remains before diagnostics.
- Navigation becomes a compact bottom or top workspace switcher.
- Right rail becomes a drawer.
- Dense tables use column priority and horizontal scroll, not crushed text.
- Map and chart retain stable minimum height.
- No toolbar or text overlap at 390px width.

## Accessibility

- WCAG AA contrast.
- Visible focus rings.
- Keyboard control for nav, heatmap, timeline, tabs, chart controls, and tables.
- Text alternatives and tabular equivalents for visualizations.
- Do not encode direction or status by color alone.
- Respect reduced motion.

## Mandatory Visual Verification

1. Start the production build or stable dev server.
2. Capture 1440x1000, 1280x800, 768x1024, and 390x844.
3. Wait for chart/map readiness markers.
4. Assert nonblank chart/map pixels or renderer DOM/canvas state.
5. Inspect top, middle, and bottom of long mobile pages.
6. Test hover/focus/selected/loading/empty/stale/error states.
7. Compare against the chosen benchmark behaviors.
8. Save screenshots and a short mismatch report.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
