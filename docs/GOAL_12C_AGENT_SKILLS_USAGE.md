# Goal 12C Agent Skills Usage

agent-skills-main was used only as a process reference. The local runtime does not import it and the release package excludes it.

Process use:

- Test-driven development: Goal 12C focused tests were added before and alongside each patch area.
- Security hardening: CSV text, report identifiers, local file paths, workflow payloads, and model diagnostics names were treated as trust boundaries.
- Source-driven development: external references informed architecture boundaries only; no runtime source copy.
- Debugging: failures in TTE handling and report escaping were fixed at root cause.
- Code review and quality: changes were kept modular with public API preservation tests.
- Documentation/ADRs: Goal 12C docs record TTE/model selection, surface QA, diff, stress, and diagnostics boundaries.
- Shipping: compileall, smoke, pytest, cleanup, and release build gates were run before handoff.
