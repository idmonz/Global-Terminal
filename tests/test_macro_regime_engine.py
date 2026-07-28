from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib.macro_regime_engine import build_macro_regime_ai_context, build_macro_regime_cards


def test_macro_regime_handles_data_gaps():
    payload = {"results": {"cpi": UnifiedDataResult(ok=False, data=pd.DataFrame(), metadata={"source_confidence": 0})}, "source_confidence": 0}

    cards = build_macro_regime_cards(payload)
    context = build_macro_regime_ai_context(payload)

    assert cards[0]["value"] in {"data gap", "mixed evidence"}
    assert "data_gaps" in context
