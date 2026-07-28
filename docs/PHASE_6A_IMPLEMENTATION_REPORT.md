# Phase 6A Implementation Report

Updated: 2026-07-01

## Delivered

- atomic versioned Market Map snapshots and bounded retention;
- explicit refresh CLI, single-flight behavior, structured health, and
  last-known-good failure semantics;
- compact first-paint payload and exact-symbol detail route;
- ETag, 304, Cache-Control, stale, unavailable, and schema mismatch states;
- SEC company facts with period/unit/form/filed/accession provenance;
- Alpha Vantage/Finnhub reported and scheduled earnings truth;
- visible snapshot age, refresh duration, provider-call count, and amber stale
  state;
- Market Map -> AAPL -> return state preservation;
- controlled online, stale, and API-invalid offline browser harness.

## Main Files

- `lib/market_snapshot_store.py`
- `scripts/refresh_market_snapshot.py`
- `lib/sec_edgar_provider.py`
- `lib/equity_provider_breadth.py`
- `lib/symbol_intelligence.py`
- `lib/api_contracts.py`
- `backend/api/app.py`
- `apps/web/src/components/MarketMapScreener.tsx`
- `apps/web/src/components/SymbolWorkstation.tsx`
- `apps/web/scripts/capture-phase6a.mjs`
- `tests/test_phase6a_market_snapshot.py`
- `tests/test_phase6a_sec_facts_calendar.py`

## Commands

```powershell
python scripts/refresh_market_snapshot.py --period 1y --retention 5
python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8004
npm --prefix apps/web run start -- --hostname 127.0.0.1 --port 3045
```

The commercial product remains Next.js/FastAPI/reusable `lib/`; Streamlit remains
the internal lab.

