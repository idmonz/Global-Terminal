from __future__ import annotations

REPORT_TYPES = {
    "Daily Global Brief", "Watchlist Brief", "War Room Brief", "Energy Geopolitics Brief",
    "Crypto Derivatives Watch", "Portfolio Risk Report", "Provider Health Report",
    "Data Quality Report", "Strategy Review Report", "Alert Summary Report",
    "options_pricing_report", "options_scenario_report", "options_iv_report", "options_payoff_report",
    "quant_model_snapshot_report",
    "options_chain_snapshot_report", "options_vol_surface_report", "options_book_risk_report", "quant_diagnostics_report",
}
REPORT_CAVEAT = "Reports are generated from available data sources and may include stale, proxy, estimated, historical-only, or missing-key data. Verify source status before relying on outputs."


def validate_report_type(report_type: str) -> str:
    if report_type in REPORT_TYPES:
        return report_type
    # Keep custom report topics possible while preserving the known catalog.
    return str(report_type or "Watchlist Brief")


def build_report_source_snapshot(source: str = "local", freshness: str = "unknown", confidence: str = "unknown", gaps: list[str] | None = None) -> dict:
    return {"source": source, "freshness": freshness, "confidence": confidence, "gaps": gaps or [], "labels": [freshness, confidence]}

