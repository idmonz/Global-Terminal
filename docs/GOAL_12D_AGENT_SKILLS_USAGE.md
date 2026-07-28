# GOAL 12D Agent Skills Usage

The external `agent-skills-main` reference was used only as process guidance. It was not installed, copied, vendored, or included in runtime/release.

Applied process:

- test-driven-development: focused Goal 12D tests were added before implementation patches.
- security-and-hardening: command text, CSV-derived identifiers, case files, report exports, and workflow payloads were treated as trust boundaries.
- source-driven-development: external references were inspected as inventory and mapped to concept-only use.
- debugging-and-error-recovery: root causes were fixed rather than snapshot-only assertions.
- code-review-and-quality: no default/fake TTE behavior and unknown-model silent pricing were removed.
- shipping-and-launch: compileall, smoke, pytest, cleanup, release build, and release manifest inspection were run before handoff.
