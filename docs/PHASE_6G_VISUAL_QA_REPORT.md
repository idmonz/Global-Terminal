# Phase 6G Visual QA Report

Updated: 2026-07-03

## Production Browser Proof

Production Next.js and FastAPI were exercised through headless Chrome using
`apps/web/scripts/capture-phase6g.mjs`.

Passed scenarios:

- desktop Change Inbox;
- 390 px mobile selected change before the long symbol/operations rails;
- event and severity filtering with URL persistence;
- explicit filtered-empty state;
- AAPL event -> exact Catalyst panel -> stateful return;
- API-offline saved before/after evidence;
- preview-only delivery and disabled background status.

Assertions:

- six deterministic fixture changes across two symbols;
- zero provider requests during inbox use;
- no horizontal overflow;
- no console or page errors;
- no duplicate IDs;
- no unlabeled controls;
- visible keyboard focus;
- exact change ID, list, filter, symbol, and panel restored after return.

Primary captures:

- `review_workspace/phase6g_visual/change-inbox-desktop.png`
- `review_workspace/phase6g_visual/change-inbox-mobile.png`
- `review_workspace/phase6g_visual/no-matching-change.png`
- `review_workspace/phase6g_visual/change-event-exact-catalysts.png`
- `review_workspace/phase6g_visual/change-inbox-returned.png`
- `review_workspace/phase6g_visual/offline-saved-change-evidence.png`

The desktop and mobile captures were personally inspected. The desktop surface
keeps scan rows, evidence, and operation truth visible without overlap. Mobile
places the selected evidence first and preserves readable controls and source
labels.

## Regression Proof

- Phase 6E online production capture passed for AAPL desktop, TSLA mobile,
  advanced Watchlist, and unknown symbol.
- Phase 6F production capture passed for Catalyst desktop/mobile, exact return,
  HTTP 429/LKG, and API-offline saved snapshot.

