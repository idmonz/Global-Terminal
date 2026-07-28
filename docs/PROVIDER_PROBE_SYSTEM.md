# Provider Probe System

Goal 10 provider probes are lightweight diagnostics.

## Modules

- `lib.provider_probe_runner`
- `lib.provider_probe_store`
- `lib.provider_probe_visuals`
- `lib.provider_health_engine`
- `scripts/run_provider_probes.py`

## Behavior

- `--dry-run` never requires internet, OpenBB, API keys, or writes.
- Missing keys are nonfatal and visible.
- Results save only to gitignored private storage when explicitly requested.
- Provider Center and OpenBB Data Hub expose probe summaries.

Provider probes are lightweight diagnostics. Missing API keys, rate limits, and provider outages may affect availability.

## Goal 10B Split Scripts

- `scripts/probe_openbb_runtime.py`
- `scripts/probe_provider_matrix.py`
- `scripts/probe_macro_energy_sources.py`
- `scripts/probe_crypto_sources.py`
- `scripts/probe_news_osint_sources.py`

`scripts/run_provider_probes.py --suite <suite>` can dispatch to the split probes. All split scripts support `--dry-run` and `--output`; missing keys remain nonfatal.

## Goal 11 Update

Goal 11 adds a local Personal Research Operating System layer. It stores private workspace state in SQLite under `data/private/`, adds watchlist/alerts/reports/strategy decision-log workflows, links OSINT/provider context to watchlist records, and remains manual, research-only, and release-hygiene controlled. No external source code, external folders, private DBs, secrets, live trading, broker execution, or background automation are included in release artifacts.
