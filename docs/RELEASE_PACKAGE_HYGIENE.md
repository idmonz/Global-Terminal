# Release Package Hygiene

`scripts/build_release_zip.py` now includes `.gitignore` and excludes external references, private data, caches, generated artifacts, logs, secrets, virtual environments, and recovery folders.

`tests/test_release_archive_hygiene.py` builds a release zip and verifies:

- `.gitignore`, app, requirements, pytest config, core lib/pages/scripts/docs/tests/static entries are present.
- `external/`, `data/cache/`, `data/private/`, pycache, pyc/pyo/log files, `.env`, and `.streamlit/secrets.toml` are absent.

Release packages remain self-contained for the app source while keeping optional/private/generated files out.
