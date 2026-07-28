# Phase 6K Visual QA Report

Updated: 2026-07-10

## Method

The in-app Browser was requested first but no `iab` target was available. The
repository's production Chrome/Playwright-core harness then exercised the local
production Next/FastAPI pair with isolated review databases. Screenshots and
machine assertions are under `review_workspace/phase6k_visual/` and are excluded
from releases.

## Personally Inspected Captures

- `account-research-lazy-closed-desktop.png`
- `account-research-import-preview-desktop.png`
- `account-research-exact-evidence-desktop.png`
- `account-research-acknowledged-desktop.png`
- `account-research-acknowledged-mobile.png`
- `account-research-anonymous-mobile.png`
- `account-research-account-b-isolated.png`
- `account-research-signed-out.png`
- `account-research-api-offline-local-retained.png`

Desktop presents preview, account-owned exact symbols, and source-aware inbox
in one dense band before the existing chart/history. Mobile places account
identity, import action, and critical inbox rows before the long Watchlist
history. Observation clocks, source status, unavailable hosted persistence, and
unavailable external delivery remain visible.

## Assertions

- account calls before opening the lazy surface: 0;
- bounded preview candidates: 2; imported exact identities: 2;
- saved-change inbox rows: 3; final persisted state: acknowledged;
- kill switch: suppressed; expired rule: expired; conflict: 409;
- Account B watchlist/inbox reads: 404/404 and counts 0/0;
- desktop width 1,518 px and mobile width 376 px with no horizontal overflow;
- offline account API leaves local symbols, chart, and actions visible;
- Phase 6H Analyst Workspace and Phase 6I operations remain visible;
- no unexpected page/console errors in the primary journey.

The clean-room layout adopts scanning density, source-context visibility, and
compact research/review co-presence from the inspected benchmark categories;
no external source, asset, screenshot, font, or trade dress was copied.
