from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


def run_market_refresh_schedule(
    *,
    refresh: Callable[[], dict[str, Any]],
    interval_seconds: float,
    max_runs: int | None = 1,
    stop_event: threading.Event | None = None,
    wait: Callable[[float], bool] | None = None,
) -> list[dict[str, Any]]:
    interval = max(1.0, float(interval_seconds))
    bounded_runs = None if max_runs is None else max(1, min(int(max_runs), 10_000))
    stopper = stop_event or threading.Event()
    wait_fn = wait or stopper.wait
    results: list[dict[str, Any]] = []
    while not stopper.is_set() and (bounded_runs is None or len(results) < bounded_runs):
        result = refresh()
        results.append(dict(result))
        if bounded_runs is not None and len(results) >= bounded_runs:
            break
        if wait_fn(interval):
            break
    return results

