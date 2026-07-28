# Phase 5M Product And Symbol Contract

## User Journey

The user searches by symbol or name, selects a bounded result, opens a canonical asset workstation, changes interval/range/surface state, inspects chart and source truth, and can move to or from Market Map and Research Memory.

Canonical route:

```text
/?view=asset&symbol=<SAFE_SYMBOL>&assetClass=<equity|etf|crypto>&interval=<SUPPORTED_INTERVAL>&range=<SUPPORTED_RANGE>&surface=<overview|chart|financials|news|sources>&mode=<fixture|cache|live-if-available>
```

Legacy `timeframe` remains a compatibility input but canonical links emit `interval` and `range`.

## Symbol Identity

Every supported identity carries:

- canonical symbol and normalized search symbol;
- name, asset class, exchange, currency, region;
- sector/industry for local equity taxonomy where present;
- base/quote asset for crypto pairs;
- provider symbol aliases;
- registry provider, source reference, source status, reviewed timestamp, caveat, and data gap.

The registry is bounded and deterministic. It is not presented as an authoritative complete exchange security master or current index-membership dataset.

## Search

- Query length: 1 to 64 characters.
- Allowed characters: letters, numbers, spaces, `.`, `-`, `_`, `/`, and `=`.
- Result limit: 1 to 20, default 8.
- Ranking order: exact canonical symbol, exact alias, symbol prefix, token/name prefix, then token/name containment.
- Stable tie-break: asset-class priority, canonical symbol.
- Duplicate aliases resolve to one canonical identity.
- Unsupported or ambiguous values do not silently fall back to AAPL/BTC.

## Workstation

First desktop viewport must show:

- symbol, name, exchange, asset class, currency;
- last available price/change or explicit unavailable state;
- requested and effective interval/range;
- nonblank chart in successful runtime or deterministic fixture mode;
- equity/ETF taxonomy and fundamentals availability or crypto pair/derivatives availability;
- symbol-scoped news availability;
- compact source/freshness/caveat strip;
- Research Memory handoff using an opaque public origin token.

## Failure Semantics

- `unknown-symbol`: no registry identity and no asset rows.
- `asset-class-mismatch`: canonical identity exists under another class.
- `unsupported-interval` or `unsupported-range`: no provider request is made with the rejected capability.
- `no-history`: identity remains visible; chart rows remain empty.
- `provider-error`: no fabricated quote/history.
- `cache-miss`: cache mode stays honest and does not make a live request.
- `stale`: original provider fetch time is retained.
- `fixture`: deterministic symbol-specific synthetic rows only.

Outputs are read-only research information, not advice or execution.

