# Goal 10B Release Hygiene Report

## Included

- `.gitignore`
- `.env.example`
- `requirements.txt`
- `requirements-openbb.txt`
- `app.py`
- `lib/`
- `pages/`
- `tests/`
- `scripts/`
- `docs/`
- `static/`

## Excluded

- `external/`
- external source/archive tokens including OpenBB, WorldMonitor, OpenStock, OpenAlice, Fincept, finvizfinance, Bloomberg-terminal, BB-Terminal, and quant-traderr variants
- `_recovery/`
- `data/cache/`
- `data/private/`
- provider probe result JSON
- pycache, pytest cache, compiled Python, logs
- `.env`, `.env.*` except `.env.example`
- virtual environments
- Streamlit secrets

Release hygiene is enforced by `scripts/build_release_zip.py` and tests.
