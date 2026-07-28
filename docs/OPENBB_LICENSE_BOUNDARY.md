# OpenBB License Boundary

OpenBB is treated as an optional external dependency.

## Rules

- Do not copy OpenBB source into `lib/`.
- Do not vendor OpenBB source trees or archives into release packages.
- Do not add OpenBB to mandatory `requirements.txt`.
- Use `requirements-openbb.txt` for optional installs.
- Do not require paid API keys for base launch.
- Do not claim paid provider data is free.

## Release Boundary

`scripts/build_release_zip.py` excludes `external/`, generated artifacts, caches, private data, secrets, and source archives. Goal 8 adds `requirements-openbb.txt` and `.env.example` to the release include list while keeping OpenBB source outside the package.

## Goal 9 Boundary

The OpenBB-compatible endpoint catalog is project-native metadata. It does not copy OpenBB source code and does not add OpenBB to mandatory base requirements.

OpenBB source archives and external trees remain excluded from release packages.
