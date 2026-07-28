# Visual Version Registry

Updated: 2026-07-27

## Completion Rule

Every product phase that changes a user-visible surface must ship with a
versioned `apps/web/scripts/capture-phase*.mjs` command, a machine-readable
`review_workspace/phase*_visual/summary.json`, personally inspected desktop and
390px mobile captures, and a checked-in visual QA report. Nonblank rendering is
not acceptance: the harness must assert dimensions, overflow, state truth,
unexpected browser errors, and the phase's primary user journey.

The generated `review_workspace` evidence is deliberately excluded from release
artifacts. This registry and each checked-in report preserve the durable audit
trail and exact regeneration command.

## Registered Evidence

| Version | Product surface | Capture command | Evidence/report |
|---|---|---|---|
| Phase 5H-6I | Market, map, news, symbol, options, brief, operations iterations | `npm --prefix apps/web run visual:phase<id>` | `apps/web/scripts/capture-phase5h.mjs` through `capture-phase6i.mjs`; corresponding Phase reports |
| Phase 6J | Identity and tenancy readiness | `npm --prefix apps/web run visual:phase6j` | `review_workspace/phase6j_visual/summary.json` and Phase 6J visual report |
| Phase 6K | Account Research journey | `npm --prefix apps/web run visual:phase6k` | `review_workspace/phase6k_visual/summary.json` and `docs/PHASE_6K_VISUAL_QA_REPORT.md` |
| Phase 6L | `watchlist-desk` navigation, local-first research sync, hosted-unavailable recovery | `npm --prefix apps/web run visual:phase6l` | `review_workspace/phase6l_visual/summary.json` and `docs/PHASE_6L_VISUAL_QA_REPORT.md` |
| Phase 6M | Unified Attention digest, queue, review policy/state, exact evidence return, A/B and offline recovery | `npm --prefix apps/web run visual:phase6m` | `review_workspace/phase6m_visual/summary.json` and `docs/PHASE_6M_VISUAL_QA_REPORT.md` |
| Phase 6N | Explicit observation run, progress/cancel/recovery, source/session/quota truth, material Attention handoff, exact return, and Account A/B isolation | `powershell -ExecutionPolicy Bypass -File scripts/run_phase6n_visual_handoff.ps1` | `review_workspace/phase6n_visual/summary.json`, 23 personally inspected screenshots, independent verifier pass, and `docs/PHASE_6N_VISUAL_QA_REPORT.md` |
| Phase 6O | Alert rule creation/lifecycle, stored-observation evaluation, trigger history, worker failure/recovery, A/B isolation, conflict, and exact evidence return | `powershell -ExecutionPolicy Bypass -File scripts/run_phase6o_visual_handoff.ps1` | `review_workspace/phase6o_visual/summary.json`, 18 personally inspected screenshots, independent verifier pass, and `docs/PHASE_6O_VISUAL_QA_REPORT.md` |
| Phase 6P | Hosted sign-in surface, account continuity, restore, conflict, offline, export/import/delete controls, and 390px recovery truth | `powershell -ExecutionPolicy Bypass -File scripts/run_phase6p_visual_handoff.ps1` | `review_workspace/phase6p_visual/summary.json`, 6 personally inspected screenshots, independent verifier pass, and `docs/PHASE_6P_VISUAL_QA_REPORT.md` |
| Phase 6Q | Hosted schedule consent/control, due/run/source/quota/LKG truth, controlled failure/recovery/kill/cleanup, Account A/B, session expiry, mobile, and prior-surface regressions | `powershell -ExecutionPolicy Bypass -File scripts/run_phase6q_visual_handoff.ps1` | `review_workspace/phase6q_visual/summary.json`, 24 personally inspected screenshots, independent verifier pass, and `docs/PHASE_6Q_VISUAL_QA_REPORT.md` |

## Phase 6L Required Captures

- readable Watchlist Desk desktop navigation with the Research rail at least 160px;
- sync plan reviewed, explicit consent, pending local queue, and honest Hosted unavailable state;
- mobile sync truth before long research history with no horizontal overflow;
- Account B queue isolation;
- account API outage with local Watchlist research retained;
- Analyst Workspace, Market Map, and Daily Brief regression checks.

Phase 6L's deterministic visual journey is seeded with
`python scripts/seed_phase6l_visual_data.py --reset`; both databases stay under
`review_workspace/phase6l_visual/` and must never enter a release archive.

## Phase 6M Required Captures

- desktop digest and prioritized queue plus 390px critical-first layout;
- source-degraded and no-material states;
- review, acknowledge, snooze, expiry/undo, checkpoint, and conflict;
- exact Analyst, News, Brief, and Map drilldown/return;
- local/account, Account A/B isolation, and account API outage continuity;
- Analyst, Operations, Watchlist, and Daily Brief regressions.

The final machine summary records 9 visible rows, 168px desktop ProductNav,
zero hidden/provider requests, no duplicate IDs or unlabeled controls, no page
overflow, and no unexpected browser/page errors.

## Phase 6N Accepted Evidence

The production handoff wrote a real `phase6n.visual.v1` summary and 23
screenshots. The independent verifier accepted all 13 mandatory captures,
mobile critical-first y=720, 168px ProductNav, visible focus, live-region
status, zero direct provider requests, all controlled recovery states, Account
A/B isolation, conflict/offline truth, and exact drilldown/return. All 23 files
were personally inspected and passed source/layout integrity review.

## Phase 6O Accepted Evidence

The production handoff wrote `phase6o.visual.v1` and 18 screenshots. The
independent verifier accepted all 17 mandatory captures, 44,984-byte initial
HTML, 168px desktop ProductNav, 390px no-overflow layout, first mobile trigger
at y=560, visible 2px focus, one live region, zero duplicate IDs/unlabeled
controls/provider requests/unexpected errors, and exact Analyst/News/Brief/Map
return. Empty, active, history, lifecycle, quota, LKG, unavailable, worker
recovery, conflict, and A/B states were personally inspected.

## Phase 6P Accepted Evidence

The production handoff wrote `phase6p.visual.v1` and six screenshots. The
independent verifier accepted hosted sign-in, restored, conflict, offline, and
390px states with 168px desktop ProductNav, 376px mobile root, 374px mobile
continuity console, visible 2px focus, live regions, and zero overflow,
unlabeled controls, provider requests, or unexpected errors. Direct inspection
found and closed the backup-input accessible-name gap and mobile truth-bar text
clipping before the final capture. These states remain deterministic visual
proof; the separate 2026-07-16 owner-run hosted harness now verifies the real
Supabase session, fresh-repository restore, Account B isolation, and cleanup.

## Phase 6Q Accepted Visual Evidence

The production handoff wrote `phase6q.visual.v1` and 24 screenshots. The
independent verifier accepted a 49,002-byte initial Alert Manager document,
168px desktop ProductNav, 390px root and 378px mobile schedule panel, visible
2px focus, two live regions, zero horizontal overflow, duplicate IDs, unlabeled
controls, unexpected errors, or market-provider requests. Safe default,
consent/enable, running, source-backed controlled completion, no-due, replay,
quota, provider-offline/LKG, lease expiry/recovery, kill, cleanup, Account A/B,
session expiry, and six regression surfaces were directly inspected. This is
product/interaction evidence only; every capture remains `hosted-unverified`
and is not proof of a deployed recurring invocation.

The CI/supply-chain continuation recaptured the same 24-image set at
2026-07-27T08:20:32Z. The safe-default desktop, 390px tall mobile, and Watchlist
regression captures were directly inspected again. No visible product code
changed; the rerun confirms the deployment-file hardening introduced no layout,
navigation, focus, mobile, or provider-call regression.
