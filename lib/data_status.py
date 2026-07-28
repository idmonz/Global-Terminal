from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


FRESHNESS_FRESH = "fresh"
FRESHNESS_STALE = "stale"
FRESHNESS_MISSING = "missing"
FRESHNESS_ESTIMATED = "estimated"
FRESHNESS_ERROR = "error"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DataResult:
    ok: bool
    data: Any = None
    source: str = ""
    provider: str = ""
    fetched_at: datetime = field(default_factory=utc_now)
    stale_after_seconds: int = 900
    error: str | None = None
    warning: str | None = None
    is_cached: bool = False
    is_estimated: bool = False
    is_adjusted: bool | None = None
    coverage: str = "unknown"
    freshness_status: str = FRESHNESS_MISSING
    is_paid_required: bool = False

    @property
    def age_seconds(self) -> float:
        return max(0.0, (utc_now() - self.fetched_at).total_seconds())

    def refreshed_status(self) -> str:
        if self.error:
            return FRESHNESS_ERROR
        if self.is_estimated:
            return FRESHNESS_ESTIMATED
        if not self.ok:
            return FRESHNESS_MISSING
        if self.age_seconds > self.stale_after_seconds:
            return FRESHNESS_STALE
        return FRESHNESS_FRESH

    def to_dict(self) -> dict[str, Any]:
        status = self.refreshed_status()
        return {
            "provider": self.provider,
            "source": self.source,
            "status": status,
            "ok": self.ok,
            "fetched_at": self.fetched_at.isoformat(),
            "age_seconds": round(self.age_seconds, 1),
            "stale_after_seconds": self.stale_after_seconds,
            "coverage": self.coverage,
            "cached": self.is_cached,
            "estimated": self.is_estimated,
            "adjusted": self.is_adjusted,
            "paid_required": self.is_paid_required,
            "warning": self.warning,
            "error": self.error,
        }


_RECENT_RESULTS: list[DataResult] = []


def record_result(result: DataResult) -> DataResult:
    result.freshness_status = result.refreshed_status()
    _RECENT_RESULTS.append(result)
    del _RECENT_RESULTS[:-250]
    return result


def get_recent_results() -> list[DataResult]:
    return list(_RECENT_RESULTS)


def success(
    data: Any,
    *,
    source: str,
    provider: str,
    stale_after_seconds: int = 900,
    warning: str | None = None,
    is_cached: bool = False,
    is_estimated: bool = False,
    is_adjusted: bool | None = None,
    coverage: str = "complete",
) -> DataResult:
    return record_result(
        DataResult(
            ok=True,
            data=data,
            source=source,
            provider=provider,
            stale_after_seconds=stale_after_seconds,
            warning=warning,
            is_cached=is_cached,
            is_estimated=is_estimated,
            is_adjusted=is_adjusted,
            coverage=coverage,
            freshness_status=FRESHNESS_ESTIMATED if is_estimated else FRESHNESS_FRESH,
        )
    )


def failure(
    *,
    source: str,
    provider: str,
    error: str,
    stale_after_seconds: int = 900,
    warning: str | None = None,
    coverage: str = "unavailable",
    is_paid_required: bool = False,
    is_estimated: bool = False,
) -> DataResult:
    return record_result(
        DataResult(
            ok=False,
            data=None,
            source=source,
            provider=provider,
            stale_after_seconds=stale_after_seconds,
            error=error,
            warning=warning,
            coverage=coverage,
            freshness_status=FRESHNESS_ESTIMATED if is_estimated else FRESHNESS_ERROR,
            is_paid_required=is_paid_required,
            is_estimated=is_estimated,
        )
    )


def missing_key(provider: str, env_var: str, *, source: str = "environment") -> DataResult:
    return failure(
        source=source,
        provider=provider,
        error=f"Missing optional environment variable: {env_var}",
        warning="Unavailable: API key or paid provider required.",
        coverage="missing key",
        is_paid_required=True,
    )


def combine_results(results: Iterable[DataResult], *, provider: str, source: str) -> DataResult:
    items = [item for item in results if item is not None]
    if not items:
        return failure(provider=provider, source=source, error="No data results were supplied.")
    errors = [item for item in items if not item.ok]
    estimated = any(item.is_estimated for item in items)
    stale = any(item.refreshed_status() == FRESHNESS_STALE for item in items)
    warnings = [item.warning for item in items if item.warning]
    error_text = "; ".join(item.error for item in errors if item.error) or None
    if errors and len(errors) < len(items) and error_text:
        warnings.append(f"Partial feed errors: {error_text}")
    warning = "; ".join(warnings) or None
    all_failed = len(errors) == len(items)
    status = FRESHNESS_ERROR if all_failed else FRESHNESS_ESTIMATED if estimated else FRESHNESS_STALE if stale else FRESHNESS_FRESH
    return record_result(
        DataResult(
            ok=not all_failed,
            source=source,
            provider=provider,
            fetched_at=max((item.fetched_at for item in items), default=utc_now()),
            stale_after_seconds=min((item.stale_after_seconds for item in items), default=900),
            error=error_text if all_failed else None,
            warning=warning,
            is_cached=all(item.is_cached for item in items),
            is_estimated=estimated,
            coverage=f"{len(items) - len(errors)}/{len(items)} feeds available",
            freshness_status=status,
            data=[item.to_dict() for item in items],
        )
    )


def provider_status_table(results: Iterable[DataResult] | None = None) -> list[dict[str, Any]]:
    source_results = list(results) if results is not None else get_recent_results()
    if not source_results:
        return []
    latest: dict[tuple[str, str], DataResult] = {}
    for result in source_results:
        latest[(result.provider, result.source)] = result
    return [result.to_dict() for result in latest.values()]


def provider_status_rows(results: Iterable[DataResult] | None = None) -> list[dict[str, Any]]:
    return provider_status_table(results)


def ok_result(
    data: Any = None,
    *,
    source: str,
    provider: str,
    stale_after_seconds: int = 3600,
    warning: str | None = None,
    is_cached: bool = False,
    is_estimated: bool = False,
    is_adjusted: bool | None = None,
    coverage: str = "complete",
) -> DataResult:
    return success(
        data,
        source=source,
        provider=provider,
        stale_after_seconds=stale_after_seconds,
        warning=warning,
        is_cached=is_cached,
        is_estimated=is_estimated,
        is_adjusted=is_adjusted,
        coverage=coverage,
    )


def error_result(
    *,
    source: str,
    provider: str,
    error: str,
    data: Any = None,
    warning: str | None = None,
    stale_after_seconds: int = 3600,
    is_estimated: bool = False,
    is_paid_required: bool = False,
    coverage: str = "missing",
) -> DataResult:
    result = failure(
        source=source,
        provider=provider,
        error=error,
        stale_after_seconds=stale_after_seconds,
        warning=warning,
        is_estimated=is_estimated,
        is_paid_required=is_paid_required,
        coverage=coverage,
    )
    result.data = data
    return result


def combine_statuses(statuses: list[DataResult], *, provider: str, source: str) -> DataResult:
    return combine_results(statuses, provider=provider, source=source)
