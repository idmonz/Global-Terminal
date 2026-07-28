# OpenBB Optional Backend Bridge

Goal 8 adds an optional OpenBB bridge through:

- `lib/openbb_bridge.py`
- `lib/openbb_catalog.py`
- `lib/openbb_data_mapper.py`
- `lib/openbb_provider_adapter.py`
- `lib/openbb_diagnostics.py`
- `lib/openbb_screener_backend.py`

The bridge uses lazy imports only. If OpenBB is missing, functions return `DataResult` warnings and the native provider path remains available.

## Result Metadata

OpenBB results carry:

- `provider`
- `source`
- `command`
- `warning`
- `error`
- `caveat`
- `is_openbb`
- `is_optional`
- `requires_key`
- `fallback_used`

## Source Modes

- Auto: use the safe local policy for the app area.
- Native only: do not call OpenBB.
- OpenBB preferred: try OpenBB, then native fallback where allowed.
- OpenBB only: do not silently fallback.

OpenBB is an optional backend. Provider availability, licensing, data rights, and API key requirements must be verified by the user before production or commercial use.

## Goal 9 Bridge Expansion

Goal 9 adds:

- `lib/openbb_endpoint_resolver.py`
- `lib/openbb_real_probe.py`
- `lib/openbb_capability_runtime.py`

Runtime probes remain button-triggered. Missing OpenBB returns graceful skipped/warning payloads and native providers remain available.
