from __future__ import annotations
from pathlib import Path
from typing import Any
from .quant_diagnostics_report import build_quant_diagnostics_report
from .report_inbox import create_report
from .strategy_decision_log import attach_report_to_commit


def attach_quant_diagnostics_to_report(prices_by_asset: dict[str, list[float]], *, db_path: str | Path | None = None) -> dict[str, Any]:
    report=build_quant_diagnostics_report(prices_by_asset)
    created=create_report(report_type='quant_diagnostics_report', title=report['title'], summary='Local supplied-data quant diagnostics.', markdown_body=report['markdown_body'], source_snapshot=report['snapshot'].get('source_snapshot'), data_confidence='user_supplied', provider_gaps=['supplied_series_only','no_prediction_claim'], attachments=[{'attachment_type':'quant_diagnostics_snapshot','payload':report['snapshot'],'research_only':True}], tags=['quant_diagnostics','goal12b'], db_path=db_path)
    return {'ok': True, 'report_id': created['report_id'], 'report': created, 'snapshot': report['snapshot'], 'research_only': True}


def attach_quant_diagnostics_to_strategy_commit(commit_id: str, prices_by_asset: dict[str, list[float]], *, db_path: str | Path | None = None) -> dict[str, Any]:
    attached=attach_quant_diagnostics_to_report(prices_by_asset, db_path=db_path)
    commit=attach_report_to_commit(commit_id, attached['report_id'], db_path=db_path)
    return {'ok': bool(commit), 'commit_id': commit_id, 'report_id': attached['report_id'], 'commit': commit, 'research_only': True}
