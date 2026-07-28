from __future__ import annotations

from pathlib import Path
from typing import Any

from .options_provider_capabilities import build_options_source_snapshot
from .options_report_generator import generate_options_pricing_report, generate_options_scenario_report
from .options_result_schema import build_options_result
from .report_inbox import create_report
from .research_attachment_models import build_research_attachment


def build_options_attachment(result: dict[str, Any], *, title: str | None = None) -> dict[str, Any]:
    source = result.get("source_snapshot") or build_options_source_snapshot("manual", used_for_calculation=True)
    return build_research_attachment("option_analysis_snapshot", title or result.get("title", "Options research snapshot"), result, source)


def attach_options_result_to_report(result: dict[str, Any], *, db_path: str | Path | None = None) -> dict[str, Any]:
    attachment = build_options_attachment(result)
    source = result.get("source_snapshot") or build_options_source_snapshot("manual", used_for_calculation=True)
    report = create_report(
        report_type=result.get("report_type", "options_pricing_report"),
        title=result.get("title", "Options Research Report"),
        summary="Options result attached as a research-only report artifact.",
        source_snapshot=source,
        data_confidence="user-supplied",
        provider_gaps=result.get("caveats", []),
        attachments=[attachment],
        markdown_body=result.get("markdown_body", ""),
        tags=["goal12a", "options", "attachment"],
        db_path=db_path,
    )
    return {"ok": True, "report_id": report["report_id"], "report": report, "attachment": attachment, "research_only": True}


def build_options_source_snapshot(provider: str = "manual", *, used_for_calculation: bool = True, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    from .options_provider_capabilities import build_options_source_snapshot as _build
    return _build(provider, used_for_calculation=used_for_calculation, extra=extra)
