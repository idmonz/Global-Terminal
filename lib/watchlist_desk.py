from __future__ import annotations

import copy
import os
import re
import statistics
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .equity_provider_breadth import (
    fetch_alpha_vantage_overview,
    fetch_finnhub_company_news,
    fetch_finnhub_earnings_calendar,
)
from .market_data import fetch_multi_history, normalize_ohlcv
from .research_snapshot import (
    MAX_RESEARCH_PROVIDER_CALLS,
    MAX_RESEARCH_SYMBOLS,
    RESEARCH_SNAPSHOT_VERSION,
    RESEARCH_SNAPSHOT_TTL_SECONDS,
    build_research_snapshot_rows,
    default_provider_budget,
    research_snapshot_cache_key,
)
from .research_snapshot_diff import (
    build_change_alert_preview,
    build_refresh_operations_contract,
    build_research_snapshot_diff,
    change_alert_readiness_for_list,
)
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now
from .research_workspace_paths import get_workspace_db_path
from .runtime_cache import RuntimeCacheRecord, load_runtime_cache_record, save_runtime_cache_record
from .symbol_workstation import history_cache_key, resolve_symbol
from .watchlist_store import create_watchlist_item


WATCHLIST_DESK_VERSION = "watchlist_desk.v1"
WATCHLIST_MATERIALIZATION_VERSION = "watchlist_materialization.v1"
MAX_WATCHLISTS = 20
MAX_WATCHLIST_SYMBOLS = 50
MAX_MATERIALIZE_SYMBOLS = MAX_RESEARCH_SYMBOLS
MAX_MATERIALIZE_CONCURRENCY = 2
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
SAFE_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9._=-]{0,23}$")
_ACTIVE_MATERIALIZATIONS: set[str] = set()
_ACTIVE_MATERIALIZATIONS_LOCK = threading.Lock()


class WatchlistConflict(ValueError):
    pass


def compute_watchlist_advanced_metrics(history: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Derive bounded watchlist metrics from an existing exact-symbol cache."""
    rows = [
        row
        for row in history
        if isinstance(row, dict) and _number(row.get("close")) is not None
    ]
    closes = [float(row["close"]) for row in rows]
    volumes = [
        float(row["volume"])
        for row in rows
        if _number(row.get("volume")) is not None
    ]

    def period_return(observations: int) -> float | None:
        if len(closes) <= observations or closes[-observations - 1] == 0:
            return None
        return round((closes[-1] / closes[-observations - 1] - 1.0) * 100.0, 4)

    returns = [
        closes[index] / closes[index - 1] - 1.0
        for index in range(1, len(closes))
        if closes[index - 1] != 0
    ]
    recent_returns = returns[-21:]
    realized_volatility = (
        round(statistics.stdev(recent_returns) * (252**0.5) * 100.0, 4)
        if len(recent_returns) >= 20
        else None
    )
    rsi = None
    if len(closes) >= 15:
        deltas = [closes[index] - closes[index - 1] for index in range(len(closes) - 14, len(closes))]
        average_gain = sum(max(delta, 0.0) for delta in deltas) / 14
        average_loss = sum(max(-delta, 0.0) for delta in deltas) / 14
        rsi = 100.0 if average_loss == 0 else 100.0 - (100.0 / (1.0 + average_gain / average_loss))
        rsi = round(rsi, 4)
    sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    trend_state = None
    if sma_20 is not None and sma_50 is not None:
        trend_state = (
            "bullish"
            if closes[-1] >= sma_20 >= sma_50
            else "bearish"
            if closes[-1] <= sma_20 <= sma_50
            else "mixed"
        )
    complete = len(closes) >= 66
    return {
        "status": "available" if complete else "partial" if closes else "unavailable",
        "observation_count": len(closes),
        "return_1w_pct": period_return(5),
        "return_1m_pct": period_return(21),
        "return_3m_pct": period_return(63),
        "realized_volatility_1m_pct": realized_volatility,
        "average_volume_10": (
            round(sum(volumes[-10:]) / 10.0, 4) if len(volumes) >= 10 else None
        ),
        "rsi_14": rsi,
        "sma_20": round(sma_20, 4) if sma_20 is not None else None,
        "sma_50": round(sma_50, 4) if sma_50 is not None else None,
        "trend_state": trend_state,
        "provider_calls": 0,
        "calculation_source": "existing-symbol-history-cache",
        "formula_version": "phase6e.watchlist.v1",
        "data_gap": (
            None
            if complete
            else "At least 66 cached daily observations are required for the full advanced metric set."
            if closes
            else "No exact-symbol history cache is available; no provider refresh was attempted."
        ),
        "not_financial_advice": True,
    }


def _cached_watchlist_metrics(item: dict[str, Any]) -> dict[str, Any]:
    asset_class = str(item.get("asset_class") or "equity")
    symbol = str(item.get("symbol") or "")
    record = load_runtime_cache_record(
        history_cache_key(asset_class, symbol, "1d", "3mo")
    )
    metrics = compute_watchlist_advanced_metrics(
        record.data if record is not None and isinstance(record.data, list) else []
    )
    return {
        **metrics,
        "provider": record.provider if record is not None else None,
        "source_url": record.source_url if record is not None else None,
        "fetched_at": record.fetched_at_iso if record is not None else None,
        "freshness": (
            "cached"
            if record is not None and record.is_fresh(900)
            else "stale"
            if record is not None
            else "unavailable"
        ),
    }


def _clean_name(value: Any, *, fallback: str = "Primary Watchlist") -> str:
    text = str(value or "").replace("\x00", " ").strip()
    if not text:
        text = fallback
    if len(text) > 80:
        raise ValueError("Watchlist name must be 80 characters or fewer.")
    return text


def _list_id(value: Any, *, fallback: str = "primary") -> str:
    text = str(value or fallback).strip().lower()
    if not SAFE_ID.fullmatch(text):
        raise ValueError("watchlist_id must be a lowercase URL-safe identifier.")
    return text


def _decode_collection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "list_id": str(row.get("list_id") or ""),
        "name": str(row.get("name") or ""),
        "position": int(row.get("position") or 0),
        "active": bool(row.get("active")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _decode_job(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    saved = json_loads(row.get("rows_json"), [])
    rows = saved.get("rows", []) if isinstance(saved, dict) else saved
    provider_budget = saved.get("provider_budget") if isinstance(saved, dict) else None
    return {
        "job_id": row.get("job_id"),
        "list_id": row.get("list_id"),
        "status": row.get("status"),
        "requested_count": int(row.get("requested_count") or 0),
        "completed_count": int(row.get("completed_count") or 0),
        "failed_count": int(row.get("failed_count") or 0),
        "skipped_count": int(row.get("skipped_count") or 0),
        "provider_call_budget": int(row.get("provider_call_budget") or 0),
        "provider_call_count": int(row.get("provider_call_count") or 0),
        "queue_depth": int(row.get("queue_depth") or 0),
        "duration_ms": int(row.get("duration_ms") or 0),
        "interval": row.get("interval"),
        "range": row.get("range_name"),
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "last_error": row.get("last_error") or None,
        "rows": rows if isinstance(rows, list) else [],
        "provider_budget": provider_budget if isinstance(provider_budget, dict) else None,
        "broad_universe_rebuild": False,
        "installed_background_service": False,
    }


def create_watchlist(
    name: str,
    *,
    list_id: str | None = None,
    position: int | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    existing_count = execute_query(
        "SELECT COUNT(*) AS count FROM watchlist_collections WHERE active = 1",
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if int((existing_count or {}).get("count", 0)) >= MAX_WATCHLISTS:
        raise ValueError(f"At most {MAX_WATCHLISTS} active watchlists are allowed.")
    normalized_name = _clean_name(name)
    normalized_id = _list_id(list_id or re.sub(r"[^a-z0-9]+", "-", normalized_name.lower()).strip("-") or "watchlist")
    duplicate = execute_query(
        "SELECT list_id FROM watchlist_collections WHERE list_id = ? AND active = 1",
        (normalized_id,),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if duplicate:
        raise WatchlistConflict("duplicate-watchlist")
    if position is None:
        last = execute_query(
            "SELECT COALESCE(MAX(position), -1) AS position FROM watchlist_collections WHERE active = 1",
            fetch=True,
            one=True,
            db_path=db_path,
        )
        position = int((last or {}).get("position", -1)) + 1
    now = utc_now()
    row = {
        "list_id": normalized_id,
        "name": normalized_name,
        "position": max(0, int(position)),
        "active": 1,
        "created_at": now,
        "updated_at": now,
        "metadata_json": "{}",
    }
    execute_query(
        """
        INSERT INTO watchlist_collections (
            list_id, name, position, active, created_at, updated_at, metadata_json
        ) VALUES (
            :list_id, :name, :position, :active, :created_at, :updated_at, :metadata_json
        )
        """,
        row,
        db_path=db_path,
    )
    return _decode_collection(row)


def ensure_default_watchlist(db_path: str | Path | None = None) -> dict[str, Any]:
    row = execute_query(
        "SELECT * FROM watchlist_collections WHERE list_id = 'primary' AND active = 1",
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if row:
        return _decode_collection(row)
    return create_watchlist("Primary Watchlist", list_id="primary", position=0, db_path=db_path)


def list_watchlists(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows = execute_query(
        """
        SELECT c.*,
            (SELECT COUNT(*) FROM watchlist_items i
             WHERE i.watchlist_id = c.list_id AND i.active = 1) AS item_count
        FROM watchlist_collections c
        WHERE c.active = 1
        ORDER BY c.position ASC, c.updated_at DESC, c.list_id ASC
        """,
        fetch=True,
        db_path=db_path,
    )
    output = []
    for row in rows:  # type: ignore[union-attr]
        current = _decode_collection(row)
        current["item_count"] = int(row.get("item_count") or 0)
        output.append(current)
    return output


def rename_watchlist(
    list_id: str,
    name: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_id = _list_id(list_id)
    changed = execute_query(
        """
        UPDATE watchlist_collections
        SET name = ?, updated_at = ?
        WHERE list_id = ? AND active = 1
        """,
        (_clean_name(name), utc_now(), normalized_id),
        db_path=db_path,
    )
    if not changed:
        raise KeyError("watchlist-not-found")
    row = execute_query(
        "SELECT * FROM watchlist_collections WHERE list_id = ?",
        (normalized_id,),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    return _decode_collection(row or {})


def archive_watchlist(list_id: str, *, db_path: str | Path | None = None) -> bool:
    normalized_id = _list_id(list_id)
    if normalized_id == "primary":
        raise ValueError("The primary watchlist cannot be archived.")
    now = utc_now()
    changed = execute_query(
        "UPDATE watchlist_collections SET active = 0, updated_at = ? WHERE list_id = ? AND active = 1",
        (now, normalized_id),
        db_path=db_path,
    )
    execute_query(
        "UPDATE watchlist_items SET active = 0, updated_at = ? WHERE watchlist_id = ? AND active = 1",
        (now, normalized_id),
        db_path=db_path,
    )
    return bool(changed)


def _require_watchlist(list_id: str, db_path: str | Path | None) -> dict[str, Any]:
    normalized_id = _list_id(list_id)
    row = execute_query(
        "SELECT * FROM watchlist_collections WHERE list_id = ? AND active = 1",
        (normalized_id,),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if not row and normalized_id == "primary":
        return ensure_default_watchlist(db_path)
    if not row:
        raise KeyError("watchlist-not-found")
    return _decode_collection(row)


def _public_item(row: dict[str, Any]) -> dict[str, Any]:
    symbol = str(row.get("symbol") or "").upper()
    asset_class = str(row.get("asset_class") or "").lower() or None
    identity = resolve_symbol(symbol, asset_class=asset_class) if symbol else None
    context = (
        identity.get("market_map_context")
        if identity and isinstance(identity.get("market_map_context"), dict)
        else {}
    )
    return {
        "item_id": row.get("item_id"),
        "list_id": row.get("watchlist_id") or "primary",
        "position": int(row.get("position") or 0),
        "symbol": symbol,
        "name": (identity or {}).get("name") or row.get("display_name"),
        "asset_class": (identity or {}).get("asset_class") or asset_class,
        "exchange": (identity or {}).get("exchange") or row.get("exchange"),
        "mic": (identity or {}).get("mic"),
        "cik": (identity or {}).get("cik"),
        "sector": context.get("sector") or (identity or {}).get("sector"),
        "industry": context.get("industry") or (identity or {}).get("industry"),
        "identity_origin": (identity or {}).get("identity_origin"),
        "identity_status": "exact" if identity else "identity-unavailable",
        "last_price": context.get("price"),
        "change_pct": context.get("return_1d_pct"),
        "market_provider": context.get("market_provider"),
        "market_source_url": context.get("market_source_url"),
        "market_fetched_at": context.get("market_fetched_at"),
        "source_status": (identity or {}).get("snapshot_status") or (identity or {}).get("source_status") or "unavailable",
        "freshness": (identity or {}).get("snapshot_status") or "unavailable",
        "capability": "workstation" if identity else "unavailable",
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "not_financial_advice": True,
    }


def list_watchlist_symbols(
    list_id: str = "primary",
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    collection = _require_watchlist(list_id, db_path)
    rows = execute_query(
        """
        SELECT * FROM watchlist_items
        WHERE watchlist_id = ? AND active = 1
        ORDER BY position ASC, created_at ASC, item_id ASC
        """,
        (collection["list_id"],),
        fetch=True,
        db_path=db_path,
    )
    return [_public_item(row) for row in rows]  # type: ignore[arg-type]


def add_watchlist_symbol(
    list_id: str,
    symbol: str,
    *,
    asset_class: str | None = None,
    private_reason: str = "",
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    collection = _require_watchlist(list_id, db_path)
    normalized_symbol = str(symbol or "").upper().strip()
    if not SAFE_SYMBOL.fullmatch(normalized_symbol):
        raise ValueError("unknown-symbol")
    normalized_class = str(asset_class or "").lower().strip() or None
    identity = resolve_symbol(normalized_symbol, asset_class=normalized_class)
    if identity is None:
        any_identity = resolve_symbol(normalized_symbol)
        raise ValueError("asset-class-mismatch" if any_identity and normalized_class else "unknown-symbol")
    count = execute_query(
        "SELECT COUNT(*) AS count FROM watchlist_items WHERE watchlist_id = ? AND active = 1",
        (collection["list_id"],),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if int((count or {}).get("count", 0)) >= MAX_WATCHLIST_SYMBOLS:
        raise ValueError(f"At most {MAX_WATCHLIST_SYMBOLS} active symbols are allowed per watchlist.")
    duplicate = execute_query(
        """
        SELECT item_id FROM watchlist_items
        WHERE watchlist_id = ? AND upper(symbol) = ? AND active = 1
        """,
        (collection["list_id"], identity["symbol"]),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if duplicate:
        raise WatchlistConflict("duplicate-symbol")
    last = execute_query(
        """
        SELECT COALESCE(MAX(position), -1) AS position
        FROM watchlist_items WHERE watchlist_id = ? AND active = 1
        """,
        (collection["list_id"],),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    item = create_watchlist_item(
        item_type=str(identity["asset_class"]),
        watchlist_id=collection["list_id"],
        position=int((last or {}).get("position", -1)) + 1,
        symbol=str(identity["symbol"]),
        display_name=str(identity["name"]),
        asset_class=str(identity["asset_class"]),
        exchange=str(identity.get("exchange") or ""),
        watch_reason=str(private_reason or "")[:1000],
        default_command=f"{identity['symbol']} DES",
        default_page="apps/web/?view=watchlist-desk",
        source="watchlist-desk-local",
        metadata={
            "identity_origin": identity.get("identity_origin"),
            "cik": identity.get("cik"),
            "mic": identity.get("mic"),
        },
        db_path=db_path,
    )
    execute_query(
        "UPDATE watchlist_collections SET updated_at = ? WHERE list_id = ?",
        (utc_now(), collection["list_id"]),
        db_path=db_path,
    )
    return _public_item(item)


def archive_watchlist_symbol(
    list_id: str,
    item_id: str,
    *,
    db_path: str | Path | None = None,
) -> bool:
    collection = _require_watchlist(list_id, db_path)
    changed = execute_query(
        """
        UPDATE watchlist_items SET active = 0, updated_at = ?
        WHERE watchlist_id = ? AND item_id = ? AND active = 1
        """,
        (utc_now(), collection["list_id"], str(item_id or "")),
        db_path=db_path,
    )
    return bool(changed)


def reorder_watchlist(
    list_id: str,
    ordered_item_ids: Iterable[str],
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    collection = _require_watchlist(list_id, db_path)
    requested = [str(item or "") for item in ordered_item_ids]
    current_rows = execute_query(
        "SELECT item_id FROM watchlist_items WHERE watchlist_id = ? AND active = 1",
        (collection["list_id"],),
        fetch=True,
        db_path=db_path,
    )
    current = {str(row["item_id"]) for row in current_rows}  # type: ignore[union-attr]
    if len(requested) != len(set(requested)) or set(requested) != current:
        raise ValueError("Reorder requires every active item exactly once.")
    now = utc_now()
    for position, item_id in enumerate(requested):
        execute_query(
            """
            UPDATE watchlist_items SET position = ?, updated_at = ?
            WHERE watchlist_id = ? AND item_id = ?
            """,
            (position, now, collection["list_id"], item_id),
            db_path=db_path,
        )
    return list_watchlist_symbols(collection["list_id"], db_path=db_path)


def materialization_lock_key(list_id: str, *, db_path: str | Path | None = None) -> str:
    return f"{get_workspace_db_path(db_path)}::{_list_id(list_id)}"


def _period_for_range(range_name: str) -> str:
    return {
        "1mo": "1mo",
        "3mo": "3mo",
        "6mo": "6mo",
        "1y": "1y",
        "2y": "2y",
        "5y": "5y",
        "ytd": "ytd",
        "max": "max",
    }.get(str(range_name or "3mo").lower(), "3mo")


def _frame_for_symbol(raw: Any, provider_symbol: str) -> Any:
    columns = getattr(raw, "columns", None)
    if columns is None:
        return None
    if getattr(columns, "nlevels", 1) > 1:
        for level in range(columns.nlevels):
            if provider_symbol in set(columns.get_level_values(level)):
                try:
                    return raw.xs(provider_symbol, axis=1, level=level)
                except Exception:
                    return None
    return raw


def _history_rows(frame: Any) -> list[dict[str, Any]]:
    normalized = normalize_ohlcv(frame)
    if normalized is None or getattr(normalized, "empty", True):
        return []
    rows: list[dict[str, Any]] = []
    for row in normalized.to_dict(orient="records"):
        date_value = row.get("date")
        if hasattr(date_value, "isoformat"):
            date_value = date_value.isoformat()
        rows.append(
            {
                "date": str(date_value),
                "open": _number(row.get("open")),
                "high": _number(row.get("high")),
                "low": _number(row.get("low")),
                "close": _number(row.get("close")),
                "adj_close": _number(row.get("adj_close")),
                "volume": _number(row.get("volume")),
            }
        )
    return rows


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _prime_history_batch(
    identities: list[dict[str, Any]],
    *,
    interval: str,
    range_name: str,
) -> dict[str, Any]:
    if not identities:
        return {"rows": [], "provider_call_count": 0}
    if interval != "1d":
        return {
            "rows": [
                {
                    "symbol": identity["symbol"],
                    "status": "skipped",
                    "source_status": "unavailable",
                    "history_row_count": 0,
                    "fetched_at": None,
                    "data_gap": "Bounded watchlist batch materialization currently supports 1d history only.",
                }
                for identity in identities
            ],
            "provider_call_count": 0,
        }
    provider_symbols = [str(identity["provider_symbol"]) for identity in identities]
    raw, status = fetch_multi_history(provider_symbols, period=_period_for_range(range_name))
    fetched_at = status.fetched_at.astimezone(timezone.utc)
    output = []
    for identity in identities:
        frame = _frame_for_symbol(raw, str(identity["provider_symbol"]))
        rows = _history_rows(frame)
        if rows:
            record = RuntimeCacheRecord(
                key=history_cache_key(
                    str(identity["asset_class"]),
                    str(identity["symbol"]),
                    interval,
                    range_name,
                ),
                data=rows,
                source=str(identity["symbol"]),
                provider="yfinance",
                source_url=f"https://finance.yahoo.com/quote/{identity['provider_symbol']}",
                fetched_at=fetched_at,
            )
            save_runtime_cache_record(record)
            output.append(
                {
                    "symbol": identity["symbol"],
                    "status": "fresh",
                    "source_status": "live/fresh",
                    "history_row_count": len(rows),
                    "fetched_at": record.fetched_at_iso,
                    "data_gap": None,
                }
            )
        else:
            output.append(
                {
                    "symbol": identity["symbol"],
                    "status": "failed",
                    "source_status": "unavailable",
                    "history_row_count": 0,
                    "fetched_at": fetched_at.isoformat(),
                    "data_gap": status.error or "No usable same-symbol history returned by the bounded batch.",
                }
            )
    return {"rows": output, "provider_call_count": 1}


def _cached_histories(
    identities: list[dict[str, Any]],
    *,
    interval: str,
    range_name: str,
    current_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    histories: dict[str, list[dict[str, Any]]] = {}
    expected = {
        str(row.get("symbol") or ""): row
        for row in current_rows
        if isinstance(row, dict) and row.get("symbol")
    }
    for identity in identities:
        symbol = str(identity["symbol"])
        expected_row = expected.get(symbol) or {}
        record = load_runtime_cache_record(
            history_cache_key(
                str(identity["asset_class"]),
                symbol,
                interval,
                range_name,
            )
        )
        expected_count = int(expected_row.get("history_row_count") or 0)
        if (
            record is not None
            and isinstance(record.data, list)
            and record.data
            and len(record.data) == expected_count
            and record.fetched_at_iso == expected_row.get("fetched_at")
        ):
            histories[symbol] = [
                row for row in record.data if isinstance(row, dict)
            ]
    return histories


def _save_research_snapshot_rows(
    rows: list[dict[str, Any]],
    *,
    fetched_at: str,
) -> None:
    try:
        cache_time = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        cache_time = datetime.now(timezone.utc)
    for row in rows:
        identity = row.get("identity") if isinstance(row.get("identity"), dict) else {}
        symbol = str(row.get("symbol") or identity.get("symbol") or "").upper()
        asset_class = str(identity.get("asset_class") or "equity").lower()
        if not symbol:
            continue
        save_runtime_cache_record(
            RuntimeCacheRecord(
                key=research_snapshot_cache_key(asset_class, symbol),
                data=row,
                source=symbol,
                provider="watchlist-research-snapshot",
                source_url="https://www.alphavantage.co/documentation/ ; https://finnhub.io/docs/api",
                fetched_at=cache_time,
            )
        )


def _write_job(row: dict[str, Any], *, db_path: str | Path | None) -> None:
    execute_query(
        """
        INSERT OR REPLACE INTO watchlist_materialization_jobs (
            job_id, list_id, status, requested_count, completed_count, failed_count,
            skipped_count, provider_call_budget, provider_call_count, queue_depth,
            duration_ms, interval, range_name, started_at, completed_at, last_error,
            rows_json, created_at
        ) VALUES (
            :job_id, :list_id, :status, :requested_count, :completed_count, :failed_count,
            :skipped_count, :provider_call_budget, :provider_call_count, :queue_depth,
            :duration_ms, :interval, :range_name, :started_at, :completed_at, :last_error,
            :rows_json, :created_at
        )
        """,
        row,
        db_path=db_path,
    )


def _job_result(row: dict[str, Any]) -> dict[str, Any]:
    return _decode_job(row) or {}


def _materialization_job_summary(job: dict[str, Any] | None) -> dict[str, Any] | None:
    if not job:
        return None
    summary = dict(job)
    summary.pop("rows", None)
    return summary


def materialize_watchlist(
    list_id: str = "primary",
    *,
    interval: str = "1d",
    range_name: str = "3mo",
    max_symbols: int = MAX_MATERIALIZE_SYMBOLS,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    collection = _require_watchlist(list_id, db_path)
    lock_key = materialization_lock_key(collection["list_id"], db_path=db_path)
    with _ACTIVE_MATERIALIZATIONS_LOCK:
        if lock_key in _ACTIVE_MATERIALIZATIONS:
            return {
                "job_id": None,
                "list_id": collection["list_id"],
                "status": "busy",
                "requested_count": 0,
                "completed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "provider_call_budget": 0,
                "provider_call_count": 0,
                "queue_depth": 0,
                "duration_ms": 0,
                "interval": interval,
                "range": range_name,
                "started_at": None,
                "completed_at": None,
                "last_error": "another materialization is active",
                "rows": [],
                "broad_universe_rebuild": False,
                "installed_background_service": False,
            }
        _ACTIVE_MATERIALIZATIONS.add(lock_key)

    started_clock = time.perf_counter()
    started_at = utc_now()
    job_id = new_id("watchmat")
    bounded_max = max(1, min(int(max_symbols), MAX_MATERIALIZE_SYMBOLS))
    items = list_watchlist_symbols(collection["list_id"], db_path=db_path)
    selected = items[:bounded_max]
    previous_job = latest_materialization_job(collection["list_id"], db_path=db_path)
    previous_rows = {
        str(row.get("symbol") or "").upper(): row
        for row in (previous_job or {}).get("rows", [])
        if isinstance(row, dict) and row.get("symbol")
    }
    skipped_count = max(0, len(items) - len(selected))
    identities = []
    preflight_rows = []
    for item in selected:
        identity = resolve_symbol(str(item["symbol"]), asset_class=str(item["asset_class"]))
        if identity:
            identities.append(identity)
        else:
            preflight_rows.append(
                {
                    "symbol": item["symbol"],
                    "status": "failed",
                    "source_status": "unavailable",
                    "history_row_count": 0,
                    "fetched_at": None,
                    "data_gap": "Exact identity became unavailable before materialization.",
                }
            )
    try:
        provider_result = _prime_history_batch(
            identities,
            interval=str(interval or "1d").lower(),
            range_name=str(range_name or "3mo").lower(),
        )
        normalized_interval = str(interval or "1d").lower()
        normalized_range = str(range_name or "3mo").lower()
        histories = _cached_histories(
            identities,
            interval=normalized_interval,
            range_name=normalized_range,
            current_rows=list(provider_result.get("rows") or []),
        )
        research_identities = [
            identity
            for identity in identities
            if histories.get(str(identity["symbol"]))
        ]
        research_result = (
            build_research_snapshot_rows(
                research_identities,
                histories,
                overview_fetcher=fetch_alpha_vantage_overview,
                earnings_fetcher=fetch_finnhub_earnings_calendar,
                news_fetcher=fetch_finnhub_company_news,
                previous_rows=previous_rows,
                history_call_count=int(provider_result.get("provider_call_count") or 0),
                max_symbols=len(research_identities),
            )
            if research_identities
            else None
        )
        research_by_symbol = {
            str(row.get("symbol") or "").upper(): row
            for row in (research_result or {}).get("rows", [])
            if isinstance(row, dict) and row.get("symbol")
        }
        rows = [*preflight_rows]
        for history_row in list(provider_result.get("rows") or []):
            symbol = str(history_row.get("symbol") or "").upper()
            research_row = research_by_symbol.get(symbol)
            rows.append(
                {
                    **history_row,
                    **(research_row or {}),
                    "history_row_count": history_row.get("history_row_count", 0),
                }
            )
        if research_result:
            _save_research_snapshot_rows(
                list(research_result.get("rows") or []),
                fetched_at=str(research_result.get("generated_at") or started_at),
            )
        completed_count = sum(1 for row in rows if row.get("status") == "fresh")
        failed_count = sum(1 for row in rows if row.get("status") == "failed")
        skipped_count += sum(1 for row in rows if row.get("status") == "skipped")
        status = "completed" if rows and completed_count == len(rows) else "failed" if rows and failed_count == len(rows) else "partial" if rows else "empty"
        completed_at = utc_now()
        row = {
            "job_id": job_id,
            "list_id": collection["list_id"],
            "status": status,
            "requested_count": len(selected),
            "completed_count": completed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "provider_call_budget": (
                int(research_result["provider_budget"]["maximum_calls"])
                if research_result
                else len(selected)
            ),
            "provider_call_count": (
                int(research_result["provider_budget"]["actual_calls"])
                if research_result
                else min(int(provider_result.get("provider_call_count") or 0), len(selected))
            ),
            "queue_depth": len(selected),
            "duration_ms": int((time.perf_counter() - started_clock) * 1000),
            "interval": str(interval or "1d").lower(),
            "range_name": str(range_name or "3mo").lower(),
            "started_at": started_at,
            "completed_at": completed_at,
            "last_error": "" if status in {"completed", "empty"} else "one or more symbols were not materialized",
            "rows_json": json_dumps(
                {
                    "rows": rows,
                    "provider_budget": (
                        research_result.get("provider_budget")
                        if research_result
                        else None
                    ),
                }
            ),
            "created_at": started_at,
        }
        _write_job(row, db_path=db_path)
        return _job_result(row)
    except Exception:
        completed_at = utc_now()
        row = {
            "job_id": job_id,
            "list_id": collection["list_id"],
            "status": "failed",
            "requested_count": len(selected),
            "completed_count": 0,
            "failed_count": len(selected),
            "skipped_count": skipped_count,
            "provider_call_budget": len(selected),
            "provider_call_count": 0,
            "queue_depth": len(selected),
            "duration_ms": int((time.perf_counter() - started_clock) * 1000),
            "interval": str(interval or "1d").lower(),
            "range_name": str(range_name or "3mo").lower(),
            "started_at": started_at,
            "completed_at": completed_at,
            "last_error": "watchlist materialization failed",
            "rows_json": "[]",
            "created_at": started_at,
        }
        _write_job(row, db_path=db_path)
        return _job_result(row)
    finally:
        with _ACTIVE_MATERIALIZATIONS_LOCK:
            _ACTIVE_MATERIALIZATIONS.discard(lock_key)


def latest_materialization_job(
    list_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    normalized_id = _list_id(list_id)
    row = execute_query(
        """
        SELECT * FROM watchlist_materialization_jobs
        WHERE list_id = ? ORDER BY started_at DESC, job_id DESC LIMIT 1
        """,
        (normalized_id,),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    return _decode_job(row if isinstance(row, dict) else None)


def list_materialization_jobs(
    list_id: str,
    *,
    limit: int = 20,
    completed_only: bool = False,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    normalized_id = _list_id(list_id)
    bounded_limit = max(1, min(int(limit), 100))
    where_status = "AND status = 'completed'" if completed_only else ""
    rows = execute_query(
        f"""
        SELECT * FROM watchlist_materialization_jobs
        WHERE list_id = ? {where_status}
        ORDER BY started_at DESC, job_id DESC LIMIT ?
        """,
        (normalized_id, bounded_limit),
        fetch=True,
        db_path=db_path,
    )
    return [
        decoded
        for row in (rows if isinstance(rows, list) else [])
        if (decoded := _decode_job(row if isinstance(row, dict) else None)) is not None
    ]


def build_watchlist_change_contract(
    list_id: str,
    *,
    db_path: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    collection = _require_watchlist(list_id, db_path)
    jobs = list_materialization_jobs(collection["list_id"], limit=20, db_path=db_path)
    successes = [row for row in jobs if row.get("status") == "completed" and row.get("rows")]
    current = successes[0] if successes else None
    previous = successes[1] if len(successes) > 1 else None
    diff = build_research_snapshot_diff(previous, current, now=now)
    lock_key = materialization_lock_key(collection["list_id"], db_path=db_path)
    with _ACTIVE_MATERIALIZATIONS_LOCK:
        busy = lock_key in _ACTIVE_MATERIALIZATIONS
    background_enabled = str(os.getenv("WATCHLIST_BACKGROUND_REFRESH_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}
    alert_kill_switch = str(os.getenv("WATCHLIST_CHANGE_ALERT_KILL_SWITCH", "")).strip().lower() in {"1", "true", "yes", "on"}
    operations = build_refresh_operations_contract(
        jobs,
        now=now,
        background_enabled=background_enabled,
        busy=busy,
    )
    alert_readiness = change_alert_readiness_for_list(
        collection["list_id"],
        diff,
        db_path=db_path,
        now=now,
        kill_switch=alert_kill_switch,
    )
    return {
        "list_id": collection["list_id"],
        "list_name": collection["name"],
        "change_inbox": diff,
        "refresh_operations": operations,
        "alert_readiness": alert_readiness,
        "privacy_scope": "local-private",
        "provider_call_count": 0,
        "caveat": "Saved-snapshot comparison is observation-only and makes no provider request.",
        "not_financial_advice": True,
    }


def build_watchlist_desk_contract(
    *,
    list_id: str = "primary",
    selected_symbol: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    collection = _require_watchlist(list_id, db_path)
    collections = list_watchlists(db_path)
    items = list_watchlist_symbols(collection["list_id"], db_path=db_path)
    requested = str(selected_symbol or "").upper().strip()
    selected = next((row for row in items if row["symbol"] == requested), None)
    if selected is None and items:
        selected = items[0]
    jobs = list_materialization_jobs(collection["list_id"], limit=20, db_path=db_path)
    latest_job = jobs[0] if jobs else None
    successful_jobs = [row for row in jobs if row.get("status") == "completed" and row.get("rows")]
    latest_success = successful_jobs[0] if successful_jobs else None
    previous_success = successful_jobs[1] if len(successful_jobs) > 1 else None
    change_inbox = build_research_snapshot_diff(previous_success, latest_success)
    lock_key = materialization_lock_key(collection["list_id"], db_path=db_path)
    with _ACTIVE_MATERIALIZATIONS_LOCK:
        busy = lock_key in _ACTIVE_MATERIALIZATIONS
    operations = build_refresh_operations_contract(
        jobs,
        background_enabled=str(os.getenv("WATCHLIST_BACKGROUND_REFRESH_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"},
        busy=busy,
    )
    alert_readiness = change_alert_readiness_for_list(
        collection["list_id"],
        change_inbox,
        db_path=db_path,
        kill_switch=str(os.getenv("WATCHLIST_CHANGE_ALERT_KILL_SWITCH", "")).strip().lower() in {"1", "true", "yes", "on"},
    )
    states = {
        str(row.get("symbol")): row
        for row in (latest_success or {}).get("rows", [])
        if isinstance(row, dict)
    }
    desk_items = []
    for item in items:
        state = states.get(str(item["symbol"])) or {}
        quote = state.get("quote") if isinstance(state.get("quote"), dict) else {}
        financials = state.get("financials") if isinstance(state.get("financials"), dict) else {}
        financial_metrics = (
            financials.get("metrics")
            if isinstance(financials.get("metrics"), dict)
            else {}
        )
        advanced = {
            **_cached_watchlist_metrics(item),
            **(state.get("performance") if isinstance(state.get("performance"), dict) else {}),
            **(state.get("risk") if isinstance(state.get("risk"), dict) else {}),
            **(state.get("technicals") if isinstance(state.get("technicals"), dict) else {}),
            **financial_metrics,
            "financial_source_status": financials.get("source_status"),
            "financial_fetched_at": financials.get("fetched_at"),
            "financial_data_gap": financials.get("data_gap"),
        }
        desk_items.append(
            {
                **item,
                "last_price": quote.get("last_price", item.get("last_price")),
                "change_pct": quote.get("change_pct", item.get("change_pct")),
                "market_provider": quote.get("provider", item.get("market_provider")),
                "market_source_url": quote.get("source_url", item.get("market_source_url")),
                "market_fetched_at": quote.get("retrieved_at", item.get("market_fetched_at")),
                "source_status": state.get("source_status") or item.get("source_status"),
                "freshness": state.get("source_status") or item.get("freshness"),
                "advanced": advanced,
                "catalysts": (
                    state.get("catalysts")
                    if isinstance(state.get("catalysts"), dict)
                    else {
                        "availability": "unavailable",
                        "earnings": [],
                        "dividends": [],
                        "news": [],
                        "next_event": None,
                        "source_status": "unavailable",
                        "data_gap": "No bounded Research Snapshot has been materialized.",
                    }
                ),
                "research_snapshot_version": state.get("research_snapshot_version"),
                "source_register": (
                    state.get("source_register")
                    if isinstance(state.get("source_register"), list)
                    else []
                ),
                "refresh_status": state.get("status") or "not-materialized",
                "refresh_fetched_at": state.get("fetched_at"),
                "refresh_data_gap": state.get("data_gap"),
            }
        )
    selected = next((row for row in desk_items if selected and row["item_id"] == selected["item_id"]), None)
    return {
        "watchlist_desk_version": WATCHLIST_DESK_VERSION,
        "workspace": "watchlist-desk",
        "privacy_scope": "local-private",
        "collections": collections,
        "active_list": collection,
        "items": desk_items,
        "selected": selected,
        "change_inbox": change_inbox,
        "refresh_operations": operations,
        "alert_readiness": alert_readiness,
        "materialization": {
            "version": WATCHLIST_MATERIALIZATION_VERSION,
            "latest_job": _materialization_job_summary(latest_job),
            "latest_success": _materialization_job_summary(latest_success),
            "limits": {
                "maximum_symbols_per_job": MAX_MATERIALIZE_SYMBOLS,
                "maximum_concurrency": MAX_MATERIALIZE_CONCURRENCY,
                "maximum_provider_calls": MAX_RESEARCH_PROVIDER_CALLS,
                "ttl_seconds": RESEARCH_SNAPSHOT_TTL_SECONDS,
            },
            "manual_only": True,
            "installed_background_service": False,
            "broad_universe_rebuild": False,
        },
        "summary": {
            "list_count": len(collections),
            "item_count": len(desk_items),
            "selected_symbol": (selected or {}).get("symbol"),
            "fresh_count": sum(1 for row in desk_items if row.get("refresh_status") == "fresh"),
            "stale_count": sum(1 for row in desk_items if row.get("refresh_status") == "stale"),
            "failed_count": sum(1 for row in desk_items if row.get("refresh_status") == "failed"),
            "research_enriched_count": sum(
                1
                for row in desk_items
                if row.get("research_snapshot_version")
                and (
                    row.get("advanced", {}).get("market_cap") is not None
                    or row.get("catalysts", {}).get("availability") == "available"
                )
            ),
            "source_status": "local-private",
            "non_advisory": True,
        },
        "privacy": {
            "scope": "local-private",
            "private_reason_stored_locally": True,
            "private_reason_in_payload": False,
            "private_reason_in_url": False,
            "private_reason_in_fixture": False,
            "private_reason_in_external_ai": False,
            "private_reason_in_logs": False,
            "private_reason_in_release": False,
        },
        "readiness": {
            "local_persistence": True,
            "exact_identity_required": True,
            "materialization": "manual-bounded",
            "hosted_sync": "unavailable",
            "hosted_auth": "unavailable",
        },
        "caveat": "Local-private watchlist research context. Quotes may be delayed and materialization is manual; no execution or recommendation is provided.",
    }


def build_watchlist_desk_fixture_contract() -> dict[str, Any]:
    symbols = ["AAPL", "TSLA", "JNJ", "TTE", "TMUS"]
    fixture_identities = {
        "AAPL": {
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "mic": "XNAS",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
        "TSLA": {
            "name": "Tesla, Inc.",
            "exchange": "NASDAQ",
            "mic": "XNAS",
            "sector": "Consumer Cyclical",
            "industry": "Auto Manufacturers",
        },
        "JNJ": {
            "name": "Johnson & Johnson",
            "exchange": "NYSE",
            "mic": "XNYS",
            "sector": "Healthcare",
            "industry": "Drug Manufacturers",
        },
        "TTE": {
            "name": "TotalEnergies SE",
            "exchange": "NYSE",
            "mic": "XNYS",
            "sector": "Energy",
            "industry": "Integrated Oil & Gas",
        },
        "TMUS": {
            "name": "T-Mobile US, Inc.",
            "exchange": "NASDAQ",
            "mic": "XNAS",
            "sector": "Communication Services",
            "industry": "Telecom Services",
        },
    }
    fixture_values = {
        "AAPL": (214.35, 3_240_000_000_000, 31.4, 7.12, "2026-07-29", "2026-08-10"),
        "TSLA": (393.45, 1_260_000_000_000, 188.2, 2.09, "2026-07-23", None),
        "JNJ": (166.28, 400_000_000_000, 24.8, 6.70, "2026-07-15", "2026-08-26"),
        "TTE": (68.42, 156_000_000_000, 9.6, 7.13, "2026-07-24", "2026-09-24"),
        "TMUS": (238.17, 270_000_000_000, 22.9, 10.40, "2026-07-30", "2026-08-29"),
    }
    items = []
    snapshot_rows = []
    for position, symbol in enumerate(symbols):
        identity = fixture_identities[symbol]
        last_price, market_cap, pe_ratio, eps, earnings_date, ex_dividend_date = fixture_values[symbol]
        start = last_price * 0.82
        history = [
            {
                "date": (datetime(2026, 4, 1, tzinfo=timezone.utc) + timedelta(days=index)).date().isoformat(),
                "close": round(start + (last_price - start) * index / 69 + ((index % 5) - 2) * 0.15, 4),
                "volume": 1_000_000 + position * 200_000 + index * 2_000,
            }
            for index in range(70)
        ]
        history[-1]["close"] = last_price
        advanced = {
            **compute_watchlist_advanced_metrics(history),
            "market_cap": market_cap,
            "revenue_ttm": market_cap * 0.12,
            "eps": eps,
            "pe_ratio": pe_ratio,
            "annual_dividend_per_share": None if symbol == "TSLA" else round(eps * 0.13, 2),
            "dividend_yield": None if symbol == "TSLA" else 0.009 + position * 0.004,
            "financial_source_status": "fixture",
            "financial_fetched_at": "2026-07-03T00:00:00+00:00",
            "financial_data_gap": None,
        }
        earnings = {
            "symbol": symbol,
            "event_type": "scheduled-earnings",
            "event_date": earnings_date,
            "estimated_eps": round(eps / 4, 2),
            "reported_eps": None,
            "provider": "phase6f fictional fixture",
            "source_url": None,
            "source_status": "fixture",
            "fetched_at": "2026-07-03T00:00:00+00:00",
            "not_financial_advice": True,
        }
        dividends = (
            [
                {
                    "symbol": symbol,
                    "event_type": "dividend",
                    "ex_dividend_date": ex_dividend_date,
                    "payment_date": None,
                    "amount": advanced["annual_dividend_per_share"],
                    "yield": advanced["dividend_yield"],
                    "provider": "phase6f fictional fixture",
                    "source_url": None,
                    "source_status": "fixture",
                    "fetched_at": "2026-07-03T00:00:00+00:00",
                    "not_financial_advice": True,
                }
            ]
            if ex_dividend_date
            else []
        )
        news = [
            {
                "title": f"{symbol} deterministic catalyst fixture",
                "summary": "Fictional row for network-free interaction and layout QA.",
                "published_at": "2026-07-02T18:00:00+00:00",
                "source_url": None,
                "provider": "phase6f fictional fixture",
                "source_status": "fixture",
                "fetched_at": "2026-07-03T00:00:00+00:00",
                "exact_symbol_scope": True,
                "match_terms": [symbol],
                "match_evidence": {
                    "symbol": symbol,
                    "scope": "fictional-exact-symbol-fixture",
                    "exact": True,
                    "terms": [symbol],
                },
                "not_financial_advice": True,
            }
        ]
        catalysts = {
            "symbol": symbol,
            "availability": "fixture",
            "source_status": "fixture",
            "fetched_at": "2026-07-03T00:00:00+00:00",
            "earnings": [earnings],
            "dividends": dividends,
            "news": news,
            "next_event": earnings,
            "caveat": "Fictional deterministic catalysts for network-free product QA.",
            "data_gap": "No current provider event is claimed in fixture mode.",
            "not_financial_advice": True,
        }
        source_register = [
            {
                "provider": "phase6f fictional fixture",
                "source": f"{symbol} research snapshot",
                "source_url": None,
                "source_status": "fixture",
                "fetched_at": "2026-07-03T00:00:00+00:00",
                "row_count": 1,
                "caveat": "Deterministic and non-current.",
                "data_gap": "Use local mode and run a bounded refresh for provider-backed values.",
                "not_financial_advice": True,
            }
        ]
        snapshot_rows.append(
            {
                "research_snapshot_version": RESEARCH_SNAPSHOT_VERSION,
                "symbol": symbol,
                "status": "fixture",
                "source_status": "fixture",
                "fetched_at": "2026-07-03T00:00:00+00:00",
                "quote": {
                    "last_price": last_price,
                    "change_pct": advanced["return_1w_pct"],
                    "source_status": "fixture",
                },
                "performance": advanced,
                "risk": advanced,
                "technicals": advanced,
                "financials": {
                    "availability": "fixture",
                    "source_status": "fixture",
                    "metrics": {
                        "market_cap": market_cap,
                        "revenue_ttm": advanced["revenue_ttm"],
                        "eps": eps,
                        "pe_ratio": pe_ratio,
                    },
                },
                "catalysts": catalysts,
                "source_register": source_register,
                "data_gap": "Fictional deterministic snapshot; no live market claim.",
                "not_financial_advice": True,
            }
        )
        items.append(
            {
                "item_id": f"fixture-watch-{symbol.lower()}",
                "list_id": "fixture-daily",
                "position": position,
                "symbol": symbol,
                "name": identity["name"],
                "asset_class": "equity",
                "exchange": identity.get("exchange"),
                "mic": identity.get("mic"),
                "cik": None,
                "sector": identity.get("sector"),
                "industry": identity.get("industry"),
                "identity_origin": "phase6d-qa-fixture",
                "identity_status": "exact",
                "last_price": last_price,
                "change_pct": advanced["return_1w_pct"],
                "source_status": "fixture",
                "freshness": "fixture",
                "capability": "workstation",
                "refresh_status": "fixture",
                "refresh_fetched_at": "2026-07-03T00:00:00+00:00",
                "refresh_data_gap": "Fictional deterministic snapshot; no current market observation is claimed.",
                "not_financial_advice": True,
                "advanced": advanced,
                "catalysts": catalysts,
                "research_snapshot_version": RESEARCH_SNAPSHOT_VERSION,
                "source_register": source_register,
            }
        )
    collection = {
        "list_id": "fixture-daily",
        "name": "Daily Radar",
        "position": 0,
        "active": True,
        "item_count": len(items),
        "created_at": "2026-07-02T00:00:00+00:00",
        "updated_at": "2026-07-02T00:00:00+00:00",
    }
    previous_rows = copy.deepcopy(snapshot_rows)
    for index, row in enumerate(previous_rows):
        if index >= 2:
            continue
        quote = row.get("quote") if isinstance(row.get("quote"), dict) else {}
        quote["last_price"] = round(float(quote.get("last_price") or 0) * (0.975 - index * 0.002), 4)
        catalysts = row.get("catalysts") if isinstance(row.get("catalysts"), dict) else {}
        earnings = catalysts.get("earnings") if isinstance(catalysts.get("earnings"), list) else []
        if earnings:
            current_date = datetime.fromisoformat(str(earnings[0]["event_date"]))
            earnings[0]["event_date"] = (current_date - timedelta(days=1 + index % 2)).date().isoformat()
        catalysts["news"] = []
    previous_job = {
        "job_id": "fixture-phase6g-previous",
        "list_id": "fixture-daily",
        "status": "completed",
        "requested_count": 5,
        "completed_count": 5,
        "failed_count": 0,
        "skipped_count": 0,
        "provider_call_budget": MAX_RESEARCH_PROVIDER_CALLS,
        "provider_call_count": 0,
        "queue_depth": 0,
        "duration_ms": 0,
        "interval": "1d",
        "range": "3mo",
        "started_at": "2026-07-02T00:00:00+00:00",
        "completed_at": "2026-07-02T00:00:00+00:00",
        "last_error": None,
        "rows": previous_rows,
        "provider_budget": {**default_provider_budget(max_symbols=5), "actual_calls": 0, "cache_hits": 0},
    }
    current_job = {
        **previous_job,
        "job_id": "fixture-phase6g-current",
        "started_at": "2026-07-03T00:00:00+00:00",
        "completed_at": "2026-07-03T00:00:00+00:00",
        "rows": snapshot_rows,
    }
    change_inbox = build_research_snapshot_diff(previous_job, current_job, now=datetime(2026, 7, 3, tzinfo=timezone.utc))
    fixture_rule = {
        "alert_id": "fixture-alert-rule",
        "active": True,
        "threshold": "material",
        "cooldown_minutes": 60,
        "expires_at": None,
        "last_triggered_at": None,
        "metadata_json": {
            "minimum_severity": "material",
            "delivery": "preview-only",
            "opt_in": True,
        },
    }
    return {
        "watchlist_desk_version": WATCHLIST_DESK_VERSION,
        "workspace": "watchlist-desk",
        "privacy_scope": "fictional-demo",
        "collections": [collection],
        "active_list": collection,
        "items": items,
        "selected": items[0] if items else None,
        "change_inbox": change_inbox,
        "refresh_operations": {
            **build_refresh_operations_contract(
                [current_job, previous_job],
                now=datetime(2026, 7, 3, tzinfo=timezone.utc),
                background_enabled=False,
            ),
            "source_status": "fixture",
        },
        "alert_readiness": {
            **build_change_alert_preview(
                change_inbox,
                rule=fixture_rule,
                events=[],
                now=datetime(2026, 7, 3, tzinfo=timezone.utc),
            ),
            "source_status": "fixture",
            "fictional": True,
        },
        "materialization": {
            "version": WATCHLIST_MATERIALIZATION_VERSION,
            "latest_job": _materialization_job_summary({
                "job_id": "fixture-phase6f-research",
                "list_id": "fixture-daily",
                "status": "fixture",
                "requested_count": 5,
                "completed_count": 5,
                "failed_count": 0,
                "skipped_count": 0,
                "provider_call_budget": MAX_RESEARCH_PROVIDER_CALLS,
                "provider_call_count": 0,
                "queue_depth": 0,
                "duration_ms": 0,
                "interval": "1d",
                "range": "3mo",
                "started_at": "2026-07-03T00:00:00+00:00",
                "completed_at": "2026-07-03T00:00:00+00:00",
                "last_error": None,
                "rows": snapshot_rows,
                "provider_budget": {
                    **default_provider_budget(max_symbols=5),
                    "actual_calls": 0,
                    "cache_hits": 0,
                    "next_safe_refresh_at": None,
                },
                "broad_universe_rebuild": False,
                "installed_background_service": False,
            }),
            "latest_success": _materialization_job_summary(current_job),
            "limits": {
                "maximum_symbols_per_job": MAX_MATERIALIZE_SYMBOLS,
                "maximum_concurrency": MAX_MATERIALIZE_CONCURRENCY,
                "maximum_provider_calls": MAX_RESEARCH_PROVIDER_CALLS,
                "ttl_seconds": RESEARCH_SNAPSHOT_TTL_SECONDS,
            },
            "manual_only": True,
            "installed_background_service": False,
            "broad_universe_rebuild": False,
        },
        "summary": {
            "list_count": 1,
            "item_count": len(items),
            "selected_symbol": items[0]["symbol"] if items else None,
            "fresh_count": 0,
            "stale_count": 0,
            "failed_count": 0,
            "research_enriched_count": len(items),
            "source_status": "fixture",
            "non_advisory": True,
        },
        "privacy": {
            "scope": "fictional-demo",
            "private_reason_stored_locally": False,
            "private_reason_in_payload": False,
            "private_reason_in_url": False,
            "private_reason_in_fixture": False,
            "private_reason_in_external_ai": False,
            "private_reason_in_logs": False,
            "private_reason_in_release": False,
        },
        "readiness": {
            "local_persistence": False,
            "exact_identity_required": True,
            "materialization": "deterministic-fixture",
            "hosted_sync": "unavailable",
            "hosted_auth": "unavailable",
        },
        "caveat": "Fictional deterministic watchlist for network-free UI development. No current quote is claimed.",
    }
