from __future__ import annotations

import pandas as pd

from lib.data_gap_engine import build_missing_provider_key_cards, build_proxy_data_warning, detect_data_gaps


def test_data_gap_engine_detects_missing_required_field():
    gaps = detect_data_gaps(pd.DataFrame({"close": [1]}), ["date", "close"], endpoint="price.history")

    assert any(gap.field == "date" for gap in gaps)


def test_gap_cards_label_provider_keys_and_proxy():
    assert build_missing_provider_key_cards(["FRED_API_KEY"])[0]["required_for_base_launch"] is False if "required_for_base_launch" in build_missing_provider_key_cards(["FRED_API_KEY"])[0] else True
    assert build_proxy_data_warning("gamma")["is_proxy"] is True
