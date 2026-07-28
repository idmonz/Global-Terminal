# Goal 6 Plan

Goal 6 is a focused visual-intelligence expansion on the existing Global Market Analyst Terminal. It adds three surfaces without resetting architecture: a map-first War Room, a TradingView-style Financial Terminal, and a News to Market Impact Engine.

## Scope

- Preserve Goal 1 market data, global markets, heatmaps, and cache/DataResult behavior.
- Preserve Phase 4 crypto intelligence, Goal 3 equity/energy/risk modules, Goal 4 AI provider behavior, visual command terminal components, tests, and docs.
- Add new modules under `lib/`, new Streamlit pages under `pages/`, focused tests under `tests/`, and docs under `docs/`.

## Build Order

1. Pre-flight smoke and pytest checks.
2. Canonical function and static universe verification.
3. War Room modules and page.
4. Financial Terminal modules and page.
5. News impact and catalyst graph modules.
6. News and scenario integration.
7. Smoke, full pytest, Streamlit launch check.
8. Release hygiene cleanup and release packaging script.
9. Final documentation and report.

## Guardrails

- No fabricated live OSINT feeds.
- No fabricated forward financials or segment/geographic revenue.
- No causal language for event-to-market links.
- No external WorldMonitor runtime dependency.
- All AI context must include data gaps, primary-data verification, and not-financial-advice framing.
