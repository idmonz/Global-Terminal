from __future__ import annotations
from typing import Any
from .options_book_risk import build_option_book_risk_snapshot
from .options_book_schema import OPTION_BOOK_NOTICE


def build_option_book_risk_report(rows_or_snapshot: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
    snap = rows_or_snapshot if isinstance(rows_or_snapshot, dict) and 'totals' in rows_or_snapshot else build_option_book_risk_snapshot(rows_or_snapshot)  # type: ignore[arg-type]
    totals = snap.get('totals', {})
    body = [
        '# Option Book Risk Report', '', OPTION_BOOK_NOTICE, '',
        f"- Positions: {len(snap.get('positions', []))}",
        f"- Total delta: {totals.get('total_delta')}",
        f"- Total gamma: {totals.get('total_gamma')}",
        f"- Total vega 1pct: {totals.get('total_vega')}",
        f"- Total theta/day: {totals.get('total_theta_per_day')}",
        f"- Mark value: {totals.get('mark_value')}", '',
        'No portfolio advice, rebalancing instruction, or hedge instruction is generated.'
    ]
    return {'ok': True, 'report_type': 'options_book_risk_report', 'title': 'Option Book Risk Report', 'markdown_body': '\n'.join(body), 'snapshot': snap, 'notice': OPTION_BOOK_NOTICE, 'research_only': True}
