from __future__ import annotations

import importlib
import json
from pathlib import Path

import pandas as pd

from lib.compliance import contains_forbidden_language
from lib.crypto_scenarios import crypto_scenario_matrix, estimate_liquidation_pressure_map


ROOT = Path(__file__).resolve().parents[1]
EXPECTATIONS = json.loads((ROOT / "docs" / "CANONICAL_EXPECTATIONS.json").read_text(encoding="utf-8"))


def _module_name(path: str) -> str:
    return path[:-3].replace("/", ".")


def test_required_files_exist_and_are_non_placeholder():
    forbidden = EXPECTATIONS["no_placeholder_patterns"]
    for rel_path in EXPECTATIONS["required_files"]:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = path.read_text(encoding="utf-8")
        assert text.strip(), rel_path
        for pattern in forbidden:
            assert pattern not in text, f"{rel_path} contains {pattern}"


def test_minimum_line_count_guards_for_critical_modules():
    for rel_path, minimum in EXPECTATIONS["minimum_line_counts"].items():
        path = ROOT / rel_path
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) >= minimum, f"{rel_path} has {len(lines)} lines, expected at least {minimum}"


def test_goal1_required_functions_and_constants():
    for rel_path, names in EXPECTATIONS["required_functions"].items():
        if not rel_path.startswith(("lib/market_data", "lib/heatmaps")):
            continue
        module = importlib.import_module(_module_name(rel_path))
        for name in names:
            assert callable(getattr(module, name, None)), f"{rel_path}:{name}"

    global_markets = importlib.import_module("lib.global_markets")
    for name in EXPECTATIONS["required_constants"]["lib/global_markets.py"]:
        value = getattr(global_markets, name, None)
        assert isinstance(value, list)
        assert value, name


def test_phase4_crypto_required_functions():
    for rel_path, names in EXPECTATIONS["required_functions"].items():
        if not rel_path.startswith(("lib/crypto_derivatives", "lib/crypto_scenarios")):
            continue
        module = importlib.import_module(_module_name(rel_path))
        for name in names:
            assert callable(getattr(module, name, None)), f"{rel_path}:{name}"


def test_static_universe_row_counts():
    for rel_path, minimum in EXPECTATIONS["minimum_static_rows"].items():
        frame = pd.read_csv(ROOT / rel_path)
        assert len(frame) >= minimum, f"{rel_path} has {len(frame)} rows, expected at least {minimum}"


def test_phase4_liquidation_pressure_map_required_columns():
    klines = pd.DataFrame(
        {
            "high": [101 + idx for idx in range(80)],
            "low": [99 + idx for idx in range(80)],
            "close": [100 + idx for idx in range(80)],
            "volume": [1000 + idx for idx in range(80)],
        }
    )
    oi_history = pd.DataFrame({"sum_open_interest": [100, 110, 120, 130]})
    frame, status = estimate_liquidation_pressure_map(
        klines=klines,
        oi_history=oi_history,
        snapshot={"funding_rate": 0.0001},
    )
    required = {"level", "side", "leverage_band", "pressure_score", "distance_pct", "basis", "confidence", "caveat"}
    assert status.is_estimated
    assert required.issubset(frame.columns)
    assert frame["caveat"].str.contains("Estimated", case=False).all()


def test_crypto_intelligence_page_contains_key_tab_labels():
    text = (ROOT / "pages" / "8_Crypto_Intelligence.py").read_text(encoding="utf-8")
    for label in [
        "Futures & Perps",
        "Open Interest",
        "Funding & Basis",
        "Taker Flow",
        "Long/Short Bias",
        "Liquidations",
        "On-chain & Stablecoins",
        "Scenario Monitor",
        "Data Status",
    ]:
        assert label in text


def test_global_heatmaps_page_contains_metric_and_size_controls():
    text = (ROOT / "pages" / "7_Global_Heatmaps.py").read_text(encoding="utf-8")
    for label in ["Color metric", "Size mode", "US S&P 500", "US Sectors", "Cross-Asset"]:
        assert label in text


def test_no_forbidden_recommendation_language_in_scenario_outputs():
    rows = crypto_scenario_matrix(symbol="BTCUSDT", snapshot={"data_gaps": "none", "funding_rate": 0.0001})
    combined = rows.to_string(index=False) if hasattr(rows, "to_string") else str(rows)
    assert not contains_forbidden_language(combined)
