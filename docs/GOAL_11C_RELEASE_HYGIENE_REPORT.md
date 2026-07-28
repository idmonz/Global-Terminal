# Goal 11C Release Hygiene Report

Generated: 2026-06-14T11:20:58+00:00

## required exclusions

- external folders and archives
- `data/private/`
- `data/cache/`
- SQLite DB files
- environment files except `.env.example`
- `.streamlit/secrets.toml`
- provider probe outputs
- logs
- pycache and pytest cache
- generated distribution artifacts
- external reference project names and source trees

## validation

- `tests/test_goal11c_release_hygiene.py` verifies release file names exclude private/external/generated artifacts.
- `tests/test_goal11c_no_external_source_copy.py` verifies runtime files do not refer to external source tree names.
- `scripts/build_release_zip.py` already excludes private data, external trees, generated artifacts, and secrets.

## final status

PASS after final validation sequence.
