# Phase 6Q Visual QA Report

Updated: 2026-07-27

## Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6q_visual_handoff.ps1
```

The handoff started isolated production FastAPI and Next.js processes, captured
real browser output with Chrome/Playwright, wrote
`review_workspace/phase6q_visual/summary.json`, and ran an independent summary
verifier.

## Accepted Matrix

The 24 screenshots cover disabled/unverified default, consent and enable,
running, controlled source completion, no due work, replay, quota blocked,
provider unavailable, partial LKG, expired lease, recovery, kill, cleanup,
Account A/B isolation, session expiry, 390x844 mobile/tall, and regressions for
Alert Manager, Watchlist, Attention, Analyst, Map, and News.

Measured acceptance:

- initial HTML: 49,002B, limit 100,000B;
- desktop ProductNav: 168px;
- mobile root/panel: 390px/378px;
- horizontal overflow: false on every asserted surface;
- keyboard focus: visible 2px solid outline;
- live regions: two;
- duplicate IDs and unlabeled controls: zero;
- unexpected errors and market-provider requests: zero;
- controlled session-expiry 401: expected and separately classified.

## Direct Inspection

The safe-default desktop, completed-source desktop, and mobile tall captures were
opened and inspected at full rendered resolution. The Research rail is readable,
the primary schedule card does not crush adjacent controls, source/quota/outcome
remain visible, and the 390px route reflows to one column without clipped text.

The completed source state is deliberately labeled as a controlled visual
fixture. Every screenshot still displays hosted unverified. These captures prove
product layout and state truth, not a deployed recurring run.
