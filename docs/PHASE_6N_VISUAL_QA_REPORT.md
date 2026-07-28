# Phase 6N Visual QA Report

Updated: 2026-07-14
Status: passed; final visual matrix inspected and registered

## Method And Evidence

The required in-app Browser discovery was attempted. Localhost navigation was
rejected by the configured enterprise browser policy, which explicitly
prohibited retrying through alternate browser surfaces. Before that rejection,
the repository production Chrome harness produced:

- `review_workspace/phase6n_visual/observation-run-progress-desktop.png`;
- `review_workspace/phase6n_visual/observation-run-completed-desktop.png`.

Both images were personally inspected. The completed desktop capture shows a
readable 168px product rail, compact run command band, last-run/session/provider
truth, and a dense Attention queue. It does not show crushed Research labels.

## Defects Found And Repaired

- the first progress capture retained a scrolled page position and left an
  unacceptable empty upper area; the harness now scrolls to the top before
  capture;
- the first 390px run put the first material row at y=1017 on an 844px viewport;
- mobile CSS was compacted so observation metrics, change strips, and filters
  use bounded horizontal rows and redundant explanatory copy is removed;
- the visual harness now declares progress, completed, no-due-work,
  quota-blocked, partial/LKG, cancelled, provider/runtime-offline, no-list,
  drilldown/return, navigation-width, hidden-request, and regression checks.

## Gate Truth

The approved-machine production handoff completed on 2026-07-14. The real
`review_workspace/phase6n_visual/summary.json` reports `passed: true`, and the
independent verifier reports:

- 23 real screenshots, including all 13 mandatory files;
- first material mobile row at y=720 in the 390x844 viewport;
- 168px desktop ProductNav and no horizontal overflow;
- visible 2px keyboard focus and one polite live region;
- zero direct provider requests and zero unexpected browser/page errors;
- successful News, Brief, Map, and Analyst drilldown/return;
- Account A reviewed state, Account B isolation, controlled 409 conflict, and
  controlled 503 offline continuity.

All 23 final images were personally inspected. The visual completion gate is
closed; this does not imply benchmark parity or hosted persistence readiness.

## 2026-07-14 Harness Closure Recheck

The official in-app Browser was attempted again and rejected localhost under
the same enterprise network policy. No alternate browser surface or raw CDP
workaround was used after that rejection.

The repository-side handoff is now complete and machine-verifiable:

- `capture-phase6n.mjs` covers desktop progress/completion, 390x844 critical
  ordering, all six controlled recovery states, runtime offline, Account A/B
  isolation, optimistic conflict, and News/Brief/Map/Analyst return journeys;
- each capture group fails on browser/page errors or direct provider requests;
- keyboard focus, `aria-live`, ProductNav width, horizontal overflow, and
  screenshot byte floors are asserted;
- `verify-phase6n-visual-summary.mjs` independently rejects incomplete or
  synthetic pass summaries;
- `run_phase6n_visual_handoff.ps1` prepares the local web/API runtime, executes
  the capture, and then runs the independent verifier.

The exact approved-machine command is:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6n_visual_handoff.ps1
```

At that checkpoint, passing repository tests proved the handoff and verifier
behavior, not the final visual result. The gate remained open until that
command produced a real
`review_workspace/phase6n_visual/summary.json` and the resulting images were
personally inspected and registered.

## 2026-07-14 First Handoff Run

The first user-run handoff reached the capture harness but failed its focus
assertion. Inspection of the newly written progress image found the real root
cause: the reused production server rendered browser-default HTML without the
terminal stylesheet. The prior valid completed image remained styled, proving
this was a stale Next.js process/build-asset mismatch rather than an intended
design state.

The handoff now starts a fresh production process on unused ports and cleans up
only those new processes. The capture now rejects a missing terminal
stylesheet before taking evidence, and keyboard focus verification traverses
the real tab order instead of assuming `Shift+Tab` and `Tab` return to the same
control. A fresh handoff run is required; the unstyled progress image is
explicitly rejected evidence.

## 2026-07-14 Drilldown Recheck

A later approved-machine run completed the desktop, mobile, recovery-state,
runtime-offline, and all four drilldown screenshots before failing the
drilldown telemetry gate. Personal inspection of the Analyst capture exposed
`account-session-http-404` in the workspace identity bar.

The backend `/api/account/session` contract and its tenancy tests were healthy.
The failure was created by `installAccountRuntime()` in the visual harness:
its Attention-only route mock returned a synthetic `404` for every unmatched
account route, including the Analyst workspace session request. Unmatched
account routes now fall through to the real same-origin account proxy.

Browser telemetry now records unexpected HTTP failures as structured status,
URL, and resource-type evidence instead of relying on Chromium's URL-less
`Failed to load resource` console text. This prevents another missing route
from becoming an opaque status-only failure. At that checkpoint, the visual
gate remained open until the corrected handoff completed and every resulting
image was inspected.

The next run exposed a second telemetry-classification defect rather than a
product failure. Next.js RSC prefetch requests and OpenStreetMap image requests
were reported as `net::ERR_ABORTED` when the drilldown journey moved to its next
verified destination. These are browser-initiated cancellations, not HTTP or
network failures. The harness now retains only same-origin `_rsc` fetch and
OpenStreetMap tile cancellations under `cancelledRequests` while continuing to
fail on all other aborts, HTTP `4xx/5xx`, DNS/connection errors, page errors,
and unexpected console errors.

## 2026-07-14 Isolated-Port CORS Recheck

The subsequent run reached the final Phase 6H-6M regression sweep and exposed
a real runtime-boundary defect. The visual handoff starts a clean web process
at port `3167`, while FastAPI still allowed only loopback origins in the old
`3000-3099` range. Browser reads for the AAPL compact summary and chart were
therefore blocked by CORS even though both runtime endpoints were healthy.

FastAPI now permits only `http://127.0.0.1:3xxx` and
`http://localhost:3xxx` product origins. External origins remain rejected.
Regression tests prove both the preflight policy and the exact Phase 6N
summary/chart GET requests from `http://127.0.0.1:3167`. The visual gate stayed
open until the approved-machine handoff completed and its final images passed
personal inspection.

## 2026-07-14 Account Proof Recheck

The next approved-machine capture completed every non-account journey and
wrote a `passed: true` capture report. The independent verifier correctly
rejected it because the runtime's secure default left process-local test auth
disabled, so Account A/B isolation evidence was absent.

The handoff now enables local test auth only for its child runtime, assigns a
unique temporary account database per run, forces non-secure cookies only for
the loopback HTTP journey, and restores prior process environment values after
the child processes stop. The ordinary launcher and product default remain
unchanged. Identity, CSRF, tenant isolation, and Attention API regression tests
pass with this boundary. At that historical checkpoint, one corrected handoff
run was then required for final visual inspection and registration; the final
accepted run below closed it.

## 2026-07-14 Final Accepted Run

The corrected handoff completed both capture and independent verification.
Every final image was inspected in these groups:

- desktop progress and completion;
- 390x844 critical-first and 390x3843 full-flow mobile;
- no-due, quota-blocked, partial/LKG, cancelled, provider-offline, no-list, and
  runtime-offline states;
- News, Brief, Map, and Analyst drilldown/return;
- Account A reviewed, Account B isolated, optimistic conflict, and account API
  offline with local evidence retained;
- Phase 6H Analyst, Phase 6I Operations, Phase 6L Watchlist, and Phase 6M
  Attention regressions.

The inspected UI has no incoherent overlap, clipping, crushed Research rail, or
horizontal page overflow. The Watchlist regression keeps its full 168px rail;
the map is nonblank with visible tiles, marker, layer controls, and evidence
rail; Analyst and Watchlist charts are nonblank.

The image viewer intermittently displayed large black regions in some dark UI
captures. Direct `System.Drawing` sampling of all 23 PNG files found zero
near-black samples in every non-chart image; the tiny ratios in chart/map
images come from legitimate rendered pixels. Progress and completed desktop
top-250 regions matched exactly across 100,000 sampled pixels. The apparent
black regions were a viewer presentation artifact, not screenshot corruption.
