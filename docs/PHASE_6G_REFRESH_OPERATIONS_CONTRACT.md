# Phase 6G Refresh Operations Contract

Updated: 2026-07-03

## Purpose

Expose enough local operational truth to answer:

1. Is refresh available and safe to run?
2. What happened on the last attempt and last success?
3. When is the next provider-safe refresh?
4. Did the job exceed budget, overlap, fail, or retain LKG?

## Required Fields

- operation version, mode, installed/running/readiness truth;
- last attempt, last success, previous success, and next eligible time;
- queue, busy/overlap, duration, symbol counts, and bounded event history;
- maximum/planned/actual calls by operation;
- cache, stale LKG, failure, blocked, and skipped counts;
- background kill switch and safe manual refresh action;
- source status, caveat, and data gap.

`installed_background_service` is always false unless an independently installed
service is directly verified. The script's existence is not installation.
Background refresh defaults disabled. Manual materialization remains bounded to
five symbols and 16 provider calls.

## Alert Readiness

The existing local-private alert store is reused with scope
`watchlist_change`. A rule must be explicitly enabled and includes minimum
severity, cooldown, optional expiry, and preview-only delivery metadata.

Candidates expose stable fingerprint, dedupe, cooldown, expiry,
acknowledgement, and kill-switch state. Preview events may be persisted locally
for audit/dedupe. No external notification is sent.
