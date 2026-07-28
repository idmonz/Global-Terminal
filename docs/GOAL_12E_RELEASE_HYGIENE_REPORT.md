# Goal 12E Release Hygiene Report

## Commands

```text
python scripts/safe_cleanup_generated_artifacts.py --dry-run
python scripts/safe_cleanup_generated_artifacts.py --execute
python scripts/build_release_zip.py
```

## Cleanup result

Safe cleanup removed generated artifact groups: tests/__pycache__, scripts/__pycache__, pages/__pycache__, lib/__pycache__, data/cache, __pycache__, and .pytest_cache.

## Release build result

```text
files selected before manifest: 1110
zip entries after manifest: 1111
files packaged: 1110
```

## Exclusion status

The release excludes external archives/source trees, private data, data/private/options_cases, case_index.json, surface_review_queue.json, uploaded CSVs, local option-chain/book files, DBs, SQLite files, .env secrets, .streamlit secrets, provider probe results, logs, pycache, node_modules, model weights, HuggingFace cache, TensorFlow checkpoints, and Torch checkpoints.
