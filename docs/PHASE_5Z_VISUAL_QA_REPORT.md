# Phase 5Z Visual QA Report

Updated: 2026-07-01

## Method

The in-app browser was attempted first and was unavailable. The repository's
Playwright Core harness used local Chrome as the permitted fallback:

`npm --prefix apps/web run visual:phase5z`

The harness asserts runtime truth, rows/tiles, hierarchy, metric changes, selected
symbol, workstation return, unknown-symbol isolation, overflow, console errors,
page errors, and screenshot size.

## Online Evidence

Directory: `review_workspace/phase5z_market_discovery_online_final/`

- 137 rows and 137 tiles;
- 131 broad official-listed observations;
- 137 listing identities and 60 taxonomy matches;
- 14 filters and 6 universe-truth cells;
- sector drilldown produced 17 Information Technology rows and 9 industry groups;
- equal-size/relative-volume encoding changed in place;
- AAPL opened a ready workstation and returned with query, selected symbol,
  hierarchy, size, and color state;
- unsupported `ZZZZ` showed an unavailable state without AAPL identity;
- desktop first tile top: 846 px;
- mobile map section top: 790 px;
- horizontal overflow, console errors, and page errors: zero.

## Offline Evidence

Directory: `review_workspace/phase5z_market_discovery_offline_final/`

- runtime explicitly offline with runtime fallback;
- 30 deterministic fixture rows;
- official observation/listing/taxonomy coverage claims: zero;
- hierarchy and size/color controls remain usable;
- offline AAPL fallback workstation and return state work;
- unsupported `ZZZZ` remains isolated;
- horizontal overflow, console errors, and page errors: zero.

## Personal Inspection

The final desktop, hierarchy, encoding, selected-symbol, workstation, cache, mobile,
and unsupported screenshots were opened and inspected. A clipped fourteenth desktop
filter was corrected with a seven-column/two-row layout. Mobile universe truth was
changed to a compact horizontal strip so the next map section is visible in the
first viewport.

## Residual Visual Gap

The layout is a useful dense internal beta, not a full Finviz squarified market map
or TradingView GPU-scale heatmap. The broad response still needs materialized
pagination/summary payloads before thousands of symbols are practical.
