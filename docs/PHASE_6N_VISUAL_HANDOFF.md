# Phase 6N Visual Evidence Handoff

Updated: 2026-07-14
Status: completed and independently verified on an approved local-browser machine

## Run

From the repository root, execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6n_visual_handoff.ps1
```

The script selects unused local ports, starts a fresh production web process
and FastAPI process, checks both health surfaces, captures the Phase 6N matrix,
independently verifies the resulting summary, and stops only the processes it
started. This avoids reusing an older Next.js process whose asset manifest no
longer matches the current production build.

For the Account A/B isolation journey only, the handoff enables the existing
process-local test identity behind a run-scoped environment override. It uses a
new temporary account database and HTTP-compatible local cookies, then stops
the child processes, removes the temporary database, and restores all prior
process environment values. Normal product startup keeps local test identity
disabled unless explicitly configured.

## Passing Output

A successful run prints `Phase 6N visual evidence verified.` and writes:

- `review_workspace/phase6n_visual/summary.json`;
- `review_workspace/phase6n_visual/*.png`.

The verifier requires real screenshot files larger than 12 KB, all four
drilldown destinations, Account A/B isolation, optimistic conflict, offline
retention, the six controlled operational states, 390px critical-first order,
a visible keyboard focus state, an `aria-live` status region, no horizontal
overflow, no browser/page errors, and zero direct provider requests.
The capture also fails immediately if the terminal stylesheet is absent; plain
browser-default HTML is never accepted as visual proof.
Unexpected transport failures are reported with the HTTP status, exact URL,
and resource type. Controlled `409` and `503` scenarios remain accepted only
inside their named conflict/offline journeys.
Allowlisted browser-initiated `net::ERR_ABORTED` cancellations are retained
separately as navigation evidence. Only same-origin Next.js `_rsc` fetches and
OpenStreetMap tile images qualify because those resources are routinely
cancelled when a verified drilldown immediately navigates to its return
destination. Any other aborted request remains a failure.

## Accepted Evidence

The command succeeded on 2026-07-14. Its generated files remain the accepted
reproducible evidence set; all 23 images were personally inspected, the
independent verifier passed, release gates were rerun, and the visual registry
was updated. Do not hand-edit `summary.json` or substitute HTTP markers when
reproducing this evidence.
