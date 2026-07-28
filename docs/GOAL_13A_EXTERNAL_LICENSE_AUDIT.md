# Goal 13A External License Audit

Generated: 2026-06-15

This is an engineering license audit, not legal advice. Goal 13A uses external projects as process, architecture, and behavior references only. No external source code, vendored dependency, generated asset, model weight, checkpoint, notebook, or runtime package is copied into this project.

| Source | Observed license and notices | Logic studied | Code copied | Attribution required in release | Compatibility decision | Risk notes |
|---|---|---|---:|---|---|---|
| `external/agent-skills-main.zip` | MIT. Copyright 2025 Addy Osmani. | DEFINE, PLAN, BUILD, VERIFY, REVIEW, SHIP workflow, spec-first planning, TDD loop, review and ship gates. | No | No copied source. Concept mention in docs only. | Compatible for process-only study. | MIT notice not bundled because no source copied. |
| `external/tensortrade-master.zip` | Apache-2.0. | Feed, observer, environment, action-scheme separation. Action conversion into orders was studied only to remove that class of behavior. | No | No copied source. | Compatible for clean-room architecture inspiration. | All RL, action, broker, reward, and exchange concepts excluded from runtime. |
| `external/QuantDinger-main.zip` | Apache-2.0. | Backtest range policy, strategy review lifecycle, guardrail vocabulary, workflow decomposition. | No | No copied source. | Compatible for behavior-level inspiration. | Broker/API/live/paper execution surfaces were explicitly rejected. |
| `external/Kronos-master.zip` | MIT. Copyright 2025 ShiYu. | Model artifact metadata, financial foundation-model caveats, data preparation expectations, provenance needs. | No | No copied source. | Compatible for metadata-only model-card inspiration. | No weights, checkpoints, Torch, Hugging Face, inference, or forecast runtime added. |
| `external/OpenAlice-master.zip` | AGPL-3.0. | Tool audit workflow, artifact review discipline, thesis/build discipline, safety documentation shape. | No | No copied source. | Research-only, behavior-only. | Copyleft-sensitive. No AGPL source, runtime, or network service copied. |
| `external/worldmonitor-main.zip` and embedded folder | AGPL-3.0-only. Copyright 2024-2026 Elie Habib. | Simulation package/status concepts, run-id validation concern, pointer/queue parity, package hardening notes. | No | No copied source. | Research-only, behavior-only. | No Redis, queue, API route, worker, R2, or background service added. |
| `external/OpenBB-develop.zip` | AGPL-3.0-only. Copyright OpenBB Inc. | Provider metadata and registry-governance concepts. | No | No copied source. | Research-only, behavior-only. | No OpenBB hard dependency or provider SDK requirement added. |
| `external/BB-Terminal-main.zip` | No top-level license found in inspected metadata; package is private. | Dense terminal UX and command grouping vocabulary. | No | No copied source. | Research-only, no-copy. | Treat as unknown/no-license for code purposes. |
| `external/bloomberg-terminal-main.zip` | No top-level license found in inspected metadata; package is private. | Dense terminal UX and simulated-market caveat patterns. | No | No copied source. | Research-only, no-copy. | Treat as unknown/no-license for code purposes. |
| `external/OpenStock-main.zip` | AGPL-3.0. | Case/report/watchlist UX flow concepts. | No | No copied source. | Research-only, behavior-only. | Copyleft-sensitive. No source copied. |
| `external/optlib-master.zip` | MIT. Copyright 2017 Davis W. Edwards. | Existing options formula context from prior goals only. | No | No copied source. | Compatible for prior concept use. | No Goal 13A runtime dependency added. |
| `external/osiris-master.zip` | MIT. Copyright 2026 simplifaisoul. | Source/layer/time/intelligence UX vocabulary. | No | No copied source. | Compatible for concept use. | Not used for Goal 13A runtime. |
| `external/quant-traderr-lab-main.zip` | MIT. Copyright 2026 quant-traderr. | Quant diagnostic vocabulary from prior goals. | No | No copied source. | Compatible for concept use. | Not used for Goal 13A runtime. |
| `external/worldview-main.zip` | NASA Open Source Agreement 1.3. Copyright 2013-2026 United States Government as represented by NASA Administrator. | Layer/time UX and source metadata concepts only. | No | No copied source. | Research-only, behavior-only. | NASA license is treated as no-copy without a separate license plan. |

## Boundary Decision

All Goal 13A implementation is clean-room, project-native Python using existing local patterns from this repository. External materials were inspected for lifecycle, schema, validation, review, and release-gate ideas. No external project files or source snippets were copied into `lib/`, `pages/`, `tests/`, `scripts/`, `static/`, or `docs/`.
