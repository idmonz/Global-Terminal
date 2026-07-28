# Goal 13 Action-less Simulation Architecture Prep

This document prepares Goal 13 only. It does not implement a Goal 13 runtime.

## Core objects

- `simulation_case`: local research container linked to options research cases and Strategy-as-Git records.
- `scenario_set`: supplied deterministic shocks, time windows, or hypothetical states.
- `data_feed_snapshot`: immutable, source-labeled supplied-data payload.
- `model_artifact`: local model metadata, caveats, inputs, and outputs; no heavy inference runtime required.
- `simulation_result`: deterministic output table with source/caveat schema and no action instructions.
- `review_queue_item`: audit object for human review; not approval and not execution.
- `actionless_boundary`: simulations may compute, display, attach, and review; they may not route, place, approve, or automate market actions.

## No-execution policy

Goal 13 must remain no broker execution, no order routing, no RL trading agent, no autonomous trading, no live trading, no model weights, no mandatory heavy ML runtime, and no instruction wording.

## Source/caveat schema

Each simulation artifact should include: `source`, `snapshot_time`, `freshness`, `data_quality`, `method`, `limitations`, `review_status`, `research_only`, and the standard research-only notice.

## Relationship to existing systems

- Options research cases become parent containers for surface, chain, book, and diagnostic inputs.
- Strategy-as-Git stores simulation artifacts as review attachments only.
- Report Inbox receives simulation reports with caveats and redacted local paths.

## External concept mapping

- tensortrade: feed/scenario/action separation, with action execution removed.
- QuantDinger: research lifecycle monitoring without broker/API/autonomous agent.
- Kronos: model artifact/caveat schema without model runtime.
- OpenAlice: artifact workflow/review queue without execution.
- agent-skills: implementation process only.
