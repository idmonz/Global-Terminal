from __future__ import annotations
from typing import Any
from .options_book_schema import OptionBookPosition, OPTION_BOOK_NOTICE


def _f(row: dict[str, Any], field: str, default: float | None = None) -> float:
    value = row.get(field, default)
    if value in (None, ""):
        if default is None:
            raise ValueError(f"missing_{field}")
        return float(default)
    return float(value)


def normalize_option_book_positions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted=[]; rejected=[]
    for i, row in enumerate(rows, start=1):
        try:
            side=str(row.get('option_type','')).strip().lower()
            if side in {'c','call'}: side='call'
            elif side in {'p','put'}: side='put'
            else: raise ValueError('invalid_option_type')
            pos=str(row.get('position','long')).strip().lower()
            if pos not in {'long','short'}: raise ValueError('invalid_position')
            p=OptionBookPosition(
                position_id=str(row.get('position_id') or f'pos_{i}'), underlying=str(row.get('underlying') or row.get('symbol') or '').strip(),
                option_type=side, expiry=str(row.get('expiry') or row.get('expiration') or '').strip(), strike=_f(row,'strike'),
                quantity=_f(row,'quantity',1.0), position=pos, premium=_f(row,'premium',0.0), mark=_f(row,'mark', row.get('premium',0.0)),
                implied_volatility=_f(row,'implied_volatility', row.get('volatility',0.2)), underlying_price=_f(row,'underlying_price'), contract_multiplier=_f(row,'contract_multiplier',100.0),
                source=str(row.get('source') or 'user_supplied_local_position'), timestamp=str(row.get('timestamp') or ''),
                delta=None if row.get('delta') in (None,'') else float(row.get('delta')), gamma=None if row.get('gamma') in (None,'') else float(row.get('gamma')),
                vega=None if row.get('vega') in (None,'') else float(row.get('vega')), theta=None if row.get('theta') in (None,'') else float(row.get('theta')), rho=None if row.get('rho') in (None,'') else float(row.get('rho')),
            )
            if not p.underlying or not p.expiry or p.strike <= 0 or p.quantity <= 0 or p.contract_multiplier <= 0:
                raise ValueError('invalid_required_position_fields')
            item = p.to_dict()
            for extra in ("time_to_expiry_years", "tte", "asset_class", "model", "pricing_model", "futures_price", "domestic_rate", "foreign_rate", "risk_free_rate", "dividend_yield", "volatility", "snapshot_timestamp"):
                if extra in row and row.get(extra) not in (None, ""):
                    item[extra] = row.get(extra)
            accepted.append(item)
        except Exception as exc:
            rejected.append({'row_number': i, 'error': str(exc), 'row': row})
    return {'ok': len(rejected)==0, 'positions': accepted, 'rejected_positions': rejected, 'position_count': len(accepted), 'notice': OPTION_BOOK_NOTICE, 'research_only': True}
