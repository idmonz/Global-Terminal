# GOAL 12A Release Hygiene Report

## Required inclusions

- `.gitignore`
- `.env.example`
- `app.py`
- `requirements.txt`
- `requirements-openbb.txt`
- `README.md`
- `lib/`
- `pages/`
- `tests/`
- `scripts/`
- `docs/`
- `static/`

## Exclusions enforced by build script

- `external/`
- private/cache data
- SQLite DB files by path policy and generated/private exclusion
- secrets files
- logs and pycache after cleanup
- external archives/source trees
- model weights and ML cache/checkpoints by name/path exclusion policy

## Goal 12A release status

Final gate results are recorded in `GOAL_12A_FINAL_REPORT.md` after compileall, smoke, pytest, safe cleanup, and release build.

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.


## Final gate results

- compileall: passed
- smoke tests: passed
- full pytest: passed; 485 collected tests after Goal 12A additions.
- safe cleanup dry-run: would remove 7 generated artifact(s)
- safe cleanup execute: removed 7 generated artifact(s)
- release build: passed.

```text
release build: passed
files selected before manifest: 922
zip entries after manifest: 923
files packaged: 922
```
