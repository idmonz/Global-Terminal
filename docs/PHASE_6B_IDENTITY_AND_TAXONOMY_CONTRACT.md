# Phase 6B Identity And Taxonomy Contract

Updated: 2026-07-01

## Identity

`lib/market_identity.py` defines `market_identity.v1`.

Each accepted identity preserves:

- symbol and normalized symbol;
- name, asset/security type, exchange, and MIC;
- Nasdaq Trader listing status, source URL, source state, and as-of;
- SEC CIK, exchange, source URL, and source state when matched;
- identity conflict flag;
- explicit `authoritative_index_membership=false`.

The reconciliation deterministically excludes invalid symbols, flagged/inactive
listings, unsupported venues, warrants, rights, units, preferred/preference
shares, and depositary preferred shares. Common ADR/ADS and ordinary shares remain
eligible when the market provider and official listing agree.

## Observation

`yahoo_us_market_snapshot.v2` uses at most three pages of 250 rows, sorted by
market capitalization with a 500 million USD query floor. Duplicate symbols are
removed. The final 2026-07-01 observation was:

- provider candidates: 750;
- official supported identity matches: 333;
- excluded/unverified candidates: 417;
- request-time per-symbol calls: zero.

These are delayed public screener observations, not exchange realtime quotes.

## Classification

`yahoo_sector_classification.v2` issues at most 11 sector queries and intersects
the results with accepted identities.

Evidence layers remain separate:

1. 60 reviewed local sector/industry rows: `static/proxy`;
2. 273 Yahoo sector-query memberships: `provider-classification`;
3. project canonical sector labels: a transparent mapping over raw provider
   sector names;
4. raw provider sector: preserved;
5. official GICS/SIC/index membership: not claimed.

Final coverage:

- sector classification: 333/333;
- reviewed industry: 60/333;
- canonical sectors: 11;
- source conflict: 1 (`UBER`, local Industrials versus provider Technology),
  retained rather than silently overwritten.

