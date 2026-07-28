# Live Data Provider Center

The Data Provider Center is implemented in `pages/17_Data_Provider_Center.py`.

## Modules

- `lib/provider_registry.py`: central provider definitions and capability matrix.
- `lib/provider_diagnostics.py`: optional-key checks, mocked/testable connection probes, health summary, errors, freshness, latency, rate-limit notes, and data gaps.
- `lib/live_feeds.py`: polling abstractions for RSS, GDELT, USGS, EIA, Binance, CoinGecko, AIS status, OpenSky status, and optional WorldMonitor panels.
- `lib/realtime_connectors.py`: optional connector skeletons that do not run on app launch.

## Base Launch

No paid API is required. Optional providers remain visible but clearly marked unconfigured or unavailable.

## Goal 8 OpenBB Provider Family

- Provider Center lists OpenBB as an optional backend family.
- OpenBB installation, version, optional provider-key status, capability catalog, and caveat are visible.
- Sample OpenBB probes are button-triggered and not run automatically on page load.
- Secret values are never displayed.

## Goal 9 Provider Alignment

Provider diagnostics can be compared against the unified endpoint catalog and OpenBB runtime capability matrix.

OpenBB, EIA, FRED, AIS, and paid providers remain optional. Missing keys are surfaced as data gaps without exposing values.
# Goal 10 Update

Data Provider Center now includes:

- Real Provider Probe Center.
- No-Key / Free Official Sources table.
- Environment status table with masked values only.
- Free API setup checklist.

Probe results are optional, lightweight, and stored only in gitignored private paths when explicitly saved.

## Goal 10B Update

Data Provider Center now displays provider health heatmap metadata and split probe script commands for OpenBB runtime, provider matrix, macro/energy, crypto, and news/OSINT diagnostics. Missing keys remain visible and nonfatal.
