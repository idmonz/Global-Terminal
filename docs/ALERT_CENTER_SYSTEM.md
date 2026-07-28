# Alert Center System

## Purpose

Alert Center provides manual, button-triggered research alert evaluation. It is not a background daemon and does not send email or push notifications.

## V2 behavior

Goal 11B adds:

- `resolve_alert_metric()`
- `build_alert_data_context()`
- `evaluate_alert_with_state()`
- `apply_alert_cooldown()`
- `apply_alert_expiry()`
- `dedupe_alert_event()`
- `classify_alert_transition()`
- `build_alert_evaluation_batch()`
- `build_alert_review_queue()`

## State policy

Alert events store source snapshot, freshness, confidence, transition type, dedupe status, cooldown status, and data-gap reason inside metadata. Missing metrics create `skipped_data_gap` results and never create a false trigger.

## Tests

Covered by `tests/test_goal11b_alert_state_machine.py`.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.
