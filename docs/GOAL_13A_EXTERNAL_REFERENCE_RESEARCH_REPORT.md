# Goal 13A External Reference Research Report

Generated: 2026-06-15

## Inspection Summary

The `external (2).zip` archive was inspected at the nested ZIP inventory level, license/notice level, package metadata level, and selected workflow/schema documentation level. The implementation keeps all references outside the release package and uses them only as process or behavior references.

## References Studied

- `agent-skills-main.zip`: studied the spec, plan, build, test, review, and ship command docs plus spec-driven, test-driven, code-review, and shipping skill docs. Adopted the lifecycle sequence into Goal 13A docs and verification gates.
- `tensortrade-master.zip`: studied data feed/observer/action-scheme documentation and domain file inventory. Adopted only the separation idea: feed snapshots and scenario sets are separate from result artifacts. Action schemes, orders, RL agents, rewards, exchanges, and brokers are excluded.
- `QuantDinger-main.zip`: studied license metadata, agent docs, backtest-limit policy, and strategy-review inventory. Adopted review-state and limit/caveat vocabulary for local action-less governance. Broker/API/live/paper execution is excluded.
- `Kronos-master.zip`: studied license metadata, README, model/training/prediction inventory, and data preparation expectations. Adopted model-card metadata concepts only. No model runtime, weights, Torch, Hugging Face, or forecast inference is included.
- `OpenAlice-master.zip`: studied AGPL license, tool-audit skill, build-thesis skill, safety docs, and trading-domain README. Adopted review discipline and audit checklist concepts only. Trading domain and agent runtime are excluded.
- `worldmonitor-main.zip`: studied AGPL license, package metadata, simulation queue/status inventory, and run-id validation hardening note. Adopted local safe-ID and package-pointer style validation concepts only. No API, Redis, R2, queue, worker, or scheduler is included.
- Other references were checked for license posture and concept boundaries: OpenBB, BB-Terminal, bloomberg-terminal, OpenStock, optlib, osiris, quant-traderr-lab, and worldview.

## Clean-room Reimplementation Choices

- Goal 13A uses new local modules named for this project rather than importing or adapting external package APIs.
- The store mirrors the existing Goal 12D/12E private case-store pattern already in this repository.
- IDs are safe local identifiers, not remote run IDs, queue keys, URLs, or file paths.
- Results are deterministic user-supplied summaries and diagnostics. No model inference is invoked.
- Review state is a local governance record, not an approval to act.

## Explicitly Rejected

- TensorTrade runtime, action schemes, RL policies, reward optimization, OMS, broker, exchange, and order modules.
- QuantDinger broker integrations, paper/live execution, API server, strategy compiler runtime, and autonomous agents.
- Kronos model weights, checkpoints, prediction scripts, web UI, and training or inference dependencies.
- OpenAlice AGPL source, trading agent runtime, broker packages, MCP server, and workspace engine.
- WorldMonitor AGPL source, Redis queues, Vercel/API handlers, R2 paths, workers, and package processors.
- OpenBB hard dependencies and paid-provider assumptions.

## Source Copy Result

No external source code was copied. All implementation files are project-native and use existing local helper patterns.
