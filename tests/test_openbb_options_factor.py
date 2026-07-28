from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib import openbb_options_factor


def test_options_factor_labels_gamma_proxy(monkeypatch):
    data = pd.DataFrame({"symbol": ["SPY", "SPY"], "call_put": ["call", "put"], "open_interest": [100, 50], "volume": [20, 10], "iv": [0.2, 0.25]})
    monkeypatch.setattr(openbb_options_factor, "request_options_chain", lambda symbol, **kwargs: UnifiedDataResult(ok=True, data=data, provider="fake", source="fake", endpoint="options.chain", freshness="fresh", metadata={"source_confidence": 60}))

    scores = openbb_options_factor.build_options_factor_scores("SPY")

    assert scores["put_call_oi_ratio"] == 0.5
    assert scores["gamma_proxy"]["is_proxy"] is True
