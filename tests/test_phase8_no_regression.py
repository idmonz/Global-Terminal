from __future__ import annotations

import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase4_goal1_goal3_modules_still_import():
    modules = [
        "lib.market_data",
        "lib.global_markets",
        "lib.heatmaps",
        "lib.crypto_derivatives",
        "lib.crypto_prices",
        "lib.crypto_onchain",
        "lib.crypto_scenarios",
        "lib.equity_breadth",
        "lib.equity_scenarios",
        "lib.energy_data",
        "lib.oil_flows",
        "lib.geopolitical_news",
        "lib.worldmonitor_adapter",
        "lib.risk",
        "lib.stress_tests",
        "lib.scenario_engine",
    ]
    for module in modules:
        importlib.import_module(module)


def test_phase8_pages_and_modules_exist():
    for rel_path in [
        "lib/ai_providers.py",
        "lib/ai_analysis.py",
        "lib/ai_prompts.py",
        "lib/ai_safety.py",
        "lib/map_viz.py",
        "lib/overview.py",
        "lib/fundamentals.py",
        "lib/screeners.py",
        "lib/options_flow.py",
        "lib/bond_data.py",
        "pages/13_Screener.py",
    ]:
        assert (ROOT / rel_path).exists(), rel_path


def test_no_broad_cleanup_patterns_in_safe_cleanup_script():
    text = (ROOT / "scripts" / "safe_cleanup_generated_artifacts.py").read_text(encoding="utf-8")
    forbidden = ["Remove-Item", "rm -rf", "del /s", "rmdir /s"]
    assert not any(pattern in text for pattern in forbidden)
