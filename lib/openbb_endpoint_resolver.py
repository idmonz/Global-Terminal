from __future__ import annotations

from functools import lru_cache
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .endpoint_catalog import build_internal_endpoint_catalog, endpoint_openbb_candidates
from .openbb_bridge import OPENBB_CAVEAT, lazy_import_openbb


def build_openbb_endpoint_aliases() -> dict[str, list[str]]:
    aliases = {endpoint: endpoint_openbb_candidates(endpoint) for endpoint in build_internal_endpoint_catalog()}
    aliases.update(
        {
            "equity.financials.income": ["equity.fundamental.income", "equity.fundamental.income_statement", "equity.fundamental.income_statement.standard", "equity.fundamental.financials.income"],
            "equity.financials.balance": ["equity.fundamental.balance", "equity.fundamental.balance_sheet", "equity.fundamental.financials.balance"],
            "equity.financials.cashflow": ["equity.fundamental.cash", "equity.fundamental.cash_flow", "equity.fundamental.cashflow"],
            "equity.financials.ratios": ["equity.fundamental.ratios", "equity.fundamental.financial_ratios"],
            "equity.financials.metrics": ["equity.fundamental.metrics", "equity.fundamental.key_metrics"],
            "equity.estimates.eps": ["equity.estimates.consensus", "equity.estimates.forward_eps", "equity.calendar.earnings"],
            "equity.estimates.revenue": ["equity.estimates.consensus", "equity.estimates.forward_sales", "equity.calendar.earnings"],
            "options.chain": ["derivatives.options.chains", "derivatives.options.chain", "derivatives.options.surface", "equity.options.chains"],
            "rates.treasury_rates": ["fixedincome.government.treasury_rates", "fixedincome.government.yield_curve"],
            "rates.treasury_curve": ["fixedincome.government.yield_curve", "fixedincome.government.treasury_rates"],
            "rates.sofr": ["fixedincome.rates.sofr"],
            "rates.effr": ["fixedincome.rates.effr"],
            "energy.petroleum_status": ["commodity.energy.petroleum_status_report", "commodity.energy.short_term_energy_outlook", "commodity.petroleum_status_report"],
            "energy.short_term_outlook": ["commodity.energy.short_term_energy_outlook", "commodity.energy.petroleum_status_report"],
        }
    )
    return {key: [path for path in paths if path] for key, paths in aliases.items()}


def get_nested_attr_safe(root: Any, path: str) -> tuple[Any | None, str | None]:
    target = root
    for part in [item for item in str(path).split(".") if item]:
        try:
            target = getattr(target, part)
        except Exception as exc:
            return None, f"Missing path component '{part}' in {path}: {exc}"
        if target is None:
            return None, f"Path component '{part}' is None in {path}."
    return target, None


def endpoint_path_exists(root: Any, path: str) -> bool:
    target, error = get_nested_attr_safe(root, path)
    return error is None and target is not None


def list_available_openbb_paths(root: Any | None = None, *, max_depth: int = 4) -> list[str]:
    if root is None:
        root, _ = lazy_import_openbb()
    if root is None:
        return []
    paths: list[str] = []

    def walk(obj: Any, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        for name in sorted(dir(obj)):
            if name.startswith("_"):
                continue
            try:
                value = getattr(obj, name)
            except Exception:
                continue
            path = f"{prefix}.{name}" if prefix else name
            if callable(value):
                paths.append(path)
            elif depth < max_depth and not isinstance(value, (str, int, float, bool, bytes, list, tuple, dict, set)):
                walk(value, path, depth + 1)

    walk(root, "", 0)
    return sorted(set(paths))


def select_first_available_endpoint(endpoint_or_paths: str | list[str], root: Any | None = None) -> dict[str, Any]:
    if root is None:
        root, import_error = lazy_import_openbb()
        if root is None:
            return {"endpoint": endpoint_or_paths if isinstance(endpoint_or_paths, str) else None, "selected_path": None, "available": False, "reason": import_error or "OpenBB is not installed.", "caveat": OPENBB_CAVEAT}
    paths = build_openbb_endpoint_aliases().get(endpoint_or_paths, [endpoint_or_paths]) if isinstance(endpoint_or_paths, str) else endpoint_or_paths
    for path in paths:
        target, error = get_nested_attr_safe(root, path)
        if error is None and target is not None:
            return {"endpoint": endpoint_or_paths if isinstance(endpoint_or_paths, str) else path, "selected_path": path, "available": True, "callable": callable(target), "reason": None, "caveat": OPENBB_CAVEAT}
    return {"endpoint": endpoint_or_paths if isinstance(endpoint_or_paths, str) else None, "selected_path": None, "available": False, "reason": "No candidate endpoint path exists on this OpenBB runtime.", "caveat": OPENBB_CAVEAT}


@lru_cache(maxsize=256)
def _resolve_cached(endpoint: str, root_identity: str = "runtime") -> tuple[str | None, bool, str | None]:
    root, import_error = lazy_import_openbb()
    if root is None:
        return None, False, import_error or "OpenBB is not installed."
    report = select_first_available_endpoint(endpoint, root=root)
    return report.get("selected_path"), bool(report.get("available")), report.get("reason")


def resolve_openbb_endpoint_path(endpoint: str, root: Any | None = None) -> dict[str, Any]:
    if root is not None:
        return select_first_available_endpoint(endpoint, root=root)
    selected, available, reason = _resolve_cached(endpoint)
    return {"endpoint": endpoint, "selected_path": selected, "available": available, "reason": reason, "caveat": OPENBB_CAVEAT}


def build_endpoint_resolution_report(root: Any | None = None, endpoints: list[str] | None = None):
    aliases = build_openbb_endpoint_aliases()
    rows = []
    for endpoint in endpoints or sorted(aliases):
        report = resolve_openbb_endpoint_path(endpoint, root=root)
        rows.append(
            {
                "endpoint": endpoint,
                "candidate_paths": aliases.get(endpoint, []),
                "selected_path": report.get("selected_path"),
                "available": report.get("available"),
                "reason": report.get("reason"),
                "caveat": OPENBB_CAVEAT,
            }
        )
    return pd.DataFrame(rows) if pd is not None else rows
