# Phase 6F Research Snapshot Contract

Updated: 2026-07-03

## Contract

`research_snapshot.v1` is the bounded, public-normalized list research boundary.
It is produced by the existing watchlist materialization workflow and reused by
the Watchlist and exact-symbol Catalyst panel.

Maximum scope:

- five exact equity identities;
- one yfinance multi-history request;
- five Alpha Vantage overview requests;
- five Finnhub earnings requests;
- five Finnhub exact company-news requests;
- 16 provider calls in the worst allowed refresh.

Fresh provider cache is read before calls are spent. Failed refreshes may retain
same-symbol last-known-good data as `stale`; they cannot relabel it
`live/fresh`.

## Row Requirements

Each saved row may include:

- exact identity and asset class;
- quote, performance, risk, and technical metrics;
- normalized fundamentals and dividend fields;
- earnings/dividend events;
- strict exact-symbol news evidence;
- provider/source URL, fetched/as-of clocks, source status, confidence, caveat,
  and data gap.

Null remains null. Missing earnings, dividends, news, or fundamentals are shown
as unavailable and are never converted to zero or fabricated rows.

## Budget Ledger

The job records planned/actual calls by operation, cache hits, stale LKG hits,
failed/blocked/skipped calls, symbol counts, duration, queue/overlap state, and
next safe refresh. Response bodies, credentials, and private notes are never
metric labels.

## Privacy And Identity

Local-private watchlist reasons remain in the private database boundary. They
are excluded from jobs, public API payloads, fixtures, URLs, logs, screenshots,
AI context, and release archives. Exact-symbol caches cannot be reused across
symbols, and deterministic fixture mode cannot silently mix provider cache.

## Delivery

The Watchlist reads already-materialized rows for Price, Performance, Risk,
Financials, Technicals, and Catalysts. Mode, sort, and group changes make zero
request-time provider calls. The full workstation loads the exact Catalyst
panel additively and preserves a sanitized return state.
