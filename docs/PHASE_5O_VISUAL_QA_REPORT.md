# Phase 5O Visual QA Report

Updated: 2026-06-22

## Method

The in-app Browser bootstrap was attempted first and failed because the current MCP request metadata lacked `sandboxPolicy`. Repository `playwright-core` with installed Chrome was then used against the production Next.js server.

The first run found a real React hydration mismatch in an SVG title. It was fixed by replacing parser-sensitive SVG title text with an accessible `aria-label`, then the full capture was rerun.

## Automated Evidence

`npm --prefix apps/web run visual:phase5o` passed with:

- fixture heatmap: 30 rows and 30 tiles;
- composable controls: 10 filters and 4 rank models;
- filtered mega-cap screen: 10 rows;
- ranked table: 10 matching rows;
- factor view: 10 attribution cards;
- local saved-screen API: create/list succeeded;
- live-if-available: 55 balanced-eligible rows from 60 source-backed market rows;
- desktop width: 1,368px inside a 1,600px viewport;
- mobile width: 358px inside a 390px viewport;
- desktop/mobile horizontal overflow: none;
- console errors: 0;
- page errors: 0.

## Inspected Captures

- `review_workspace/phase5o_visual/market-discovery-heatmap-desktop.png`
- `review_workspace/phase5o_visual/market-discovery-ranked-table.png`
- `review_workspace/phase5o_visual/market-discovery-factor-attribution.png`
- `review_workspace/phase5o_visual/market-discovery-mobile.png`
- `review_workspace/phase5o_visual/market-discovery-live-data.png`

Personal inspection confirmed:

- first-viewport filter and rank hierarchy is clear;
- live and fixture runtime boundaries are visually distinct;
- heatmap sizing and return colors remain readable;
- selected-symbol score contributions reconcile visibly;
- the desktop table is dense without compression;
- mobile control order, heatmap, evidence, scatter, comparison, and saved screens remain usable.

## Benchmark Comparison

- TradingView: comparable filter density, saved-screen concept, view tabs, and symbol continuity are now present; arbitrary universes and hundreds of filters remain absent.
- Finviz: the analytical heatmap and direct symbol continuity are present; zoom/pan and authoritative full-market breadth remain absent.
- OpenBB: factor/provider provenance is visible; user-composed arbitrary widgets remain absent.
- Bloomberg-like terminals: density and selected-context continuity improved; licensed data breadth, streaming, and command composition remain absent.
