from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .options_chain_normalizer import infer_option_chain_columns, normalize_option_chain_rows
from .options_chain_quality import label_option_chain_freshness, summarize_option_chain_quality
from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE
from .options_chain_validation import validate_option_chain_rows

MAX_CSV_BYTES = 5_000_000
MAX_CELL_CHARS = 5_000


def _safe_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    if len(text) > MAX_CELL_CHARS:
        text = text[:MAX_CELL_CHARS] + "...TRUNCATED"
    return text


def parse_option_chain_csv_text(csv_text: str) -> list[dict[str, Any]]:
    if len(csv_text.encode("utf-8", errors="ignore")) > MAX_CSV_BYTES:
        raise ValueError("csv_payload_too_large")
    reader = csv.DictReader(io.StringIO(csv_text))
    rows: list[dict[str, Any]] = []
    for raw in reader:
        rows.append({str(k): _safe_cell(v) for k, v in raw.items()})
    return rows


def read_option_chain_csv(path: str | Path, *, allowed_root: str | Path | None = None) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        base = Path(allowed_root or Path.cwd()).resolve()
        candidate = base / candidate
    resolved = candidate.resolve()
    if allowed_root is not None:
        base = Path(allowed_root).resolve()
        if base not in resolved.parents and resolved != base:
            raise ValueError("path_traversal_not_allowed")
    if resolved.suffix.lower() != ".csv":
        raise ValueError("only_csv_files_allowed")
    if resolved.stat().st_size > MAX_CSV_BYTES:
        raise ValueError("csv_file_too_large")
    return resolved.read_text(encoding="utf-8-sig")


def build_option_chain_snapshot(csv_text: str | None = None, *, rows: list[dict[str, Any]] | None = None, source_label: str | None = None, snapshot_id: str | None = None) -> dict[str, Any]:
    raw_rows = rows if rows is not None else parse_option_chain_csv_text(csv_text or "")
    headers = list(raw_rows[0].keys()) if raw_rows else []
    column_map = infer_option_chain_columns(headers)
    normalized = normalize_option_chain_rows(raw_rows, column_map=column_map)
    if source_label:
        for row in normalized:
            if row.get("source") == "user_supplied_unknown_source":
                row["source"] = source_label
    validation = validate_option_chain_rows(normalized)
    accepted = validation["accepted_rows"]
    quality = summarize_option_chain_quality({"rows": accepted, "rejected_rows": validation["rejected_rows"], "caveated_rows": validation["caveated_rows"]})
    max_ts = max([str(r.get("timestamp") or "") for r in accepted], default="")
    freshness = label_option_chain_freshness(max_ts) if max_ts else {"freshness": "unknown", "age_hours": None, "caveat": "no_timestamp"}
    return {
        "ok": validation["rejected_count"] == 0,
        "snapshot_id": snapshot_id or "option_chain_snapshot_supplied",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "column_map": column_map,
        "rows": accepted,
        "rejected_rows": validation["rejected_rows"],
        "caveated_rows": validation["caveated_rows"],
        "quality": quality,
        "freshness": freshness,
        "source_snapshot": {"source": source_label or "user_supplied_csv", "freshness": freshness.get("freshness"), "confidence": "user_supplied", "used_for_calculation": True},
        "notice": GOAL12B_RESEARCH_ONLY_NOTICE,
        "research_only": True,
    }
