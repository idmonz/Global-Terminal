from __future__ import annotations
from collections import defaultdict
from typing import Any
from .options_book_ingestion import normalize_option_book_positions
from .options_book_schema import OPTION_BOOK_NOTICE
from .options_greeks import black_scholes_greeks, scale_greeks_by_contract


def _signed_qty(position: dict[str, Any]) -> float:
    sign = 1.0 if str(position.get('position','long')).lower() == 'long' else -1.0
    return sign * float(position.get('quantity',1.0))


def _position_greeks(position: dict[str, Any]) -> dict[str, float]:
    if all(position.get(k) is not None for k in ['delta','gamma','vega','theta','rho']):
        return {k: float(position.get(k,0.0)) for k in ['delta','gamma','vega','theta','rho']} | {'theta_per_day': float(position.get('theta',0.0))/365.0}
    return black_scholes_greeks(position['option_type'], float(position['underlying_price']), float(position['strike']), float(position.get('time_to_expiry_years',30/365)), float(position.get('risk_free_rate',0.0)), float(position.get('implied_volatility',0.2)))


def aggregate_option_book_greeks(positions: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {'total_delta':0.0,'total_gamma':0.0,'total_vega':0.0,'total_theta_per_day':0.0,'total_rho':0.0,'premium_value':0.0,'mark_value':0.0,'unrealized_pnl_from_supplied_mark':0.0}
    rows=[]
    for pos in positions:
        qty_signed=_signed_qty(pos)
        greeks=_position_greeks(pos)
        scaled=scale_greeks_by_contract(greeks, contract_multiplier=float(pos.get('contract_multiplier',100.0)), quantity=qty_signed, underlying_price=float(pos.get('underlying_price')))
        totals['total_delta'] += scaled['contract_delta']
        totals['total_gamma'] += scaled['contract_gamma']
        totals['total_vega'] += scaled['contract_vega_1pct']
        totals['total_theta_per_day'] += scaled['contract_theta_1day']
        totals['total_rho'] += scaled['contract_rho_1bp']
        mult=float(pos.get('contract_multiplier',100.0)); qty=float(pos.get('quantity',1.0)); sign=1.0 if pos.get('position')=='long' else -1.0
        premium_value=float(pos.get('premium',0.0))*mult*qty*sign
        mark_value=float(pos.get('mark',0.0))*mult*qty*sign
        totals['premium_value'] += premium_value; totals['mark_value'] += mark_value; totals['unrealized_pnl_from_supplied_mark'] += mark_value - premium_value
        rows.append({**pos, 'scaled_greeks': scaled, 'premium_value': premium_value, 'mark_value': mark_value, 'research_only': True})
    return {**totals, 'position_rows': rows, 'notice': OPTION_BOOK_NOTICE, 'research_only': True}


def _group_sum(positions: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in positions: buckets[str(p.get(key,''))].append(p)
    out=[]
    for name, rows in buckets.items():
        agg=aggregate_option_book_greeks(rows)
        out.append({'bucket': name, 'position_count': len(rows), **{k: agg[k] for k in ['total_delta','total_gamma','total_vega','total_theta_per_day','total_rho','mark_value']}, 'research_only': True})
    return sorted(out, key=lambda x: x['bucket'])


def aggregate_by_underlying(positions: list[dict[str, Any]]) -> list[dict[str, Any]]: return _group_sum(positions, 'underlying')
def aggregate_by_expiry(positions: list[dict[str, Any]]) -> list[dict[str, Any]]: return _group_sum(positions, 'expiry')


def aggregate_by_moneyness_bucket(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched=[]
    for p in positions:
        m=float(p['strike'])/float(p['underlying_price'])
        bucket = 'itm_put_or_otm_call_high_strike' if m > 1.05 else 'atm' if m >= 0.95 else 'itm_call_or_otm_put_low_strike'
        enriched.append({**p, 'moneyness_bucket': bucket})
    return _group_sum(enriched, 'moneyness_bucket')


def build_option_book_risk_snapshot(rows_or_positions: list[dict[str, Any]]) -> dict[str, Any]:
    norm = normalize_option_book_positions(rows_or_positions)
    positions = norm['positions']
    totals = aggregate_option_book_greeks(positions)
    return {'ok': norm['ok'], 'positions': positions, 'rejected_positions': norm['rejected_positions'], 'totals': totals, 'by_underlying': aggregate_by_underlying(positions), 'by_expiry': aggregate_by_expiry(positions), 'by_moneyness_bucket': aggregate_by_moneyness_bucket(positions), 'source_snapshot': {'source':'user_supplied_local_positions','freshness':'user_supplied','confidence':'user_supplied'}, 'notice': OPTION_BOOK_NOTICE, 'research_only': True}
