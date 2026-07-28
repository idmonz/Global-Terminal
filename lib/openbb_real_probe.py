from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .openbb_bridge import OPENBB_CAVEAT, get_openbb_version, is_openbb_installed, openbb_result_to_dict
from .openbb_endpoint_resolver import build_endpoint_resolution_report, resolve_openbb_endpoint_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_openbb_installation_probe() -> dict[str, Any]:
    installed = is_openbb_installed()
    return {
        "probe": "installation",
        "ok": installed,
        "skipped": not installed,
        "installed": installed,
        "version": get_openbb_version() if installed else None,
        "checked_at": _now(),
        "warning": None if installed else "OpenBB is not installed. Native providers remain active.",
        "caveat": OPENBB_CAVEAT,
    }


def run_openbb_endpoint_probe(endpoint: str, *, root: Any | None = None) -> dict[str, Any]:
    report = resolve_openbb_endpoint_path(endpoint, root=root)
    return {
        "probe": "endpoint",
        "endpoint": endpoint,
        "ok": bool(report.get("available")),
        "skipped": not is_openbb_installed() and root is None,
        "selected_path": report.get("selected_path"),
        "reason": report.get("reason"),
        "checked_at": _now(),
        "caveat": OPENBB_CAVEAT,
    }


def run_openbb_sample_query_probe(label: str, fn: Callable[[], Any], *, require_install: bool = True) -> dict[str, Any]:
    if require_install and not is_openbb_installed():
        return {
            "probe": label,
            "ok": False,
            "skipped": True,
            "warning": "OpenBB is not installed; sample query skipped.",
            "error": None,
            "checked_at": _now(),
            "caveat": OPENBB_CAVEAT,
        }
    try:
        result = fn()
        payload = openbb_result_to_dict(result) if hasattr(result, "to_dict") else {"ok": True, "data": result}
        payload.update({"probe": label, "skipped": False, "checked_at": _now(), "caveat": payload.get("caveat") or OPENBB_CAVEAT})
        if hasattr(result, "data") and hasattr(result.data, "__len__"):
            payload["row_count"] = len(result.data)
        return payload
    except Exception as exc:
        return {
            "probe": label,
            "ok": False,
            "skipped": False,
            "warning": "OpenBB sample query failed gracefully.",
            "error": str(exc),
            "checked_at": _now(),
            "caveat": OPENBB_CAVEAT,
        }


def run_openbb_financial_probe(symbol: str = "AAPL") -> list[dict[str, Any]]:
    from .openbb_provider_adapter import get_openbb_company_profile, get_openbb_income_statement

    return [
        run_openbb_endpoint_probe("equity.profile"),
        run_openbb_endpoint_probe("equity.financials.income"),
        run_openbb_sample_query_probe("AAPL profile", lambda: get_openbb_company_profile(symbol)),
        run_openbb_sample_query_probe("AAPL income statement", lambda: get_openbb_income_statement(symbol)),
    ]


def run_openbb_macro_probe() -> list[dict[str, Any]]:
    from .openbb_provider_adapter import get_openbb_treasury_rates

    return [
        run_openbb_endpoint_probe("rates.treasury_rates"),
        run_openbb_sample_query_probe("treasury rates", get_openbb_treasury_rates),
    ]


def run_openbb_options_probe(symbol: str = "SPY") -> list[dict[str, Any]]:
    from .openbb_provider_adapter import get_openbb_options_chain

    return [
        run_openbb_endpoint_probe("options.chain"),
        run_openbb_sample_query_probe("options chain", lambda: get_openbb_options_chain(symbol)),
    ]


def run_openbb_screener_probe() -> list[dict[str, Any]]:
    from .openbb_provider_adapter import get_openbb_equity_screener

    return [
        run_openbb_endpoint_probe("market.movers"),
        run_openbb_sample_query_probe("equity screener", get_openbb_equity_screener),
    ]


def build_openbb_real_probe_report(symbol: str = "AAPL"):
    rows: list[dict[str, Any]] = [run_openbb_installation_probe()]
    rows.extend(run_openbb_financial_probe(symbol))
    rows.extend(run_openbb_macro_probe())
    rows.extend(run_openbb_options_probe("SPY"))
    rows.extend(run_openbb_screener_probe())
    return pd.DataFrame(rows) if pd is not None else rows


def build_openbb_endpoint_probe_report(endpoints: list[str] | None = None):
    return build_endpoint_resolution_report(endpoints=endpoints)
