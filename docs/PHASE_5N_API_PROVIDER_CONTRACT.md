# Phase 5N API And Provider Contract

## Additive Workstation Fields

The existing `phase_2b.v1` `symbol_workstation` envelope remains valid and gains:

- `market_clock`
- `chart_views`
- `technical_analysis`
- `comparison`
- `financial_context`
- `exact_news`
- `crypto_derivatives`
- `panel_readiness`

The compatibility fields `history`, `quote`, `chart_specs`, `fundamentals`, `crypto_context`, `news`, and `source_register` remain.

## Provider Order

| Panel | Free-first provider | Cache policy | Failure behavior |
| --- | --- | --- | --- |
| Equity/ETF OHLCV | yfinance public adapter | symbol/interval/range, 15 min | stale or explicit unavailable |
| Crypto OHLCV | Binance USD-M public klines | symbol/interval/range, 5 min | stale or explicit unavailable |
| Financial context | yfinance statements/info | symbol/panel/version, 6 h | taxonomy plus unavailable gap |
| SEC identity | SEC public ticker registry | registry/version, 24 h | missing-user-agent or unavailable |
| Exact news | yfinance symbol news | symbol/panel/version, 15 min | exact-news-empty/unavailable |
| Crypto derivatives | Binance USD-M public endpoints | symbol/panel/version, 2-5 min | partial rows plus endpoint gaps |
| Comparison | same approved history providers | both symbols/interval/range/version | explicit overlap/provider gap |

Cache keys include asset class, symbol, interval, range, panel family, comparison symbol where relevant, and formula version.

## Safety

- No `.env` value, provider client, exception object, DataFrame, Path, local cache path, or private identifier crosses the API boundary.
- Current retrieval cannot convert an old market observation into a current quote claim.
- Live failure cannot silently fall back to fixture data.
- Unsupported liquidation, estimates, holdings, or premium fields remain unavailable.

