# Phase 5M Web Implementation Report

Updated: 2026-06-22

## Delivered Journey

Phase 5M replaces the AAPL/BTCUSDT-only boundary with a bounded universal symbol journey:

1. Search 90 reviewed identities by symbol, alias, or name.
2. Open a canonical equity, ETF, or crypto route.
3. Request provider-supported interval/range history.
4. See live/fresh, cached, stale, fixture, cache-miss, unsupported, or unknown state.
5. Continue to Market Map, Options Quant, or Research Memory without cross-symbol substitution.

## Runtime And Contracts

- `lib/symbol_workstation.py` owns symbol identity, ranking, capability, cache, provider normalization, fixture generation, and presentation contracts.
- The bounded registry contains 60 reviewed equities, 10 project-native ETFs, and 20 reviewed crypto pairs.
- Equity/ETF history uses the existing yfinance path. Crypto history uses the public Binance USD-M kline path.
- Cache keys include asset class, symbol, interval, and range. Cache mode does not refresh. Stale fallback preserves the original provider timestamp.
- Deterministic fixture history is generated independently per symbol. Unknown or unsupported requests never receive AAPL/BTC rows.
- Additive `phase_2b.v1` payloads are exposed at `/api/symbol-directory` and `/api/symbol-workstation`.

## Web Product

- `SymbolSearch.tsx` provides bounded ranked results and canonical navigation.
- `SymbolWorkstation.tsx` provides identity, price/change, interval/range controls, chart, source truth, fundamentals/crypto context, and cross-workspace actions.
- Market Map rows and Research Memory watchlists now drill into the correct symbol.
- The canonical route preserves `symbol`, `assetClass`, `interval`, `range`, `surface`, and `mode`.
- Unknown symbols and provider/cache failures have explicit product states.

## Chart Reliability Fix

Visual QA exposed duplicate intraday timestamps because one-hour observations were collapsed to dates. `FinanceChart.tsx` now preserves UTC timestamps, sorts and de-duplicates points, exposes intraday time labels, and uses a single managed resize lifecycle. BTCUSDT and ETHUSDT now render 121 distinct one-hour points without browser exceptions.

## Principal Files

- `lib/symbol_workstation.py`
- `lib/api_contracts.py`
- `backend/api/app.py`
- `scripts/export_api_fixtures.py`
- `apps/web/src/lib/contracts.ts`
- `apps/web/src/lib/fixtures.ts`
- `apps/web/src/lib/product-routes.ts`
- `apps/web/src/components/SymbolSearch.tsx`
- `apps/web/src/components/SymbolWorkstation.tsx`
- `apps/web/src/components/FinanceChart.tsx`
- `apps/web/src/components/MarketMapScreener.tsx`
- `apps/web/src/components/ResearchMemoryWorkstation.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`

No paid provider, broker path, recommendation engine, hosted auth, billing, or private-data URL field was added.
