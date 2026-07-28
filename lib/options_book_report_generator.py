from __future__ import annotations
from pathlib import Path
from typing import Any
from .options_book_reports import build_option_book_risk_report
from .report_inbox import create_report


def generate_options_book_risk_report(rows_or_snapshot: list[dict[str, Any]] | dict[str, Any], *, persist: bool = False, db_path: str | Path | None = None) -> dict[str, Any]:
    report=build_option_book_risk_report(rows_or_snapshot)
    snap=report['snapshot']
    if persist:
        created=create_report(report_type='options_book_risk_report', title=report['title'], summary='Supplied local option-book risk aggregation.', markdown_body=report['markdown_body'], source_snapshot=snap.get('source_snapshot'), data_confidence='user_supplied', provider_gaps=['supplied_positions_only','no_rebalancing'], attachments=[{'attachment_type':'options_book_risk','payload':snap,'research_only':True}], tags=['options','option_book','goal12b'], db_path=db_path)
        report['report_id']=created['report_id']; report['persisted_report']=created
    return report
