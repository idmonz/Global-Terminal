# Phase 5F Web Benchmark Research Report

Updated: 2026-06-19

## Method And Limits

Official/product pages were fetched on 2026-06-19 where access allowed. OpenBB, TradingView, Finviz, and WorldMonitor content was readable. NASA Earthdata returned an edge error and Bloomberg returned a robot challenge, so those two were supplemented by the user-provided screenshots and local external documentation. No paywall or access control was bypassed.

## Benchmarks

### OpenBB Workspace

Official page: [OpenBB Workspace](https://openbb.co/products/workspace)

Observed product ideas:

- interactive dashboards and reusable widgets;
- proprietary and public data in the same workspace;
- contextual Copilot over the data the user is viewing;
- templates and connectors as first-class objects;
- emphasis on user-controlled infrastructure and data.

Adopt: configurable research workspaces, contextual source-bound AI, reusable widget contracts.

Do not copy: OpenBB AGPL code or branded visual assets.

### TradingView Advanced Charts / Supercharts

Official page: [TradingView Charting Library](https://www.tradingview.com/HTML5-stock-forex-bitcoin-charting-library/)

Observed product ideas:

- responsive high-volume chart engine;
- many chart types, 100+ indicators, drawing tools, event marks, overlays, scales, and synchronized layouts;
- watchlists, news, broker/datafeed extension points;
- explicit requirement for a real-time datafeed when real-time pricing is claimed.

Adopt: persistent symbol/timeframe context, event marks, synchronized chart/table panels, datafeed truth.

Do not copy: proprietary charting library unless separately licensed. The current MIT Lightweight Charts renderer is a narrower legal foundation.

### Finviz

Official page: [Finviz S&P 500 Map](https://finviz.com/map.ashx)

Observed product ideas:

- map, screener, charts, news, groups, portfolio, futures, forex, crypto, and calendar share one navigation model;
- delayed quote disclosure is visible;
- the market map is an analytical object with symbol drilldown rather than decorative color tiles.

Adopt: hierarchical heatmap, screener-to-symbol flow, visible delay/source status.

Do not copy: proprietary map data, styling, or content.

### WorldMonitor

Official project: [WorldMonitor](https://github.com/koala73/worldmonitor)

Observed public documentation:

- 500+ curated feeds across 15 categories;
- dual globe/flat-map engine and 56 layer types;
- finance radar across exchanges, commodities, and crypto;
- 65+ providers and freshness monitoring;
- missing credentials produce a credentials-required state instead of synthetic output.

Adopt: map/news/provider fusion, explicit layer health, product variants by domain, truthful missing-credential behavior.

Do not copy: AGPL code, CSS, datasets, textures, screenshots, or branded assets.

### NASA Worldview

Official product: [NASA Worldview](https://worldview.earthdata.nasa.gov/)

Evidence source: user screenshot plus local `worldview-main` compare/timeline/layer documentation.

Adopt: layer catalog, date timeline, opacity, swipe/compare, permalinkable map state.

Do not copy: NASA-licensed source or assets pending legal review.

### Bloomberg Terminal

Official product: [Bloomberg Terminal](https://www.bloomberg.com/professional/products/bloomberg-terminal/)

Evidence source: product identity, user benchmark image, and public product behavior.

Adopt: keyboard-first commands, persistent context, dense but predictable navigation, integrated market/news/research workflow.

Do not copy: branding, mnemonic sets as a wholesale clone, data, visual assets, or proprietary behavior requiring licensed feeds.

## Product Synthesis

The Global Terminal should not be a clone of any one product. Its defensible combination is:

- Finviz-style cross-sectional discovery;
- TradingView-style chart and symbol continuity;
- OpenBB-style provider openness and workspace composition;
- WorldMonitor/worldview-style spatial intelligence;
- Bloomberg-like keyboard speed and dense research context;
- explicit provenance and free-first runtime modes as a differentiator.

## Design Research Rule

Before each product slice:

1. select two primary benchmarks and one contrast benchmark;
2. state the behavior being adopted;
3. state what is intentionally not copied;
4. capture or inspect the current benchmark and current local screen;
5. implement and compare the actual desktop/mobile result;
6. log remaining mismatch.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
