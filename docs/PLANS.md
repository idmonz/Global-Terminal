# Execution Plans

Substantial work uses one repository-local execution plan so later Codex turns
can recover decisions and evidence without relying on conversation history.

## Rules

- Keep exactly one phase plan in `docs/exec-plans/active/`.
- Record objective, scope, acceptance checks, progress, decisions, failures,
  and verification evidence.
- Update progress while working, not only at the end.
- Move a completed plan to `docs/exec-plans/completed/`.
- Put unrelated ideas in the roadmap instead of expanding an active phase.

This follows OpenAI's agent-harness guidance: `AGENTS.md` is a concise map,
while detailed plans and durable knowledge live in structured repository docs.
