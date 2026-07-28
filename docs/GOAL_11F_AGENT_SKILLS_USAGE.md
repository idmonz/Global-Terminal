# Goal 11F Agent Skills Usage

The external `agent-skills-main` archive was reviewed as a process reference only. It was not installed, copied into runtime, or included as a dependency.

## Process concepts applied

| Skill/reference | Goal 11F usage |
|---|---|
| test-driven-development | Added focused hotfix tests for setup artifact inclusion, command safety, report export sanitization, energy routing, and release count consistency before validating the implementation. |
| security-and-hardening | Treated command text, report HTML bodies, workflow payloads, and release artifacts as trust boundaries. |
| source-driven-development | Patched the current Goal 11E modules directly rather than assuming behavior from memory. |
| debugging-and-error-recovery | Fixed root causes: shared safety rules, release-builder exclusion rules, export path sanitization, and command-action mapping. |
| code-review-and-quality | Removed ambiguous Energy Brief routing and preserved existing renderer compatibility. |
| shipping-and-launch | Re-ran compileall, smoke, pytest, cleanup, and release packaging gates. |
| security checklist | Applied secret-exclusion and untrusted HTML escaping checks. |
| testing patterns | Used arrange-act-assert style tests with local temporary SQLite workspaces and no network/API dependency. |

## Runtime boundary

No external skill source code, hooks, plugins, or references were vendored into runtime or release.
