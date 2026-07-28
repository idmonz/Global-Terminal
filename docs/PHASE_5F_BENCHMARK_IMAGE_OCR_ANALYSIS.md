# Phase 5F Benchmark Image And OCR Analysis

Updated: 2026-06-19

## Method

Five user-provided benchmark images under `external (2)/` were inspected at original resolution. `tesseract` was not installed, so this report is a manual visual reading, not machine OCR. No OCR accuracy claim is made.

## Image Findings

### `finviz.PNG` - 1920 x 1042

- Hierarchical sector, industry, and ticker treemap dominates the viewport.
- Tile area communicates relative size; red/green intensity communicates return.
- The result is an information object, not a decorative dashboard card.
- Filters, search, bubble mode, fullscreen, and sharing sit around the visualization.

Adopt: hierarchical group layout, metric switcher, legend, hover inspector, tile-to-symbol drilldown.

### `openbb.png` - 1400 x 795

- Resizable widget grid combines company profile, price chart, news, data connectors, and templates.
- A contextual Copilot rail is attached to the user's data surface rather than isolated as a chat page.
- Tabs and widget composition support repeated professional workflows.

Adopt: workspace layouts, reusable widgets, contextual assistant, source-bound generated answers.

### `tradingview.PNG` - 1920 x 1038

- Symbol context remains persistent while the user changes analytical views.
- Annual/quarterly controls and reported-versus-estimated bars are immediately legible.
- A watchlist remains visible beside the analytical canvas.
- Chart, event marks, metrics table, and symbol navigation form one workflow.

Adopt: persistent symbol context, synchronized chart/table states, right watchlist rail, direct timeframe controls.

### `worldmonoitor.PNG` - 1920 x 1035

- The map is the main canvas, not a small card.
- Layer toggles, markers, routes, country context, live news, finance, supply-chain, AI summaries, and threat timeline are spatially connected.
- The interface uses multiple dense bands but maintains clear ownership of each region.

Adopt: map-first layout, marker-linked news, layer health, timeline, provider status, regional context.

### `터미널 예시.png` - 1061 x 563

- A single-stock page concentrates a metric/score strip, large price chart, indicators, financial charts, reports, news, and valuation.
- It prioritizes the selected security and daily analysis over platform metadata.
- The density is high but each panel answers a concrete question.

Adopt: symbol-first page, compact summary strip, large primary chart, fundamentals/news/valuation side rail.

## Comparison With Current Web Product

The current web shell has the right dark terminal tone and information density, but it spends too much first-viewport space explaining fixture/runtime boundaries and summary metadata. Benchmark products spend that space on the user's object: market, symbol, map, chart, or report.

The next design rule is therefore:

> Put the market object first; keep provenance visible but secondary and inspectable.

## Visual QA Requirement

Every design slice must include:

1. benchmark/reference review before coding;
2. desktop and mobile screenshots after coding;
3. a wait-for-render assertion for charts and maps;
4. nonblank canvas or tile checks;
5. overlap, clipping, scroll, focus, and responsive checks;
6. a comparison table of intended behavior versus observed output.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
