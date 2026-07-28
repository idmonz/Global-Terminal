from __future__ import annotations
from typing import Any


def build_options_case_selector_payload(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {"title": "Options Research Cases", "cases": cases, "case_count": len(cases), "private_storage": True, "research_only": True}


def build_options_case_timeline_panel(case: dict[str, Any]) -> dict[str, Any]:
    return {"title": "Options Case Timeline", "case_id": case.get("case_id"), "timeline": case.get("timeline", []), "artifacts": case.get("artifacts", {}), "private_storage": True, "research_only": True}
