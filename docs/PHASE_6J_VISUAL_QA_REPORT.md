# Phase 6J Visual QA Report

Updated: 2026-07-10

Production Chrome ran against web `127.0.0.1:3062` and API `127.0.0.1:8062`.
Screenshots were personally inspected.

## Passed Scenarios

- anonymous/local desktop and 390x844 mobile;
- Account A sign-in, explicit save, reload/navigation, and restore;
- real stale-version conflict with visible recovery guidance;
- sign-out and Account B isolation;
- blocked account API with browser-local layout retained;
- external Origin, unsafe redirect, traversal, and client tenant override;
- nonblank Analyst Workspace and chart throughout account states.

Desktop account state stays in one dense operations row. Mobile places
identity, sign-in action, and local/sync truth before the toolbar and chart.
Observed horizontal overflow was false at desktop and mobile widths. Expected
409/422 security probes were separated from unexpected browser errors; all
other console/page errors were zero.

Evidence:

- `review_workspace/phase6j_visual/summary.json`
- `review_workspace/phase6j_visual/account-anonymous-desktop.png`
- `review_workspace/phase6j_visual/account-a-saved.png`
- `review_workspace/phase6j_visual/account-a-version-conflict.png`
- `review_workspace/phase6j_visual/account-b-isolated.png`
- `review_workspace/phase6j_visual/account-anonymous-mobile.png`
- `review_workspace/phase6j_visual/account-api-offline-local-retained.png`
