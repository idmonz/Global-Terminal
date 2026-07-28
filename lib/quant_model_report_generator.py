from __future__ import annotations

from pathlib import Path
from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE
from .quant_model_attachment_bridge import build_quant_model_attachment
from .quant_model_lab import create_quant_model_snapshot
from .report_inbox import create_report


def render_quant_model_snapshot_markdown(snapshot: dict[str, Any]) -> str:
    lines = [f"# Quant Model Snapshot — {snapshot.get('model_name', 'Model')}", "", RESEARCH_ONLY_OPTIONS_NOTICE, "", "## Category", f"- {snapshot.get('category')}", "", "## Diagnostics"]
    for key, value in snapshot.get("diagnostics", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Caveats"])
    for caveat in snapshot.get("caveats", []):
        lines.append(f"- {caveat}")
    return "\n".join(lines) + "\n"


def attach_model_snapshot_to_report(snapshot: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    snap = snapshot or create_quant_model_snapshot()
    attachment = build_quant_model_attachment(snap)
    markdown = render_quant_model_snapshot_markdown(snap)
    report = create_report(report_type="quant_model_snapshot_report", title=f"Quant Model Snapshot — {snap.get('model_name')}", summary="Local quant model snapshot attached for review.", source_snapshot={"source": "local_quant_model_lab", "freshness": "snapshot", "confidence": "deterministic-or-placeholder"}, data_confidence="deterministic-or-placeholder", attachments=[attachment], markdown_body=markdown, tags=["goal12a", "quant_model_snapshot"], db_path=db_path)
    return {"ok": True, "snapshot": snap, "attachment": attachment, "report": report, "report_id": report.get("report_id"), "research_only": True}
