# GOAL 12D Release Hygiene Report

## Commands run

```text
python -m compileall -q app.py lib pages scripts tests
python scripts/run_smoke_tests.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python scripts/safe_cleanup_generated_artifacts.py --dry-run
python scripts/safe_cleanup_generated_artifacts.py --execute
python scripts/build_release_zip.py
```

## Results

- compileall: passed.
- smoke tests: passed.
- full pytest: 576 collected tests passed.
- safe cleanup dry-run: completed.
- safe cleanup execute: removed `tests/__pycache__`, `scripts/__pycache__`, `pages/__pycache__`, `lib/__pycache__`, `data/cache`, `__pycache__`, `.pytest_cache`.
- release build before final doc refresh: 1080 files selected, 1081 zip entries after manifest.

## Exclusion confirmations

The release build script excludes:

- `external/`
- `data/private/`
- `data/private/options_cases/`
- `data/cache/`
- uploaded CSV/local option files under excluded data paths
- `*.db`, `*.sqlite`, `*.sqlite3`
- `.env` and `.env.*` except `.env.example`
- `.streamlit/secrets.toml`
- logs and pycache
- external archives/source trees
- model weights and ML checkpoints

## Inclusion confirmations

The release includes `.env.example`, core app files, requirements files, README, `lib/`, `pages/`, `tests/`, `scripts/`, `docs/`, and `static/`.
