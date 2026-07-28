# Goal 10 Release Hygiene Report

Release package policy includes:

- Include `.gitignore`, `.env.example`, `requirements.txt`, `requirements-openbb.txt`, app, lib, pages, tests, scripts, docs, and static files.
- Exclude `.env`, `.env.*` except `.env.example`, `.streamlit/secrets.toml`, logs, pycache, caches, provider probe result JSON, private data, dist, external source archives, and reference source trees.
- Keep OpenBB, WorldMonitor, OpenAlice, Fincept, finvizfinance, BB-Terminal, and quant-traderr-lab source/archive files out of release packages.

Verified by `tests/test_release_archive_hygiene.py` and `tests/test_release_archive_hygiene_goal10.py`.

## Goal 10 Build Result

- Release build command: `python scripts/build_release_zip.py`
- Release archive: generated under `dist/`
- Files packaged: 449 in the verification build
- Release hygiene tests: passed
- Safe cleanup execute: completed; two generated Streamlit log files were skipped because Windows reported active file locks. `*.log` remains excluded from release archives.
