# WorldMonitor Reference Boundary

This repository may contain `external/worldmonitor-main` for local inspection only.

## Runtime Boundary

- Runtime code must not import from `external/worldmonitor`.
- Runtime code must not depend on WorldMonitor source files.
- Private or pro-gated WorldMonitor surfaces are not scraped.
- Optional WorldMonitor API integration is allowed only through explicit configuration such as `WORLD_MONITOR_BASE_URL`.

## Release Boundary

- `.gitignore` excludes `external/`.
- `scripts/build_release_zip.py` excludes `external/`.
- Goal 6 docs and UI describe WorldMonitor as a conceptual reference only.
