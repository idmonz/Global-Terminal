# Goal 11D Release Hygiene Report

- created_at_utc: `2026-06-14T12:36:22+00:00`
- compileall: PASS
- smoke tests: PASS
- pytest: PASS
- collected tests: 416
- safe cleanup dry-run: PASS, 7 generated artifact targets
- safe cleanup execute: PASS, 7 generated artifact targets removed
- release build: PASS
- final release package file count: 827

## Exclusion coverage

Release excludes:

- external/
- data/private/
- data/cache/
- *.db / *.sqlite / *.sqlite3
- .env / .env.* except .env.example
- .streamlit/secrets.toml
- provider probe results
- logs
- pycache
- external archives
- node_modules
- Kronos / QuantDinger / tensortrade / worldview archives and source folders

No broad shell deletion was used; cleanup used `scripts/safe_cleanup_generated_artifacts.py`.
