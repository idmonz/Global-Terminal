# Goal 11 Engineering Governance

## DEFINE

- Write the Goal 11 spec before major code.
- Clarify assumptions, acceptance criteria, non-goals, and reference boundaries.
- Keep external references conceptual only.
- Keep runtime dependencies local, optional, and testable without network access.

## PLAN

Vertical slices:

1. SQLite workspace storage.
2. Personal Research Workspace.
3. Multi-Domain Watchlist.
4. Alert Center.
5. Report Inbox.
6. Strategy-as-Git Decision Log.
7. OSINT-aware watchlist briefing.
8. Command Palette / Quick Actions.
9. Optional TradingView visual supplement.
10. Docs, tests, release hygiene.

## BUILD

- Implement incrementally.
- Preserve Goal 10B canonical functions.
- Keep modules small and testable.
- Use existing visual/provider/workspace conventions where practical.
- Do not rewrite the project or migrate frontend/storage/auth.

## VERIFY

- Tests use temporary SQLite DBs.
- Tests do not require internet, API keys, OpenBB, Streamlit runtime, or external folders.
- Missing data becomes skipped/data-gap status, never a false alert.

## REVIEW

- Record code review findings.
- Record security audit findings.
- Record test coverage and known limitations.

## SHIP

- Verify external, private data, cache, secrets, generated artifacts, and external archives are excluded from release.
- Verify no external source copied.
- Verify no live trading/broker/execution workflow.
- Verify research-only disclaimers.

