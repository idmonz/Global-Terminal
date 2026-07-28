# Phase 5M API And Provider Capability Contract

## New Additive Payloads

### `symbol_directory`

Data:

- `identities`
- `search_contract`
- `asset_class_counts`
- `provider_capabilities`
- `readiness`

### `symbol_workstation`

Data:

- `workstations`
- `capabilities`
- `readiness`

Each workstation contains:

- `identity`
- `request`
- `quote`
- `history`
- `chart_specs`
- `fundamentals`
- `crypto_context`
- `news`
- `source_register`
- `unavailable_sources`
- `summary`

The deterministic static fixture includes symbol-specific workstations for the bounded registry. Runtime API responses contain only the requested symbol.

## Routes

```text
GET /api/symbol-directory?query=<SAFE_QUERY>&asset_class=<optional>&limit=<1..20>
GET /api/symbol-workstation?symbol=<SAFE_SYMBOL>&asset_class=<class>&interval=<interval>&range=<range>&runtime_mode=<fixture|cache|live-if-available>
```

## Capability Matrix

Equity/ETF free-first history:

- provider: yfinance delayed public history;
- intervals: `1d`, `1h`;
- ranges: `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`;
- cache TTL: 15 minutes;
- stale retention: 24 hours;
- source URL: Yahoo Finance symbol page;
- caveat: unofficial/free public adapter reliability and terms require user-visible caution.

Crypto free-first history:

- provider: Binance public market-data API;
- intervals: `15m`, `1h`, `4h`, `1d`;
- ranges: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`;
- cache TTL: 5 minutes;
- stale retention: 24 hours;
- no account or API key required for the selected public endpoint;
- caveat: exchange availability, regional access, pair listing, and rate limits can change.

Fixture:

- effective interval/range: `1d` / `3mo`;
- rows are deterministic and symbol-seeded;
- values are explicitly synthetic and cannot be treated as market observations.

## Cache Rules

- key includes `asset_class`, canonical symbol, provider symbol, interval, and range;
- fresh cache can serve without network;
- cache mode never refreshes;
- live-if-available refreshes and can retain stale cache after failure;
- stale rows retain the original `fetched_at`;
- cache stores public symbol history only, never notes, holdings, account IDs, or secrets.

## API Safety

- invalid symbols, classes, intervals, and ranges return explicit contract states;
- missing numeric values remain null;
- no DataFrame, Path, Streamlit, Plotly, provider client, exception object, secret, or private path crosses the envelope;
- source status, source URL, fetched time, caveat, and data gap remain visible.

