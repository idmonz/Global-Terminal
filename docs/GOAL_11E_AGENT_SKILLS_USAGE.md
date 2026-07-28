# Goal 11E Agent Skills Usage

Goal 11E used `agent-skills-main` only as a process reference. No external skill code, hooks, plugins, or runtime files were copied or vendored.

## Files re-checked conceptually

- `skills/test-driven-development/SKILL.md`
- `skills/security-and-hardening/SKILL.md`
- `skills/source-driven-development/SKILL.md`
- `skills/debugging-and-error-recovery/SKILL.md`
- `skills/code-review-and-quality/SKILL.md`
- `skills/shipping-and-launch/SKILL.md`
- `references/security-checklist.md`
- `references/testing-patterns.md`

## Process adoption

| Skill concept | How it affected Goal 11E |
|---|---|
| Test-driven development | New tests cover command false positives, direct blocked actions, alert evaluation wiring, tool-action coverage, selected-state persistence, and rendering safety. |
| Security and hardening | User commands and workflow payloads are treated as untrusted; the same research-only boundary is applied in palette, router, and direct action layer. |
| Source-driven development | Changes were grounded in current project modules and Goal 11D reports rather than memory. |
| Debugging and error recovery | Failures were fixed at root cause: command phrase scanning, selected-state payload fields, and idempotent Markdown sanitization. |
| Code review and quality | Duplicate/placeholder paths were reduced, direct mutation paths were guarded, and new helper functions remain import-safe. |
| Shipping and launch | Final gates include compileall, smoke, full pytest, cleanup dry run, cleanup execute, and release build. |

## Runtime boundary

`agent-skills-main` remains excluded from the release and is not a dependency.
