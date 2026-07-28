# Phase 5G API And Data Contract

## Inputs

- `symbol`: validated uppercase market identifier.
- `asset_class`: `equity` or `crypto`.
- `timeframe`: allowlisted display interval.
- `mode`: `fixture`, `cache`, or `live-if-available`.

## Symbol Payload

Required sections:

- identity/context;
- quote and change;
- price/volume chart specs;
- equity fundamentals or crypto derivatives;
- related news/events;
- provider/source register;
- unavailable/data-gap rows;
- disclosure.

## Row Truth

Every source-bearing row exposes provider, source/source URL, fetched time or freshness, data state, caveat, data gap, confidence when calculated, and `not_financial_advice`.

Allowed states: live/fresh, cached, stale, delayed, fixture, static reference, proxy/estimated, provider-required, unavailable, user-supplied, error, rate-limited, forbidden.

## Determinism

Fixture export remains network-free and fixed to AAPL/BTCUSDT. Runtime provider failure never produces a fake live row.

## Adopted Boundary

Phase 5G reuses the existing `phase_2b.v1` market, equity, financial, options, crypto, news, and provider envelopes. It does not add another broad payload.

The Next.js runtime loader now receives a JSON-safe request context and adds `symbol` only to symbol-aware API routes. `assetClass` and `timeframe` remain URL/product context in this slice; existing Python providers retain their validated period/interval behavior. The UI does not claim that selecting a display timeframe changed a provider interval until the API supports it.

Supported deterministic product contexts are AAPL/equity and BTCUSDT/crypto. Other symbols are `unknown-symbol` until a provider-specific contract and tests exist.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
