# Provider Probe Script Split

Goal 10B keeps `scripts/run_provider_probes.py` and adds suite-specific probes.

## Scripts

- `scripts/probe_openbb_runtime.py`
- `scripts/probe_provider_matrix.py`
- `scripts/probe_macro_energy_sources.py`
- `scripts/probe_crypto_sources.py`
- `scripts/probe_news_osint_sources.py`

## Behavior

- All scripts support `--dry-run`.
- All scripts support `--output` JSON.
- Missing keys are nonfatal.
- OpenBB is optional.
- Crypto probes are dry-run by default and document rate-limit care.
- News/OSINT probes explicitly prevent fake live AIS/flight/FIRMS claims.

`scripts/run_provider_probes.py --suite <name>` dispatches to the split suites.
