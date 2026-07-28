# Phase 5F Data Realness And Provider Plan

Updated: 2026-06-19

## Policy

Free-first does not mean pretend-live. Every capability is assigned a provider, cache policy, latency expectation, legal/ToS note, and explicit failure state.

## Provider Matrix

| Domain | Existing/free-first path | Current truth | Next action |
|---|---|---|---|
| Equity price/history | yfinance-compatible path | optional/unofficial, may fail or delay | wrap diagnostics, symbol/timeframe runtime tests |
| SEC filings | SEC EDGAR | keyless with compliant user agent | expose filings/metadata contract |
| Fundamentals | yfinance/OpenBB optional | partial/provider-dependent | add observed fields only; full statements provider-required |
| Equity universe | native taxonomy/FinanceDatabase-inspired schema | schema/reference only | use licensed package or provider-backed universe after terms review |
| Crypto spot | CoinGecko, Binance public | real keyless path exists | symbol/timeframe route and cache telemetry |
| Crypto derivatives | Binance public endpoints | partial real path | normalize OI/funding/basis with rate-limit states |
| DeFi/on-chain | DefiLlama | keyless partial | expose protocols/chains with source timestamps |
| Options | user-supplied chain, optional yfinance/OpenBB | provider-required for live chain | build chain ingestion first; no fake GEX |
| Macro | World Bank, Treasury Fiscal, selected SDMX | real keyless paths exist | dedicated macro series contract |
| FRED | API key | missing-key unless configured | setup guide and health check |
| Energy | EIA API key, public reports/RSS | key/provider-dependent | do not claim live fundamentals without key |
| Weather | Open-Meteo, NWS | keyless/public paths exist | connect relevant event layers |
| Earthquakes | USGS | real keyless path exists | map density, clustering, timeline |
| News | RSS/GDELT | real but rate-limit/403 prone | feed-level health, dedupe, entity linking |
| Flights | OpenSky OAuth | credential-dependent | validate OAuth and quota; explicit unavailable otherwise |
| AIS | NOAA AccessAIS for bounded use | limited geography/use | keep global AIS unavailable without licensed source |
| Sanctions | registry/schema only | unavailable | evaluate official OFAC/EU/UN feeds and licenses |
| AI summary | Gemini free-first | optional/missing-key | source-bound summaries; search grounding opt-in |

## Status Contract

Provider and row status must be one of:

`live/fresh`, `cached`, `stale`, `fixture`, `proxy/static`, `missing-key`, `provider-required`, `rate-limited`, `forbidden`, `unavailable`, `error`.

Every source-bearing row includes provider, source URL, fetched timestamp, freshness, confidence, caveat, and data gap.

## Cache And Refresh

| Data | Suggested TTL | Stale fallback |
|---|---:|---:|
| quote/crypto ticker | 15-60 sec | 5-15 min |
| intraday bars | 1-5 min | 1 hour |
| daily bars | 1-6 hours | 2 days |
| fundamentals/filings | 6-24 hours | 7 days |
| news | 2-10 min | 2 hours |
| map events | 1-15 min by source | source-specific |
| provider catalog | 1 hour | 1 day |

Single-flight, request timeout, bounded retries, provider circuit state, and last-success metadata are required.

## Runtime Mode UX

- The B2C default is `live-if-available` with visible cached/stale fallback.
- `fixture` lives under Demo/Diagnostics, not as the primary home experience.
- A runtime failure does not replace the selected symbol or clear the page; it keeps the last usable row and shows age/reason.
- Provider setup is actionable but never exposes secret values.

## Commercial Provider Evolution

1. Ship free-first sources and user-supplied keys.
2. Measure reliability, latency, and coverage.
3. Add licensed vendors only for gaps users repeatedly hit.
4. Preserve provider portability at the normalized contract boundary.
5. Keep entitlements separate from analytical calculations.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
