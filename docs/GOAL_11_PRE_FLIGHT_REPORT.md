# Goal 11 Pre-Flight Report

## Baseline test status

- `python scripts/run_smoke_tests.py`: passed.
- `python -m pytest -q`: passed before Goal 11 implementation.
- Static universe row counts:
  - `static/index_constituents/sp500.csv`: 60 rows, pass.
  - `static/index_constituents/nasdaq100.csv`: 30 rows, pass.
  - `static/index_constituents/korea_watchlist.csv`: 24 rows, pass.

## Canonical guard verification

Most canonical functions were present. Two Goal 11 guard aliases were missing in the baseline and were added as compatibility wrappers without altering existing behavior:

- `lib.live_news_event_pipeline.build_news_event_stream` wraps `build_live_news_event_pipeline`.
- `lib.global_volatility_monitor.build_global_volatility_payload` wraps `build_global_volatility_monitor`.

## Release hygiene baseline

The baseline release builder already excluded `external/`, `data/`, cache files, logs, `.env`, `.streamlit/secrets.toml`, and generated Python artifacts. Goal 11 expanded the external source token exclusions to include `agent-skills-main`, `agent-skills`, `osiris`, and `optlib`.

## Proceed decision

Proceed. Baseline tests passed and canonical alias gaps were non-destructive compatibility additions.

