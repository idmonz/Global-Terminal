# Goal 11B Plan

Generated: 2026-06-13T13:30:42.912439+00:00

Goal 11B hardens Goal 11 from an MVP into an operational local research layer. The work is split into verifiable slices:

1. Pre-flight and gap audit.
2. Watchlist real-context wiring through adapters and enrichers.
3. Alert Engine V2 with expiry, cooldown, previous-value crossing, dedupe, and source snapshots.
4. Report Inbox V2 with type-specific markdown/HTML outputs and provider/data-quality memory.
5. Strategy-as-Git V2 with real guard rules, diff, graph, review queue, and forward-tracking payloads.
6. OSINT alias matching with confidence and dedupe.
7. Provider/data-quality snapshot memory.
8. Page layout payloads and Streamlit page hardening.
9. Overview/navigation integration.
10. Deep regression tests, documentation, cleanup, release build.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.
