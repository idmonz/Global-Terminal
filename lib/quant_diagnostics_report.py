from __future__ import annotations
from typing import Any
from .quant_diagnostics_returns import build_returns_diagnostics
from .quant_diagnostics_correlation import build_correlation_diagnostics
from .quant_diagnostics_volatility import build_volatility_diagnostics
from .quant_diagnostics_mean_reversion import build_mean_reversion_diagnostics, pair_residual_diagnostic
from .quant_diagnostics_time_alignment import align_series_by_timestamp
from .quant_diagnostics_hrp import build_hrp_diagnostic
from .quant_diagnostics_rmt import build_rmt_diagnostic
from .quant_diagnostics_kalman import kalman_lite_level_trend
from .quant_diagnostics_garch_lite import garch_lite_diagnostic
from .quant_diagnostics_cointegration import cointegration_diagnostic
from .research_report_sanitizer import sanitize_user_supplied_markdown_field
from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE


def build_quant_diagnostics_snapshot(prices_by_asset: dict[str, list[float] | list[dict[str, Any]]]) -> dict[str, Any]:
    aligned_payload = align_series_by_timestamp(prices_by_asset)  # type: ignore[arg-type]
    aligned_prices = aligned_payload.get('aligned', {}) if aligned_payload.get('ok') else {}
    returns_payload={asset: build_returns_diagnostics(prices)['simple_returns'] for asset, prices in aligned_prices.items()}
    first_asset=next(iter(aligned_prices), None)
    first_returns=returns_payload.get(first_asset, []) if first_asset else []
    first_prices=aligned_prices.get(first_asset, []) if first_asset else []
    snapshot={'ok': True, 'alignment': aligned_payload, 'returns_by_asset': returns_payload, 'correlation': build_correlation_diagnostics(returns_payload) if len(returns_payload)>1 else None, 'volatility': build_volatility_diagnostics(first_returns), 'mean_reversion': build_mean_reversion_diagnostics(first_prices) if first_asset else None, 'hrp': build_hrp_diagnostic(returns_payload) if returns_payload else None, 'rmt': build_rmt_diagnostic(returns_payload) if len(returns_payload)>1 else None, 'kalman_lite': kalman_lite_level_trend(first_prices) if first_prices else None, 'garch_lite': garch_lite_diagnostic(first_returns), 'source_snapshot': {'source':'supplied_local_series','freshness':'user_supplied','confidence':'user_supplied'}, 'notice': GOAL12B_RESEARCH_ONLY_NOTICE, 'research_only': True}
    if len(aligned_prices) >= 2:
        keys=list(aligned_prices.keys())[:2]
        snapshot['pair_residual'] = pair_residual_diagnostic(aligned_prices[keys[0]], aligned_prices[keys[1]])
        snapshot['cointegration'] = cointegration_diagnostic(aligned_prices[keys[0]], aligned_prices[keys[1]])
    return snapshot


def build_quant_diagnostics_report(prices_by_asset: dict[str, list[float] | list[dict[str, Any]]]) -> dict[str, Any]:
    snap=build_quant_diagnostics_snapshot(prices_by_asset)
    assets = ', '.join(sanitize_user_supplied_markdown_field(k) for k in prices_by_asset.keys())
    body=['# Local Quant Diagnostics Report','',GOAL12B_RESEARCH_ONLY_NOTICE,'', '- Supplied series only.', '- Descriptive diagnostics only; no predictive or alpha claim.', '']
    body.append(f"Assets: {assets}")
    body.append(f"Alignment: {sanitize_user_supplied_markdown_field(snap.get('alignment',{}).get('alignment','unknown'))}")
    return {'ok': True, 'report_type': 'quant_diagnostics_report', 'title': 'Local Quant Diagnostics Report', 'markdown_body': '\n'.join(body), 'snapshot': snap, 'research_only': True}
