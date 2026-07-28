# Goal 11F Plan

Goal 11F closes the final setup, command-safety, report-export, command-routing, and release-reporting defects found after Goal 11E.

## Work slices

1. Pre-flight Goal 11E baseline verification.
2. Agent-skills process review as a non-runtime engineering reference.
3. Restore `.env.example` as a placeholder-only onboarding artifact.
4. Patch command safety for advisory/guarantee false negatives and descriptive research false positives.
5. Sanitize optional report HTML export.
6. Correct Energy Brief command routing.
7. Clarify release package count terminology.
8. Update documentation and Goal 12 readiness decision.
9. Run shipping gates and produce release package.

- Scope: Goal 11F hotfix only; Goal 12 was not implemented.
- Boundary: research-only local workspace, no broker path, no autonomous execution path, no external runtime dependency.
- Verification gates: compileall, smoke tests, full pytest, cleanup dry-run, cleanup execute, and release build.
