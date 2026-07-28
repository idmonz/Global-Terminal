# Goal 11F Release Hygiene Report

## Inclusion policy

Release includes `.gitignore`, `.env.example`, `app.py`, requirements files, `README.md`, `lib/`, `pages/`, `tests/`, `scripts/`, `docs/`, and `static/`.

## Exclusion policy

Release excludes external references, external archives, private/cache data, local databases, local secret files, Streamlit secrets, provider probe results, logs, pycache, and generated artifacts.

## Environment files

- `.env.example`: included, placeholder-only.
- `.env`: excluded.
- `.env.*` except `.env.example`: excluded.

## Count terminology

- `selected_file_count_before_manifest`: project files selected before adding `release_manifest.json`.
- `manifest_entry_count`: one generated manifest entry.
- `expected_zip_entry_count_after_manifest`: selected files plus manifest.
- `actual_zip_entry_count_after_manifest`: archive entry count observed after package creation.

Final count is recorded in `docs/GOAL_11F_FINAL_REPORT.md` and `docs/RELEASE_PACKAGE_REPORT.md` after the release builder runs.

## Final release gate result

- compileall: PASS
- smoke tests: PASS
- full pytest: PASS
- collected tests: 447
- cleanup dry-run: PASS
- cleanup execute: PASS
- selected_file_count_before_manifest: 860
- manifest_entry_count: 1
- actual_zip_entry_count_after_manifest: 861
- release build: PASS
