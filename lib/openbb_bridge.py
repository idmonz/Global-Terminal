from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import sys
from typing import Any, Callable

from .data_status import DataResult, error_result, ok_result

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


OPENBB_PROVIDER = "openbb"
OPENBB_SOURCE = "optional OpenBB backend"
OPENBB_CAVEAT = "OpenBB is an optional backend. Provider availability, licensing, data rights, and API key requirements must be verified by the user before production or commercial use."


def is_openbb_installed() -> bool:
    if "openbb" in sys.modules:
        return True
    try:
        return importlib.util.find_spec("openbb") is not None
    except Exception:
        return False


def get_openbb_version() -> str | None:
    try:
        return importlib.metadata.version("openbb")
    except Exception:
        module = sys.modules.get("openbb")
        return str(getattr(module, "__version__", "")) or None


def lazy_import_openbb() -> tuple[Any | None, str | None]:
    try:
        module = importlib.import_module("openbb")
        return getattr(module, "obb", module), None
    except Exception as exc:
        return None, str(exc)


def _decorate_openbb_result(
    result: DataResult,
    *,
    command: str = "",
    caveat: str = OPENBB_CAVEAT,
    is_openbb: bool = True,
    is_optional: bool = True,
    requires_key: bool = False,
    fallback_used: bool = False,
) -> DataResult:
    result.command = command
    result.caveat = caveat
    result.is_openbb = is_openbb
    result.is_optional = is_optional
    result.requires_key = requires_key
    result.fallback_used = fallback_used
    result.openbb_metadata = {
        "ok": result.ok,
        "provider": result.provider,
        "source": result.source,
        "command": command,
        "warning": result.warning,
        "error": result.error,
        "caveat": caveat,
        "is_openbb": is_openbb,
        "is_optional": is_optional,
        "requires_key": requires_key,
        "fallback_used": fallback_used,
    }
    return result


def openbb_result_to_dict(result: DataResult) -> dict[str, Any]:
    payload = result.to_dict()
    payload.update(getattr(result, "openbb_metadata", {}))
    return payload


def openbb_available_result() -> DataResult:
    installed = is_openbb_installed()
    version = get_openbb_version() if installed else None
    warning = None if installed else "OpenBB is not installed; native providers remain active."
    result = ok_result(
        {"installed": installed, "version": version, "backend_mode": "optional", "caveat": OPENBB_CAVEAT},
        source=OPENBB_SOURCE,
        provider=OPENBB_PROVIDER,
        warning=warning,
        coverage="installed" if installed else "not installed",
        is_estimated=not installed,
    )
    if not installed:
        result.ok = False
    return _decorate_openbb_result(result, command="openbb.installation_status")


def openbb_error_to_warning(error: Exception | str | None) -> str:
    text = str(error or "Unknown OpenBB error")
    return f"OpenBB optional backend warning: {text}"


def openbb_not_installed_result(command: str = "", *, fallback_used: bool = True) -> DataResult:
    result = error_result(
        source=OPENBB_SOURCE,
        provider=OPENBB_PROVIDER,
        error="OpenBB is not installed.",
        warning="Install optional requirements from requirements-openbb.txt to enable the OpenBB backend. Native providers remain available.",
        data=_empty_frame(),
        coverage="not installed",
    )
    return _decorate_openbb_result(result, command=command, fallback_used=fallback_used)


def openbb_provider_missing_key_result(command: str = "", *, env_var: str = "", provider: str = OPENBB_PROVIDER) -> DataResult:
    result = error_result(
        source=OPENBB_SOURCE,
        provider=provider,
        error=f"Missing optional provider key: {env_var}" if env_var else "Missing optional provider key.",
        warning="The OpenBB command may require an optional provider key. No secret value is displayed.",
        data=_empty_frame(),
        coverage="missing key",
        is_paid_required=True,
    )
    return _decorate_openbb_result(result, command=command, requires_key=True)


def _empty_frame():
    return pd.DataFrame() if pd is not None else []


def openbb_to_dataframe(value: Any):
    if pd is None:
        return value if value is not None else []
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value.copy()
    for method in ("to_df", "to_dataframe"):
        converter = getattr(value, method, None)
        if callable(converter):
            try:
                converted = converter()
                if isinstance(converted, pd.DataFrame):
                    return converted.copy()
            except Exception:
                pass
    for attr in ("results", "data"):
        if hasattr(value, attr):
            try:
                return openbb_to_dataframe(getattr(value, attr))
            except Exception:
                pass
    for method in ("model_dump", "dict"):
        converter = getattr(value, method, None)
        if callable(converter):
            try:
                dumped = converter()
                if isinstance(dumped, dict) and "results" in dumped:
                    return openbb_to_dataframe(dumped["results"])
                return openbb_to_dataframe(dumped)
            except Exception:
                pass
    if isinstance(value, dict):
        if "results" in value:
            return openbb_to_dataframe(value["results"])
        if "data" in value and isinstance(value["data"], (list, tuple, dict)):
            return openbb_to_dataframe(value["data"])
        return pd.DataFrame([value])
    if isinstance(value, (list, tuple)):
        return pd.DataFrame(list(value))
    try:
        return pd.DataFrame(value)
    except Exception:
        return pd.DataFrame()


def openbb_to_dataresult(
    data: Any,
    *,
    command: str,
    source: str | None = None,
    provider: str = OPENBB_PROVIDER,
    warning: str | None = None,
    error: str | None = None,
    caveat: str = OPENBB_CAVEAT,
    requires_key: bool = False,
    fallback_used: bool = False,
    mapper: Callable[[Any], Any] | None = None,
) -> DataResult:
    mapped = mapper(data) if mapper else data
    frame = openbb_to_dataframe(mapped)
    empty = bool(getattr(frame, "empty", False))
    metadata_warning = getattr(frame, "attrs", {}).get("warning") if hasattr(frame, "attrs") else None
    combined_warning = "; ".join(item for item in [warning, metadata_warning] if item) or None
    if error:
        result = error_result(
            source=source or f"OpenBB {command}",
            provider=provider,
            error=error,
            warning=combined_warning,
            data=frame,
            coverage="unavailable",
            is_paid_required=requires_key,
        )
    elif empty:
        result = error_result(
            source=source or f"OpenBB {command}",
            provider=provider,
            error="OpenBB command returned no usable rows.",
            warning=combined_warning or "OpenBB returned an empty dataset. Native fallback may be used when source mode allows it.",
            data=frame,
            coverage="empty",
            is_paid_required=requires_key,
        )
    else:
        result = ok_result(
            frame,
            source=source or f"OpenBB {command}",
            provider=provider,
            warning=combined_warning,
            coverage=f"{len(frame)} rows" if hasattr(frame, "__len__") else "available",
            is_estimated=bool(getattr(frame, "attrs", {}).get("is_estimate", False)),
        )
    return _decorate_openbb_result(result, command=command, caveat=caveat, requires_key=requires_key, fallback_used=fallback_used)


def _resolve_command(root: Any, command: str) -> Any:
    target = root
    for part in [item for item in str(command).split(".") if item]:
        target = getattr(target, part)
    return target


def call_openbb_command_safe(
    command: str,
    *args: Any,
    obb: Any | None = None,
    mapper: Callable[[Any], Any] | None = None,
    requires_key: bool = False,
    fallback_used: bool = False,
    **kwargs: Any,
) -> DataResult:
    root = obb
    if root is None:
        root, import_error = lazy_import_openbb()
        if root is None:
            result = openbb_not_installed_result(command, fallback_used=fallback_used)
            if import_error:
                result.warning = openbb_error_to_warning(import_error)
            return result
    try:
        target = _resolve_command(root, command)
    except Exception as exc:
        return openbb_to_dataresult(
            _empty_frame(),
            command=command,
            error=f"OpenBB command is unavailable: {exc}",
            warning="This OpenBB endpoint may differ by installed version or provider package.",
            requires_key=requires_key,
            fallback_used=fallback_used,
        )
    try:
        raw = target(*args, **kwargs) if callable(target) else target
        return openbb_to_dataresult(raw, command=command, mapper=mapper, requires_key=requires_key, fallback_used=fallback_used)
    except Exception as exc:
        warning = openbb_error_to_warning(exc)
        lower = str(exc).lower()
        if any(token in lower for token in ["api key", "apikey", "unauthorized", "forbidden", "credential"]):
            return openbb_provider_missing_key_result(command)
        return openbb_to_dataresult(
            _empty_frame(),
            command=command,
            error=str(exc),
            warning=warning,
            requires_key=requires_key,
            fallback_used=fallback_used,
        )


def build_openbb_capability_catalog():
    from .openbb_catalog import build_openbb_capability_catalog as _build_openbb_capability_catalog

    return _build_openbb_capability_catalog()


def resolve_openbb_endpoint_path(endpoint: str) -> dict[str, Any]:
    from .openbb_endpoint_resolver import resolve_openbb_endpoint_path as _resolve_openbb_endpoint_path

    return _resolve_openbb_endpoint_path(endpoint)


def run_openbb_installation_probe() -> dict[str, Any]:
    status = openbb_available_result()
    return {
        "installed": bool(status.data.get("installed") if isinstance(status.data, dict) else status.ok),
        "version": status.data.get("version") if isinstance(status.data, dict) else get_openbb_version(),
        "ok": bool(status.ok),
        "warning": status.warning,
        "caveat": OPENBB_CAVEAT,
    }
