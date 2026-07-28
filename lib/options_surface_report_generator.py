from __future__ import annotations
from pathlib import Path
from typing import Any
from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE
from .options_vol_surface import build_smile_table, build_skew_table, build_term_structure_table, build_vol_surface_snapshot
from .options_surface_diff import build_surface_snapshot_diff, build_surface_change_summary
from .report_inbox import create_report


def build_options_surface_report(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    smile=build_smile_table(surface_snapshot); skew=build_skew_table(surface_snapshot); term=build_term_structure_table(surface_snapshot)
    q = surface_snapshot.get('quality_score', {})
    body=['# Options Volatility Surface Report','',GOAL12B_RESEARCH_ONLY_NOTICE,'', f"- Surface points: {surface_snapshot.get('point_count')}", f"- Expiries: {surface_snapshot.get('quality',{}).get('expiry_count')}", f"- Strikes: {surface_snapshot.get('quality',{}).get('strike_count')}", f"- Quality score: {q.get('score')}", f"- Surface caveats: {', '.join(q.get('caveats', []))}", '', 'Surface uses supplied option-chain rows only. It is not a volatility forecast.']
    return {'ok': True, 'report_type': 'options_vol_surface_report', 'title': 'Options Volatility Surface Report', 'markdown_body': '\n'.join(body), 'surface_snapshot': surface_snapshot, 'smile_table': smile, 'skew_table': skew, 'term_structure_table': term, 'quality_score': q, 'notice': GOAL12B_RESEARCH_ONLY_NOTICE, 'research_only': True}


def build_options_surface_diff_report(previous_surface: dict[str, Any], current_surface: dict[str, Any]) -> dict[str, Any]:
    diff = build_surface_snapshot_diff(previous_surface, current_surface)
    summary = build_surface_change_summary(diff)
    body = ['# Options Surface Diff Report','',GOAL12B_RESEARCH_ONLY_NOTICE,'', f"- Changed rows: {summary.get('changed_row_count')}", f"- New rows: {summary.get('new_row_count')}", f"- Missing rows: {summary.get('missing_row_count')}", f"- Max absolute IV change: {summary.get('max_abs_iv_change')}", '', 'Diff compares supplied snapshots only.']
    return {'ok': True, 'report_type': 'options_surface_diff_report', 'title': 'Options Surface Diff Report', 'markdown_body': '\n'.join(body), 'diff': diff, 'summary': summary, 'research_only': True}


def generate_options_surface_report(iv_snapshot: dict[str, Any], *, persist: bool = False, db_path: str | Path | None = None) -> dict[str, Any]:
    surface=build_vol_surface_snapshot(iv_snapshot)
    report=build_options_surface_report(surface)
    if persist:
        created=create_report(report_type='options_vol_surface_report', title=report['title'], summary='Supplied-chain volatility surface snapshot.', markdown_body=report['markdown_body'], source_snapshot=surface.get('source_snapshot'), data_confidence='user_supplied', provider_gaps=['supplied_chain_only','not_forecast'], attachments=[{'attachment_type':'options_vol_surface','payload':surface,'research_only':True}], tags=['options','vol_surface','goal12c'], db_path=db_path)
        report['report_id']=created['report_id']; report['persisted_report']=created
    return report
