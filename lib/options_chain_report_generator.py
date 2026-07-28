from __future__ import annotations
from pathlib import Path
from typing import Any
from .options_chain_ingestion import build_option_chain_snapshot
from .options_chain_iv import build_chain_iv_snapshot
from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE
from .report_inbox import create_report
from .research_report_sanitizer import escape_csv_formula_text as escape_report_value, sanitize_report_table_rows


def build_options_chain_report(chain_snapshot: dict[str, Any], *, include_iv: bool = True) -> dict[str, Any]:
    iv = build_chain_iv_snapshot(chain_snapshot) if include_iv else None
    quality = chain_snapshot.get('quality', {})
    rows = sanitize_report_table_rows(chain_snapshot.get('rows', [])[:10])
    lines = ['# Options Chain Snapshot Report','',GOAL12B_RESEARCH_ONLY_NOTICE,'', '## Source Snapshot', f"- Source: {escape_report_value(chain_snapshot.get('source_snapshot',{}).get('source','user_supplied_csv'))}", f"- Freshness: {escape_report_value(chain_snapshot.get('freshness',{}).get('freshness','unknown'))}", '', '## Quality', f"- Accepted rows: {quality.get('accepted_rows')}", f"- Rejected rows: {quality.get('rejected_rows')}", f"- Caveated rows: {quality.get('caveated_rows')}", '', '## Sample Rows']
    for row in rows:
        lines.append(f"- {row.get('underlying')} {row.get('expiry')} {row.get('option_type')} K={row.get('strike')} bid={row.get('bid')} ask={row.get('ask')} source={row.get('source')}")
    if iv:
        lines += ['', '## IV Diagnostics', f"- Solved mid IV rows: {iv.get('solved_count')}", f"- No-solution rows: {iv.get('no_solution_count')}", f"- Model mix: {escape_report_value(', '.join(iv.get('model_mix', [])))}"]
    lines += ['', 'CSV fields are escaped for report rendering. Local file paths are redacted.']
    return {'ok': True, 'report_type': 'options_chain_snapshot_report', 'title': 'Options Chain Snapshot Report', 'markdown_body': '\n'.join(lines), 'snapshot': chain_snapshot, 'iv_snapshot': iv, 'notice': GOAL12B_RESEARCH_ONLY_NOTICE, 'research_only': True}


def generate_options_chain_report(csv_text: str | None = None, *, rows: list[dict[str, Any]] | None = None, persist: bool = False, db_path: str | Path | None = None) -> dict[str, Any]:
    snap=build_option_chain_snapshot(csv_text, rows=rows)
    report=build_options_chain_report(snap)
    if persist:
        created=create_report(report_type='options_chain_snapshot_report', title=report['title'], summary='Supplied option-chain CSV snapshot with quality and IV diagnostics.', markdown_body=report['markdown_body'], source_snapshot=snap.get('source_snapshot'), data_confidence='user_supplied', provider_gaps=['supplied_csv_only','manual_chain_mode'], attachments=[{'attachment_type':'options_chain_snapshot','payload':snap,'research_only':True}], tags=['options','goal12c'], db_path=db_path)
        report['report_id']=created['report_id']; report['persisted_report']=created
    return report
