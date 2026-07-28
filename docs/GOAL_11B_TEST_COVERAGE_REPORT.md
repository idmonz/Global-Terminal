# Goal 11B Test Coverage Report

Generated: 2026-06-13T13:30:42.912439+00:00

## Counts

- Collected test files/modules: 246
- Actual test cases by AST: 383
- Added Goal 11B test files: 10
- Added Goal 11B test cases: 25

## New coverage

- Watchlist enrichment and Goal 10B adapter payloads.
- Alert cooldown, expiry, crossing, data gap behavior.
- Type-specific report content.
- Strategy guard warnings, diff, graph, attachments.
- OSINT alias matching, dedupe, confidence labels.
- Provider/data-quality memory.
- Page payloads without Streamlit runtime.
- Overview/navigation integration.
- Release hygiene regression.
- Goal 10B canonical regression guard.

## Mock boundary

Tests use temporary SQLite DBs and supplied payloads. No internet, API key, OpenBB runtime, or Streamlit runtime is required.
