# Phase 6K Execution Plan

Updated: 2026-07-10
Status: completed

## Objective

Deliver one tenant-owned watchlist-to-research-to-in-app-inbox journey with
explicit local import consent, Account A/B isolation, and honest offline and
delivery-unavailable states.

## Scope

1. Preflight, threat model, official research, and external clean-room audit.
2. Import preview/consent and tenant-owned watchlist contracts.
3. Existing research/change evidence link and tenant-safe in-app inbox.
4. Same-origin API/UI journey with accessibility and mobile behavior.
5. Isolation, conflict, dedupe, retention, performance, visual, and release QA.

## Completion Evidence

- [x] Re-read durable goal, six skills, harness, Phase 6J reports, and Phase 6K prompt.
- [x] Full baseline, web/release gates, 28-archive audit, official research, and visual comparison.
- [x] Baseline and failing trust-boundary tests.
- [x] Backend, storage, API, and web journey.
- [x] Visual/performance/security/release proof.
- [x] Reports and next evidence-selected goal.

## Decisions

- Anonymous/local use remains useful and provider-call-free.
- Import is previewed and explicitly consented; no automatic upload.
- Server session derives tenant identity on every operation.
- Existing Phase 6D-6I research engines are reused.
- External delivery, checkout, broker action, and hosted success stay unavailable.

The durable master goal remains active.
