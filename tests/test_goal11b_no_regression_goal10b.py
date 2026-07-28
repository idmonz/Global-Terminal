import importlib
from pathlib import Path


def test_goal10b_canonical_functions_still_exist():
    checks = {
        "lib.market_data": ["empty_frame", "fetch_history", "fetch_multi_history", "latest_close"],
        "lib.global_markets": ["SECTOR_ETFS", "G7_MARKETS", "CROSS_ASSET_TICKERS", "CRYPTO_MARKETS"],
        "lib.heatmaps": ["build_sp500_heatmap", "build_nasdaq100_heatmap", "build_korea_heatmap", "build_sector_heatmap", "build_g7_heatmap", "build_cross_asset_heatmap", "build_crypto_heatmap"],
        "lib.unified_data_layer": ["request_data", "get_unified_price_history", "get_unified_financials", "get_unified_screener", "get_unified_macro_dashboard_data", "get_unified_energy_dashboard_data", "get_unified_war_room_data"],
        "lib.terminal_command_router": ["parse_terminal_command", "route_terminal_command"],
        "lib.terminal_function_registry": ["build_terminal_function_registry"],
        "lib.provider_probe_runner": ["build_probe_registry", "run_provider_probe", "run_all_lightweight_probes", "build_provider_probe_summary"],
        "lib.war_room": ["build_global_event_map"],
        "lib.event_stream": ["build_event_stream"],
        "lib.layer_registry": ["build_layer_registry"],
        "lib.war_room_live_data_router": ["build_war_room_live_payload"],
        "lib.live_news_event_pipeline": ["build_news_event_stream"],
        "lib.energy_geopolitics_map": ["build_energy_geopolitics_map_payload"],
        "lib.relative_market_intelligence": ["build_rmi_table", "build_rmi_heatmap"],
        "lib.global_volatility_monitor": ["build_global_volatility_payload"],
    }
    for module_name, names in checks.items():
        module = importlib.import_module(module_name)
        for name in names:
            assert hasattr(module, name), f"{module_name}.{name} missing"


def test_static_universe_row_counts_still_safe():
    assert Path("static/index_constituents/sp500.csv").read_text(encoding="utf-8").count("\n") >= 60
    assert Path("static/index_constituents/nasdaq100.csv").read_text(encoding="utf-8").count("\n") >= 30
    assert Path("static/index_constituents/korea_watchlist.csv").read_text(encoding="utf-8").count("\n") >= 24
