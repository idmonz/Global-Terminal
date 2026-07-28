# Phase 6M Visual QA Report

Updated: 2026-07-13

## Method

The in-app Browser was unavailable after the required discovery check. The
repository production Chrome harness was used:

```powershell
npm --prefix apps/web run visual:phase6m
```

Machine evidence is in `review_workspace/phase6m_visual/summary.json`. Every
final image was directly inspected, including the formerly suspect Account B
and version-conflict captures.

## Final Evidence

- desktop: 9 visible rows, 168px ProductNav, no overflow, duplicate IDs,
  unlabeled controls, console/page errors, hidden requests, or provider calls;
- 390px: no page overflow, digest/source truth/queue visible, first high row at
  y=787, and zero hidden requests;
- source-degraded, no-material-change, reviewed, acknowledged, snoozed,
  expired/recovery, checkpoint, conflict, account-offline, and local states;
- exact Analyst, News, Daily Brief, and War Map drilldown plus stateful return;
- Account A review, Account B isolation, and account API outage continuity;
- Analyst, Operations, Watchlist, and Daily Brief regression views.

Primary captures:

- `attention-daily-review-desktop.png`
- `attention-daily-review-mobile.png`
- `attention-daily-review-mobile-tall.png`
- `attention-source-degraded.png`
- `attention-no-material-change.png`
- `attention-account-b-isolated.png`
- `attention-version-conflict.png`
- `attention-account-offline-local-retained.png`

This is product-state proof, not a benchmark-parity claim. Fixture captures are
explicitly labeled fixture evidence.
