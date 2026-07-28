from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
from .options_report_generator import generate_options_pricing_report, generate_options_scenario_report, generate_options_iv_report
from .quant_model_report_generator import attach_model_snapshot_to_report
from .report_generators import (
    generate_daily_global_brief,
    generate_watchlist_brief,
    generate_war_room_brief,
    generate_energy_geopolitics_brief,
    generate_crypto_derivatives_watch,
    generate_portfolio_risk_report,
    generate_provider_health_report,
    generate_data_quality_report,
    generate_strategy_review_report,
    generate_alert_summary_report,
)

REPORT_GENERATORS: dict[str, Callable[..., dict[str, Any]]] = {
    "daily": generate_daily_global_brief,
    "watchlist": generate_watchlist_brief,
    "war_room": generate_war_room_brief,
    "energy": generate_energy_geopolitics_brief,
    "crypto": generate_crypto_derivatives_watch,
    "portfolio": generate_portfolio_risk_report,
    "provider": generate_provider_health_report,
    "data_quality": generate_data_quality_report,
    "strategy": generate_strategy_review_report,
    "alerts": generate_alert_summary_report,
    "options": generate_options_pricing_report,
    "options_pricing_report": generate_options_pricing_report,
    "options_scenario_report": generate_options_scenario_report,
    "options_iv_report": generate_options_iv_report,
    "model_snapshot": attach_model_snapshot_to_report,
}


def run_report_generator(name: str, db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]:
    key = str(name or "daily").lower().replace(" ", "_")
    fn = REPORT_GENERATORS.get(key, generate_daily_global_brief)
    return fn(db_path=db_path, **extra)
