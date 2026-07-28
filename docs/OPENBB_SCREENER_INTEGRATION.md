# OpenBB Screener Integration

`lib/openbb_screener_backend.py` adds optional OpenBB-backed stock and ETF screener support.

The native screeners remain the default fallback. Crypto, bonds/rates, commodities, and cross-asset screeners remain native-only unless future OpenBB mappings are added.

The Screener page now exposes:

- source mode
- OpenBB installed/fallback status
- factor presets
- source/data quality fields
- CSV export
- links to Stock Analyzer, Financial Terminal, and Portfolio Quant Lab

Screener outputs use neutral labels such as research candidate and watchlist context.
