# Phase 5O Next Goal Rationale

Updated: 2026-06-22

## Decision

Next: Phase 5P Historical Global Risk Replay And Map Layers.

## Why

Phase 5O raises market discovery from usable MVP to strong internal beta. The largest remaining benchmark gap explicitly identified by the user and scorecard is the WorldMonitor/worldview category:

- current map events are useful but history is shallow;
- timeline and compare state exist, but durable snapshots and true replay do not;
- weather, flights, AIS, sanctions, and source-specific layer coverage remain uneven;
- users cannot answer “what changed between two windows?” with evidence.

Phase 5P should therefore add local snapshot capture, bounded historical timeline/compare, event replay, layer-diff summaries, and source-linked asset/news context. Premium or credentialed layers must remain unavailable unless verified.

## Why Not Phase 6 First

Hosted auth/billing/operations are necessary, but beginning them before the two strongest daily-use journeys are mature would harden an incomplete product. Phase 5P should bring map intelligence to internal-beta quality; Phase 6 then creates the commercial service foundation around proven workflows.

## Prompt Design

The next prompt follows current Codex guidance:

- Goal, context, constraints, and done-when are explicit.
- The work is one focused vertical slice.
- Verification, lint, tests, visual proof, and release checks are included.
- Repo skills use progressive disclosure.
- External agent-skill evidence is cited without vendoring the external workflow project.
