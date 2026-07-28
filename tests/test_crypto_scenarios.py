import pandas as pd

from lib.compliance import contains_forbidden_language
from lib.crypto_scenarios import SCENARIOS, crypto_scenario_matrix, estimate_liquidation_pressure_map


def _sample_klines():
    close = [100 + i for i in range(80)]
    return pd.DataFrame(
        {
            "high": [value + 2 for value in close],
            "low": [value - 2 for value in close],
            "close": close,
            "volume": [1000 + i * 3 for i in range(80)],
        }
    )


def test_estimated_liquidation_pressure_map_columns():
    klines = _sample_klines()
    oi = pd.DataFrame({"sum_open_interest": [100, 110, 125]})
    frame, status = estimate_liquidation_pressure_map(klines=klines, oi_history=oi, snapshot={"funding_rate": 0.0001})
    required = {"level", "side", "leverage_band", "pressure_score", "distance_pct", "basis", "confidence", "caveat"}
    assert status.is_estimated
    assert required.issubset(frame.columns)
    assert frame["pressure_score"].between(0, 100).all()
    assert frame["caveat"].str.contains("Estimated", case=False).all()
    assert not frame["caveat"].str.contains("official exchange liquidation data", case=False).eq(False).any()


def test_scenario_matrix_is_complete_and_neutral():
    rows = crypto_scenario_matrix(symbol="BTCUSDT", klines=_sample_klines(), snapshot={"data_gaps": "none", "funding_rate": 0.0001})
    assert set(rows["scenario"]) == set(SCENARIOS)
    assert "evidence_weight" in rows.columns
    assert "data_gaps" in rows.columns
    combined = " ".join(str(value) for value in rows.astype(str).to_numpy().flatten())
    assert not contains_forbidden_language(combined)
