# Goal 11C Spec

## objective

Productize the Personal Research OS so the daily research workflow is navigable, reviewable, source-labeled, and visibly caveated without changing the project stack.

## non-goals

No rewrite, no frontend migration, no external runtime dependency, no copied external source, no execution workflow, no automatic background process, no Options/Quant Model Lab.

## required product surfaces

1. Shared visual components: cards, chips, compact metrics, empty states, methodology payloads.
2. Command palette UX: object resolver, suggestions, quick-add payloads, result cards.
3. Watchlist: action cards, source strip, product table columns, detail panel, news/event grid, alert builder, market context tabs.
4. Report Inbox: filter/sidebar/reader/review/source-caveat/export workflow.
5. Strategy Decision Log: review queue, reader, guard dashboard, graph table, diff panel, artifact timeline.
6. OSINT: Intel Feed, Live Alerts, View Presets, Layer Panel, Hotspots, Locate payloads.
7. Research Tool Center: manual research-only tool catalog.
8. Source freshness/provider caveats across major pages.

## acceptance rules

Payloads must be testable without Streamlit runtime, internet, API keys, OpenBB installation, or external plugins. Low-confidence and inferred events must be labeled. Missing keys and historical-only sources must be explicit. Raw payloads remain behind expanders.
