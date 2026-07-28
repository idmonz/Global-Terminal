# Phase 6P Visual QA Report

Updated: 2026-07-15
Evidence version: `phase6p.visual.v1`

## Reproduction

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6p_visual_handoff.ps1
```

The handoff selects free ports, starts production FastAPI/Next processes,
creates an isolated temporary account DB, captures and verifies the evidence,
then removes only the processes and temporary files it created.

## Accepted Captures

- `account-hosted-signin-desktop.png`;
- `account-continuity-restored-desktop.png`;
- `account-continuity-conflict-desktop.png`;
- `account-continuity-offline-desktop.png`;
- `account-continuity-restored-mobile.png`;
- `account-continuity-restored-mobile-tall.png`.

The independent verifier accepted all six images. Desktop ProductNav remains
168px. The 390px root is 376px and the continuity console is 374px. Every
state has zero horizontal overflow, zero unlabeled controls, at least one live
region, no unexpected browser errors, and zero direct market-provider calls.
The hosted sign-in button has a visible 2px keyboard focus outline. Conflict
proof exposes both `Keep local` and `Use hosted`.

## Direct Inspection And Fixes

All final images were opened and inspected, not only checked for nonblank
pixels. Two issues found by the final pass were fixed before acceptance:

1. The hidden JSON backup input lacked its own accessible name. It now has
   `aria-label="Import account backup"`, and all authenticated states enforce
   zero unlabeled controls.
2. The 390px session/source truth bar clipped its third status behind internal
   horizontal scrolling. It now wraps into readable rows on narrow screens.

The dense desktop hierarchy, conflict warning, account controls, Watchlist
research context, chart, and right health rail remain stable with no overlap.

## Evidence Boundary

These screenshots use deterministic intercepted account states so conflict and
outage paths are repeatable and make no provider calls. They prove layout,
interaction, accessibility, and truthful state labels. They do not prove a
real Supabase login or hosted restore; that evidence is produced only by
`scripts/test-phase6p-product-recovery.ps1`.

Machine summary:

- `review_workspace/phase6p_visual/summary.json`;
- bytes: 3,439;
- SHA-256:
  `BD3E555E749DABED751FB88DC05B3F36F2A7595E67F11F2F44C1998690A2417D`.
