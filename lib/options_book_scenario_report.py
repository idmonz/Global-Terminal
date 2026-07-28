from __future__ import annotations

from pathlib import Path
from typing import Any
from .options_book_stress import build_option_book_stress_snapshot
from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE
from .report_inbox import create_report


def build_option_book_stress_report(rows_or_positions: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot = build_option_book_stress_snapshot(rows_or_positions)
    body = ["# Option Book Stress Report", "", GOAL12B_RESEARCH_ONLY_NOTICE, "", f"- Positions: {len(snapshot.get('risk_snapshot', {}).get('positions', []))}", "- Source: user supplied local positions", "- Scenario values are deterministic research stress calculations."]
    return {"ok": True, "report_type": "options_book_stress_report", "title": "Option Book Stress Report", "markdown_body": "\n".join(body), "snapshot": snapshot, "research_only": True}


def generate_option_book_stress_report(rows_or_positions: list[dict[str, Any]], *, persist: bool = False, db_path: str | Path | None = None) -> dict[str, Any]:
    report = build_option_book_stress_report(rows_or_positions)
    if persist:
        created = create_report(report_type="options_book_stress_report", title=report["title"], summary="Supplied option-book stress report.", markdown_body=report["markdown_body"], source_snapshot=report["snapshot"].get("source_snapshot"), data_confidence="user_supplied", provider_gaps=["supplied_positions_only"], attachments=[{"attachment_type": "options_book_stress", "payload": report["snapshot"], "research_only": True}], tags=["options", "stress", "goal12c"], db_path=db_path)
        report["report_id"] = created["report_id"]
        report["persisted_report"] = created
    return report
