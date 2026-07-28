from __future__ import annotations
from typing import Any

FIELDS = ["strategy_config_snapshot_json", "factor_snapshot_json", "backtest_snapshot_json", "oos_snapshot_json", "regime_snapshot_json", "guard_results_json", "data_quality_snapshot_json", "provider_snapshot_json", "linked_watchlist_items", "linked_reports", "status", "message"]


def diff_values(left: Any, right: Any) -> dict[str, Any]:
    return {"changed": left != right, "left": left, "right": right}


def compare_strategy_commit_payloads(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    left = left or {}; right = right or {}
    changed = {field: diff_values(left.get(field), right.get(field)) for field in FIELDS if left.get(field) != right.get(field)}
    return {"same_strategy": bool(left and right and left.get("strategy_id") == right.get("strategy_id")), "changed_fields": list(changed.keys()), "diff": changed, "change_count": len(changed)}
