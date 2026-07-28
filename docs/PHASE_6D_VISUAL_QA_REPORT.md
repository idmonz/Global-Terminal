# Phase 6D Visual QA Report

Updated: 2026-07-02

## Method

The bundled in-app browser was initialized as required but no `iab` target was
available. The repository Playwright Core harness launched local Chrome against
a production Next.js build and a dedicated FastAPI/private SQLite runtime.

`apps/web/scripts/capture-phase6d.mjs` covers online, unknown-symbol failure,
network-blocked offline, desktop, and mobile states.

## Online Evidence

- five rows visible in stable order: AAPL, TSLA, JNJ, TTE, TMUS;
- initial AAPL/TSLA and clicked JNJ exact selections passed;
- chart state ready with seven canvas layers;
- financial state present, five exact news rows, five source-ledger rows;
- materialization status completed, provider calls 1/5;
- private reason absent from DOM and URL;
- unknown symbol did not mutate the list or fall back to Apple;
- no page-level horizontal overflow or unexpected browser/page errors.

## Offline Evidence

Browser routing blocked all symbol-workstation requests:

- deterministic five-symbol list remained usable;
- chart stayed unavailable with zero canvas and zero loaded bytes;
- the UI stated that the exact panel was unavailable;
- no fake current price, live chart, or materialization claim appeared;
- desktop and mobile overflow checks passed.

## Inspected Captures

- `review_workspace/phase6d_visual_online/watchlist-desk-online-desktop.png`
- `review_workspace/phase6d_visual_online/watchlist-desk-online-mobile.png`
- `review_workspace/phase6d_visual_online/watchlist-desk-unknown-symbol.png`
- `review_workspace/phase6d_visual_offline/watchlist-desk-offline-desktop.png`
- `review_workspace/phase6d_visual_offline/watchlist-desk-offline-mobile.png`

The desktop layout reads as a dense terminal rather than a card wall. Mobile
stacks list, exact identity, tabs, chart, job health, and local organization.
Responsive chart height was fixed after visual inspection; the final gate
measures the canvas-to-operations gap directly.

