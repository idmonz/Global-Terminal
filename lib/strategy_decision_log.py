from __future__ import annotations
from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now
from .research_guard_pipeline import run_research_guard_pipeline
from .strategy_commit_diff import compare_strategy_commit_payloads
from .strategy_commit_graph import build_strategy_commit_graph
from .strategy_review_queue import build_strategy_review_queue
from .strategy_forward_metrics import build_forward_tracking_snapshot as _build_forward_tracking_snapshot, update_forward_tracking as _update_forward_tracking

STRATEGY_NOTICE = "Strategy commits are research records. They are not trade approvals, not investment recommendations, and not execution instructions."


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ["strategy_config_snapshot_json", "factor_snapshot_json", "backtest_snapshot_json", "oos_snapshot_json", "regime_snapshot_json", "data_quality_snapshot_json", "provider_snapshot_json"]:
        out[key] = json_loads(out.get(key), {})
    for key in ["guard_results_json", "linked_watchlist_items", "linked_reports", "tags"]:
        out[key] = json_loads(out.get(key), [])
    out["archived"] = bool(out.get("archived"))
    out["review_status"] = out.get("review_status") or ("archived" if out["archived"] else "requires_review")
    out["reviewed_at"] = out.get("reviewed_at") or ""
    out["review_notes"] = out.get("review_notes") or ""
    return out


def build_strategy_snapshot(strategy_config: dict[str, Any] | None = None, **snapshots: Any) -> dict[str, Any]:
    return {"strategy_config": strategy_config or {}, **snapshots, "created_at": utc_now(), "research_only": True}


def create_strategy_commit(
    *, strategy_id: str, message: str, parent_commit_id: str | None = None, status: str = "draft",
    strategy_config_snapshot: dict[str, Any] | None = None, factor_snapshot: dict[str, Any] | None = None,
    backtest_snapshot: dict[str, Any] | None = None, oos_snapshot: dict[str, Any] | None = None,
    regime_snapshot: dict[str, Any] | None = None, data_quality_snapshot: dict[str, Any] | None = None,
    provider_snapshot: dict[str, Any] | None = None, linked_watchlist_items: list[str] | None = None,
    linked_reports: list[str] | None = None, tags: list[str] | None = None, db_path: str | Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    guard_input = {"data_quality": data_quality_snapshot or {}, "provider": provider_snapshot or {}, "backtest": backtest_snapshot or {}, "oos": oos_snapshot or {}, "regime": regime_snapshot or {}, "factor": factor_snapshot or {}, "strategy_config": strategy_config_snapshot or {}}
    guard_results = run_research_guard_pipeline(guard_input, text=message)
    row = {
        "commit_id": new_id("commit"), "strategy_id": strategy_id, "parent_commit_id": parent_commit_id,
        "message": message, "created_at": now, "status": status,
        "strategy_config_snapshot_json": json_dumps(strategy_config_snapshot or {}),
        "factor_snapshot_json": json_dumps(factor_snapshot or {}), "backtest_snapshot_json": json_dumps(backtest_snapshot or {}),
        "oos_snapshot_json": json_dumps(oos_snapshot or {}), "regime_snapshot_json": json_dumps(regime_snapshot or {}),
        "guard_results_json": json_dumps(guard_results), "data_quality_snapshot_json": json_dumps(data_quality_snapshot or {}),
        "provider_snapshot_json": json_dumps(provider_snapshot or {}), "forward_tracking_start": None,
        "linked_watchlist_items": json_dumps(linked_watchlist_items or []), "linked_reports": json_dumps(linked_reports or []),
        "tags": json_dumps(tags or []), "archived": 0,
    }
    execute_query(
        """
        INSERT INTO strategy_commits (commit_id, strategy_id, parent_commit_id, message, created_at, status,
            strategy_config_snapshot_json, factor_snapshot_json, backtest_snapshot_json, oos_snapshot_json,
            regime_snapshot_json, guard_results_json, data_quality_snapshot_json, provider_snapshot_json,
            forward_tracking_start, linked_watchlist_items, linked_reports, tags, archived)
        VALUES (:commit_id, :strategy_id, :parent_commit_id, :message, :created_at, :status,
            :strategy_config_snapshot_json, :factor_snapshot_json, :backtest_snapshot_json, :oos_snapshot_json,
            :regime_snapshot_json, :guard_results_json, :data_quality_snapshot_json, :provider_snapshot_json,
            :forward_tracking_start, :linked_watchlist_items, :linked_reports, :tags, :archived)
        """, row, db_path=db_path)
    return get_strategy_commit(row["commit_id"], db_path) or _decode(row)


def get_strategy_commit(commit_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    row = execute_query("SELECT * FROM strategy_commits WHERE commit_id = ?", (commit_id,), fetch=True, one=True, db_path=db_path)
    return _decode(row) if isinstance(row, dict) else None


def list_strategy_commits(include_archived: bool = False, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    where = "" if include_archived else "WHERE archived = 0"
    rows = execute_query(f"SELECT * FROM strategy_commits {where} ORDER BY created_at DESC", fetch=True, db_path=db_path)
    return [_decode(row) for row in rows]  # type: ignore[arg-type]


def compare_strategy_commits(left_commit_id: str, right_commit_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    left = get_strategy_commit(left_commit_id, db_path); right = get_strategy_commit(right_commit_id, db_path)
    diff = compare_strategy_commit_payloads(left, right)
    return {"left": left, "right": right, **diff}


def archive_strategy_commit(commit_id: str, db_path: str | Path | None = None) -> bool:
    execute_query("UPDATE strategy_commits SET archived = 1 WHERE commit_id = ?", (commit_id,), db_path=db_path); return True


def attach_report_to_commit(commit_id: str, report_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    commit = get_strategy_commit(commit_id, db_path)
    if not commit: return None
    reports = list(dict.fromkeys([*commit.get("linked_reports", []), report_id]))
    execute_query("UPDATE strategy_commits SET linked_reports = ? WHERE commit_id = ?", (json_dumps(reports), commit_id), db_path=db_path)
    return get_strategy_commit(commit_id, db_path)


def attach_watchlist_items_to_commit(commit_id: str, watchlist_item_ids: list[str], db_path: str | Path | None = None) -> dict[str, Any] | None:
    commit = get_strategy_commit(commit_id, db_path)
    if not commit: return None
    items = list(dict.fromkeys([*commit.get("linked_watchlist_items", []), *watchlist_item_ids]))
    execute_query("UPDATE strategy_commits SET linked_watchlist_items = ? WHERE commit_id = ?", (json_dumps(items), commit_id), db_path=db_path)
    return get_strategy_commit(commit_id, db_path)


def build_strategy_commit_summary(commit: dict[str, Any]) -> dict[str, Any]:
    guards = commit.get("guard_results_json", [])
    return {"commit_id": commit.get("commit_id"), "strategy_id": commit.get("strategy_id"), "status": commit.get("status"), "guard_warnings": sum(1 for g in guards if g.get("status") != "passed"), "notice": STRATEGY_NOTICE}


def build_strategy_commit_timeline(commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(commits, key=lambda c: str(c.get("created_at", "")), reverse=True)



def build_strategy_commit_graph_payload(commits: list[dict[str, Any]] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    rows = commits if commits is not None else list_strategy_commits(db_path=db_path)
    return build_strategy_commit_graph(rows)


def build_strategy_review_queue_payload(commits: list[dict[str, Any]] | None = None, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows = commits if commits is not None else list_strategy_commits(db_path=db_path)
    return build_strategy_review_queue(rows)


def build_forward_tracking_snapshot(commit: dict[str, Any], evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    return _build_forward_tracking_snapshot(commit, evaluation)


def update_forward_tracking(commit: dict[str, Any], evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    return _update_forward_tracking(commit, evaluation)
