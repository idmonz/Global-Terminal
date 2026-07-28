from __future__ import annotations

import os
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .endpoint_catalog import build_internal_endpoint_catalog
from .openbb_bridge import OPENBB_CAVEAT, get_openbb_version, is_openbb_installed
from .openbb_endpoint_resolver import build_endpoint_resolution_report, resolve_openbb_endpoint_path


def detect_openbb_runtime_capabilities(root: Any | None = None, endpoints: list[str] | None = None) -> list[dict[str, Any]]:
    installed = is_openbb_installed() or root is not None
    catalog = build_internal_endpoint_catalog()
    rows = []
    for endpoint in endpoints or sorted(catalog):
        definition = catalog[endpoint]
        if not definition.openbb_candidate_paths:
            continue
        report = resolve_openbb_endpoint_path(endpoint, root=root)
        configured_keys = [key for key in definition.optional_provider_keys if os.getenv(key)]
        rows.append(
            {
                "endpoint": endpoint,
                "cataloged": True,
                "runtime_available": bool(report.get("available")),
                "selected_path": report.get("selected_path"),
                "openbb_installed": installed,
                "openbb_version": get_openbb_version() if installed and root is None else "mock" if root is not None else None,
                "provider_key_configured": bool(configured_keys) if definition.optional_provider_keys else True,
                "missing_optional_keys": [key for key in definition.optional_provider_keys if key not in configured_keys],
                "fallback": ", ".join(definition.native_providers) or "data gap",
                "caveat": definition.caveat or OPENBB_CAVEAT,
                "sample_query_status": "not_run",
                "reason": report.get("reason"),
            }
        )
    return rows


def build_runtime_capability_matrix(root: Any | None = None, endpoints: list[str] | None = None):
    rows = detect_openbb_runtime_capabilities(root=root, endpoints=endpoints)
    return pd.DataFrame(rows) if pd is not None else rows


def compare_catalog_vs_runtime(root: Any | None = None):
    catalog = build_internal_endpoint_catalog()
    runtime_rows = detect_openbb_runtime_capabilities(root=root)
    runtime_by_endpoint = {row["endpoint"]: row for row in runtime_rows}
    rows = []
    for endpoint, definition in catalog.items():
        runtime = runtime_by_endpoint.get(endpoint, {})
        rows.append(
            {
                "endpoint": endpoint,
                "cataloged": True,
                "has_openbb_candidate": bool(definition.openbb_candidate_paths),
                "runtime_available": bool(runtime.get("runtime_available")),
                "native_fallback": ", ".join(definition.native_providers) or "data gap",
                "gap": bool(definition.openbb_candidate_paths and not runtime.get("runtime_available")),
                "caveat": definition.caveat or OPENBB_CAVEAT,
            }
        )
    return pd.DataFrame(rows) if pd is not None else rows


def build_openbb_endpoint_gap_table(root: Any | None = None):
    matrix = build_runtime_capability_matrix(root=root)
    if pd is None:
        return [row for row in matrix if not row.get("runtime_available")]
    if matrix.empty:
        return matrix
    return matrix[~matrix["runtime_available"]].reset_index(drop=True)


def build_openbb_provider_key_gap_table():
    rows = []
    for endpoint, definition in build_internal_endpoint_catalog().items():
        for key in definition.optional_provider_keys:
            rows.append(
                {
                    "endpoint": endpoint,
                    "env_var": key,
                    "configured": bool(os.getenv(key)),
                    "required_for_base_launch": False,
                    "caveat": "Optional provider key. Secret values are never displayed.",
                }
            )
    if pd is None:
        return rows
    return pd.DataFrame(rows)


def build_endpoint_resolution_matrix(root: Any | None = None, endpoints: list[str] | None = None):
    return build_endpoint_resolution_report(root=root, endpoints=endpoints)
