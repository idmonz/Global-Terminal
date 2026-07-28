from __future__ import annotations

import pandas as pd

import lib.equity_scenarios as equity
from lib.compliance import contains_forbidden_language
from lib.scenario_engine import route_scenario_request


def _mock_frame(asset_type="equity", asset="SPY"):
    return pd.DataFrame(
        [
            {
                "asset_type": asset_type,
                "asset": asset,
                "horizon": "1w",
                "scenario": "Constructive continuation",
                "evidence_weight": 50,
                "evidence_summary": "Neutral evidence.",
                "triggers": "Trigger.",
                "invalidation_level": "Invalidation.",
                "watch_points": "Watch.",
                "catalysts": "Catalyst.",
                "data_gaps": "None.",
                "confidence_caveat": "Evidence weight is not prediction certainty.",
                "source_status": "mock",
            }
        ]
    )


def test_scenario_router_equity_crypto_energy_portfolio(monkeypatch):
    monkeypatch.setattr(equity, "compute_equity_scenario_matrix", lambda asset, horizon="1w": (_mock_frame("equity", asset), equity.ok_result(source="mock", provider="mock")))
    for asset_type, asset in [("equity", "SPY"), ("crypto", "BTCUSDT"), ("energy", "CL=F"), ("portfolio", "SPY,TLT")]:
        frame, status = route_scenario_request(asset_type, asset)
        assert status.ok
        assert not frame.empty
        assert not contains_forbidden_language(" ".join(frame.astype(str).stack().tolist()))

