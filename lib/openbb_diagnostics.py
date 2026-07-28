from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd

from .openbb_bridge import OPENBB_CAVEAT, get_openbb_version, is_openbb_installed, openbb_available_result, openbb_result_to_dict
from .openbb_capability_runtime import (
    build_openbb_endpoint_gap_table,
    build_openbb_provider_key_gap_table,
    build_runtime_capability_matrix,
    compare_catalog_vs_runtime,
)
from .openbb_catalog import build_openbb_capability_catalog, list_openbb_required_keys
from .openbb_real_probe import build_openbb_endpoint_probe_report, build_openbb_real_probe_report
from .openbb_provider_adapter import (
    get_openbb_company_profile,
    get_openbb_etf_info,
    get_openbb_options_chain,
    get_openbb_treasury_rates,
)


def openbb_installation_status() -> dict[str, Any]:
    installed = is_openbb_installed()
    return {
        "provider": "openbb",
        "installed": installed,
        "version": get_openbb_version() if installed else None,
        "backend_mode": "optional",
        "available": installed,
        "base_launch_required": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "caveat": OPENBB_CAVEAT,
    }


def openbb_provider_key_status() -> pd.DataFrame:
    return list_openbb_required_keys()


def openbb_capability_health_check() -> pd.DataFrame:
    catalog = build_openbb_capability_catalog()
    installed = is_openbb_installed()
    keys = list_openbb_required_keys().set_index("env_var") if not list_openbb_required_keys().empty else pd.DataFrame()
    rows = []
    for _, row in catalog.iterrows():
        missing_optional_keys = bool(row["requires_key"]) and not any(keys.get("configured", pd.Series(dtype=bool)).astype(bool)) if not keys.empty else bool(row["requires_key"])
        rows.append(
            {
                "app_area": row["app_area"],
                "domain": row["openbb_domain"],
                "endpoint": row["openbb_endpoint_label"],
                "openbb_installed": installed,
                "status": "ready_for_optional_probe" if installed and not missing_optional_keys else "optional_key_gap" if row["requires_key"] else "install_openbb_to_enable" if not installed else "ready_for_optional_probe",
                "native_fallback": row["native_fallback"],
                "caveat": row["caveat"],
            }
        )
    return pd.DataFrame(rows)


def _sample_query(label: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        result = fn()
        payload = openbb_result_to_dict(result)
        payload["sample"] = label
        return payload
    except Exception as exc:
        return {
            "sample": label,
            "ok": False,
            "provider": "openbb",
            "source": "sample diagnostic",
            "warning": "OpenBB sample query failed gracefully.",
            "error": str(exc),
            "caveat": OPENBB_CAVEAT,
            "fallback_used": True,
        }


def test_openbb_sample_equity_query() -> dict[str, Any]:
    return _sample_query("equity_profile_AAPL", lambda: get_openbb_company_profile("AAPL"))


def test_openbb_sample_macro_query() -> dict[str, Any]:
    return _sample_query("treasury_rates", get_openbb_treasury_rates)


def test_openbb_sample_etf_query() -> dict[str, Any]:
    return _sample_query("etf_info_SPY", lambda: get_openbb_etf_info("SPY"))


def test_openbb_sample_options_query() -> dict[str, Any]:
    return _sample_query("options_chain_SPY", lambda: get_openbb_options_chain("SPY"))


def build_openbb_diagnostics_table() -> pd.DataFrame:
    status = openbb_installation_status()
    available = openbb_available_result()
    rows = [
        {
            "check": "installation",
            "ok": status["installed"],
            "status": "installed" if status["installed"] else "not installed",
            "detail": status["version"] or "OpenBB optional package is not installed.",
            "fallback_path": "native providers remain active",
            "caveat": OPENBB_CAVEAT,
        },
        {
            "check": "backend mode",
            "ok": True,
            "status": "optional",
            "detail": "OpenBB is not required for base launch.",
            "fallback_path": "native providers",
            "caveat": OPENBB_CAVEAT,
        },
        {
            "check": "availability result",
            "ok": available.ok,
            "status": available.refreshed_status(),
            "detail": available.warning or "OpenBB can be probed.",
            "fallback_path": "native providers",
            "caveat": OPENBB_CAVEAT,
        },
    ]
    return pd.DataFrame(rows)


def build_openbb_setup_guide_payload() -> dict[str, Any]:
    return {
        "install_command": "pip install -r requirements-openbb.txt",
        "dependency_policy": "OpenBB is optional and must not be added to mandatory base requirements.",
        "env_vars": openbb_provider_key_status().to_dict(orient="records"),
        "diagnostic_policy": "Sample data probes are button-triggered. No heavy query runs on page load.",
        "license_caveat": OPENBB_CAVEAT,
        "fallback_path": "Existing yfinance, FRED, EIA, Binance, CoinGecko, DefiLlama, and native providers remain in place.",
    }


def build_openbb_runtime_diagnostics_payload() -> dict[str, Any]:
    return {
        "installation": openbb_installation_status(),
        "runtime_matrix": build_runtime_capability_matrix(),
        "catalog_runtime_comparison": compare_catalog_vs_runtime(),
        "endpoint_gaps": build_openbb_endpoint_gap_table(),
        "provider_key_gaps": build_openbb_provider_key_gap_table(),
        "endpoint_resolution_report": build_openbb_endpoint_probe_report(),
        "probe_policy": "Real sample probes are button-triggered only.",
        "caveat": OPENBB_CAVEAT,
    }


def run_openbb_button_probe_report(symbol: str = "AAPL"):
    return build_openbb_real_probe_report(symbol=symbol)
