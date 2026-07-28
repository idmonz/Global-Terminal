# Phase 6D Next Goal Rationale

Updated: 2026-07-02

## Decision

Proceed to Phase 6E: Progressive Symbol Workstation And Advanced Watchlist View.

## Evidence

Phase 6D makes the daily list route fast and useful, but the handoff to the full
Symbol Workstation still transfers approximately 1.07 MB and eagerly composes
the broad workstation tree. The chart panel alone remains approximately 163 KB.
TradingView benchmark review also exposes missing list sorting/grouping and
performance/risk/fundamental overview modes.

## Phase 6E Priority

1. make the direct Symbol Workstation summary-first and progressively delivered;
2. keep chart in the first viewport while lazy-loading lower panels;
3. preserve exact identity, origin, ETag, source clock, and same-symbol cache;
4. add compact watchlist advanced columns/sort/group without broad fan-out;
5. fix API-base build/runtime configuration so offline and deployment behavior
   is explicit rather than dependent on a baked public environment value;
6. prove lower HTML/RSC/JS transfer and desktop/mobile online/offline behavior.

Hosted auth, billing, alert delivery, and always-on refresh remain later
commercial-platform work.
