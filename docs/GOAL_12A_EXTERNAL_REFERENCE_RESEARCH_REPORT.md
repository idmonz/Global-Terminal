# GOAL 12A External Reference Research Report

- generated_at_utc: 2026-06-14T14:31:24+00:00
- source boundary: conceptual inspection only; no external source code copied into runtime modules.

## 1. External inventory

- optlib-master: 11 inspected local files available after extraction; license summary: MIT License
- Kronos-master: 92 inspected local files available after extraction; license summary: MIT License
- quant-traderr-lab-main: 65 inspected local files available after extraction; license summary: MIT License
- tensortrade-master: 456 inspected local files available after extraction; license summary: Apache License /                            Version 2.0, January 2004
- QuantDinger-main: 494 inspected local files available after extraction; license summary: Apache License /                            Version 2.0, January 2004
- OpenBB-develop: 2191 inspected local files available after extraction; license summary: Copyright (c) 2021-2025 OpenBB Inc.
- agent-skills-main: 90 inspected local files available after extraction; license summary: MIT License

## 2. License summary

- MIT references: optlib, Kronos, quant-traderr-lab, QuantDinger, OpenBB, agent-skills.
- Apache-2.0 reference: tensortrade.
- License terms were treated as source-boundary constraints; Goal 12A did not vendor or import these projects.

## 3. Files inspected

### optlib-master
- `README.md`
- `LICENSE`
- `optlib/gbs.py`
- `tests/test_gbs.py`
### Kronos-master
- `README.md`
- `LICENSE`
- `examples/prediction_example.py`
### quant-traderr-lab-main
- `README.md`
- `LICENSE`
- `Black Scholes/Black Scholes pipeline.py`
- `GARCH/GARCH pipeline.py`
### tensortrade-master
- `README.md`
- `LICENSE`
- `tensortrade/env/default/actions.py`
- `tensortrade/env/default/rewards.py`
### QuantDinger-main
- `README.md`
- `LICENSE`
### OpenBB-develop
- `README.md`
- `LICENSE`
- `openbb_platform/core/openbb_core/provider/abstract/data.py`
### agent-skills-main
- `README.md`
- `LICENSE`
- `skills/test-driven-development/SKILL.md`
- `skills/security-and-hardening/SKILL.md`
- `skills/source-driven-development/SKILL.md`
- `references/security-checklist.md`
- `references/testing-patterns.md`

## 4. Concepts adopted

- optlib-master: European closed-form option formula coverage, generalized carry intuition, Greeks/IV/payoff validation concepts.
- Kronos-master: future model artifact metadata and explicit forecast caveat concepts.
- quant-traderr-lab-main: roadmap categories for HRP/RMT/GARCH/Kalman/Cointegration/Hurst/OU-style diagnostics.
- tensortrade-master: separation between data feed, scenario, renderer, and action-less research output.
- QuantDinger-main: strategy lifecycle and review artifact workflow concepts.
- OpenBB-develop: provider capability card and optional source snapshot pattern.
- agent-skills-main: TDD, source-boundary, hardening, code review, debugging, and shipping gate process.

## 5. Concepts rejected

- Runtime imports from optlib, Kronos, quant-traderr-lab, tensortrade, QuantDinger, OpenBB, and agent-skills.
- TDA wrappers, deprecated SciPy mvn APIs, model weights, Torch/HuggingFace/TensorFlow runtimes, broker/API server surfaces, and live-provider assumptions.

## 6. Runtime dependency decision

Goal 12A is Python standard-library formula code plus existing project modules. No new mandatory provider, ML, RL, or options-library dependency was added.

## 7. Source-copy boundary

No external source tree, function body, class body, model weight, API wrapper, or configuration file was copied into runtime. Formula modules were implemented as original project-native code.

## 8. Reference mapping to Goal 12A

| Reference | Goal 12A mapping | Runtime decision |
|---|---|---|
| optlib | Formula coverage, Greeks, IV, sensitivity/report design | Not imported, not copied |
| Kronos | Future model snapshot placeholder | Metadata only |
| quant-traderr-lab | Quant Model Lab roadmap categories | Concept only |
| tensortrade | Action-less simulation architecture separation | Concept only |
| QuantDinger | Strategy lifecycle attachment workflow | Concept only |
| OpenBB | Provider capability/source snapshot cards | Optional probe only, no dependency |
| agent-skills | Process guardrails | Documentation/process only |

## 9. Research-only confirmation

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.

## 10. No external code copied confirmation

Confirmed by runtime file scan and tests: no external source signatures, archives, model weights, or external tree files are included in Goal 12A runtime or release package.
