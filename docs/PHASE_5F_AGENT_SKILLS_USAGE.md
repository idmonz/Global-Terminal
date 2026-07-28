# Phase 5F Agent Skills Usage

Updated: 2026-06-19

## Sources

The Phase 5F workflow combines:

- OpenAI Codex current manual guidance for Goal, Context, Constraints, and Done-when prompts;
- progressive-disclosure Agent Skills guidance;
- the MIT `agent-skills-main` archive;
- Apache-2.0 `open-design` audit and preflight concepts.

## Applied Agent Skills

| Skill | Evidence | Phase 5F application |
|---|---|---|
| spec-driven-development | gated phases at lines 22-192 | audit criteria before patches |
| planning-and-task-breakdown | dependency graph, vertical slices, checkpoints at lines 35-214 | release, parity, external, design, provider, verification workstreams |
| source-driven-development | official sources and verification at lines 27-183 | existing repo/external/product pages inspected first |
| frontend-ui-engineering | architecture, design system, accessibility, responsive and verification at lines 20-318 | screenshot and viewport requirements |
| api-and-interface-design | contract-first, errors, validation, additive change at lines 37-284 | retain `phase_2b.v1`, provenance and explicit unavailable states |
| test-driven-development | red/green/refactor, browser and security boundaries at lines 35-372 | focused release regression before broad checks |
| debugging-and-error-recovery | reproduce/localize/root-fix/guard/E2E at lines 40-291 | release contradiction isolated and fixed |
| code-review-and-quality | correctness, readability, architecture, security, performance at lines 22-339 | final audit dimensions |
| security-and-hardening | threat model, validation, supply chain, secrets, AI at lines 21-449 | secret-safe fixtures/releases and no execution path |
| docs-and-ADRs | ADR/API/README/agent docs at lines 23-269 | traceable Phase 5F artifacts |
| shipping | staged rollout, monitoring, rollback, verification at lines 20-292 | release reconciliation and later deployment gates |

## Applied Open-Design Process

From `open-design-main/skills/taste-skill/SKILL.md` and `redesign-skill/SKILL.md`:

- infer the audience and design language before coding;
- treat a data terminal as high-density operational software;
- audit existing brand tokens and functionality before redesign;
- use cards only where boundaries or elevation carry meaning;
- make mobile collapse explicit;
- verify loading, empty, error, hover, focus, and contrast states;
- compare screenshots and complete a final preflight.

The terminal intentionally does not adopt marketing-page rules that conflict with dense operational software. Product ergonomics and data truth take precedence over decorative novelty.

## OpenAI Prompt Shape

The next execution prompt uses:

1. **Goal**: one concrete user journey.
2. **Context**: exact current files, contracts, and known gaps.
3. **Constraints**: licensing, data truth, safety, architecture, and scope.
4. **Tasks**: vertically ordered implementation slices.
5. **Done when**: user-visible acceptance checks and commands.

Goal mode is appropriate because the task is multi-step and has measurable completion criteria. The prompt avoids a reusable custom prompt because current Codex guidance prefers Agent Skills for repeatable workflows.

## Recommended Repo Skill

After Phase 5G stabilizes, create a focused repo skill under `.agents/skills/terminal-vertical-slice/SKILL.md` that codifies:

- existing-engine inspection;
- contract and provider truth checks;
- benchmark review;
- desktop/mobile visual verification;
- no-advice and release hygiene gates.

Do not create it during the audit-only phase; first validate the workflow on one complete vertical slice.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
