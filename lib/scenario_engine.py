from __future__ import annotations

from typing import Any

import pandas as pd

from .compliance import contains_forbidden_language
from .data_status import combine_statuses, error_result, ok_result


SCENARIO_COLUMNS = [
    "asset_type",
    "asset",
    "horizon",
    "scenario",
    "evidence_weight",
    "evidence_summary",
    "triggers",
    "invalidation_level",
    "watch_points",
    "catalysts",
    "data_gaps",
    "confidence_caveat",
    "source_status",
]


def normalize_scenario_matrix(matrix: pd.DataFrame | list[dict] | dict, *, asset_type: str, asset: str, horizon: str) -> pd.DataFrame:
    if isinstance(matrix, pd.DataFrame):
        frame = matrix.copy()
    elif isinstance(matrix, list):
        frame = pd.DataFrame(matrix)
    else:
        frame = pd.DataFrame([matrix])
    rename = {
        "technical_triggers": "triggers",
        "supply_evidence": "evidence_summary",
    }
    for old, new in rename.items():
        if old in frame.columns and new not in frame.columns:
            frame[new] = frame[old]
    for column, default in {
        "asset_type": asset_type,
        "asset": asset,
        "horizon": horizon,
        "scenario": "Scenario",
        "evidence_weight": 50,
        "evidence_summary": "Neutral scenario evidence.",
        "triggers": "Watch-point trigger unavailable.",
        "invalidation_level": "Invalidation level unavailable.",
        "watch_points": "Data status and market diagnostics.",
        "catalysts": "Catalyst calendar unavailable.",
        "data_gaps": "No additional data gaps noted.",
        "confidence_caveat": "Evidence weight is not prediction certainty.",
        "source_status": "scenario engine",
    }.items():
        if column not in frame.columns:
            frame[column] = default
    return frame[SCENARIO_COLUMNS]


def assert_no_recommendation_language(frame: pd.DataFrame) -> None:
    text = " ".join(frame.astype(str).stack().tolist())
    if contains_forbidden_language(text):
        raise ValueError("Scenario matrix contains restricted language.")


def validate_scenario_output(frame: pd.DataFrame) -> tuple[bool, list[str]]:
    missing = [column for column in SCENARIO_COLUMNS if column not in frame.columns]
    try:
        assert_no_recommendation_language(frame)
    except ValueError as exc:
        missing.append(str(exc))
    return not missing, missing


def merge_scenario_evidence(*frames: pd.DataFrame) -> pd.DataFrame:
    usable = [frame for frame in frames if frame is not None and not frame.empty]
    if not usable:
        return pd.DataFrame(columns=SCENARIO_COLUMNS)
    return pd.concat(usable, ignore_index=True)


def route_scenario_request(asset_type: str, asset: str, horizon: str = "1w", **kwargs) -> tuple[pd.DataFrame, object]:
    normalized_type = asset_type.lower()
    try:
        if normalized_type in {"equity", "index", "etf"}:
            from .equity_scenarios import compute_equity_scenario_matrix

            raw, status = compute_equity_scenario_matrix(asset, horizon=horizon)
        elif normalized_type == "crypto":
            from .crypto_scenarios import compute_crypto_scenario_matrix

            raw, status = compute_crypto_scenario_matrix(asset, horizon=horizon)
        elif normalized_type in {"energy", "oil"}:
            from .oil_flows import compute_oil_scenario_matrix

            raw, status = compute_oil_scenario_matrix({"asset": asset, "horizon": horizon})
        elif normalized_type in {"portfolio", "basket"}:
            from .stress_tests import build_stress_test_matrix

            tickers = kwargs.get("tickers") or [ticker.strip() for ticker in asset.split(",") if ticker.strip()]
            raw, status = build_stress_test_matrix(tickers=tickers)
            raw["evidence_summary"] = raw["assumed_shocks"].astype(str)
            raw["triggers"] = "Stress condition selected by user."
            raw["watch_points"] = "Largest contributors and data gaps."
            raw["catalysts"] = "User-defined or standard stress condition."
            raw["invalidation_level"] = "Stress assumption no longer applies."
            raw["source_status"] = "stress test engine"
        else:
            return pd.DataFrame(), error_result(source="scenario router", provider="scenario_engine", error=f"Unsupported asset type: {asset_type}")
        frame = normalize_scenario_matrix(raw, asset_type=normalized_type, asset=asset, horizon=horizon)
        valid, issues = validate_scenario_output(frame)
        if not valid:
            return frame, error_result(source="scenario engine", provider="scenario_engine", error="; ".join(issues))
        return frame, ok_result(frame, source=status.source if status else "scenario engine", provider="scenario_engine", warning=getattr(status, "warning", None), is_estimated=True, coverage=f"{len(frame)} scenarios")
    except Exception as exc:
        return pd.DataFrame(), error_result(source="scenario router", provider="scenario_engine", error=str(exc))


def build_cross_asset_scenario(asset_type: str, asset: str, horizon: str = "1w", **kwargs) -> tuple[pd.DataFrame, object]:
    return route_scenario_request(asset_type, asset, horizon=horizon, **kwargs)


def build_scenario_data_status(statuses: list[object]) -> pd.DataFrame:
    return pd.DataFrame([status.to_dict() for status in statuses if status is not None])


def integrate_news_market_impact(news_or_events, *, price_data: dict[str, object] | None = None, fetch_market_data: bool = False) -> tuple[dict[str, object], object]:
    from .market_impact_engine import build_market_impact_context

    context = build_market_impact_context(news_or_events, price_data=price_data, fetch_market_data=fetch_market_data)
    return context, context.get("status")


def add_news_impact_to_scenario_evidence(scenario_matrix: pd.DataFrame, news_impact_evidence) -> pd.DataFrame:
    from .market_impact_engine import build_event_to_scenario_evidence

    frame = scenario_matrix.copy() if isinstance(scenario_matrix, pd.DataFrame) else pd.DataFrame(scenario_matrix)
    evidence = news_impact_evidence if isinstance(news_impact_evidence, pd.DataFrame) else build_event_to_scenario_evidence(news_impact_evidence)
    if evidence is None or evidence.empty:
        frame["news_impact_evidence"] = 0
        frame["related_assets"] = ""
        frame["catalyst_clusters"] = ""
        frame["confidence_caveat"] = frame.get("confidence_caveat", "Evidence weight is not prediction certainty.")
        return frame
    avg_evidence = round(float(evidence["news_impact_evidence"].fillna(0).mean()), 1) if "news_impact_evidence" in evidence.columns else 0
    related_assets = sorted({asset for values in evidence.get("related_assets", []) for asset in (values if isinstance(values, list) else [values]) if asset})
    catalyst_clusters = sorted({cluster for values in evidence.get("catalyst_clusters", []) for cluster in (values if isinstance(values, list) else [values]) if cluster})
    data_gaps = "; ".join(sorted({str(value) for value in evidence.get("data_gaps", []) if value and str(value) != "nan"}))
    frame["news_impact_evidence"] = avg_evidence
    frame["related_assets"] = ", ".join(related_assets)
    frame["catalyst_clusters"] = ", ".join(catalyst_clusters)
    frame["data_gaps"] = frame["data_gaps"].astype(str) + (f"; {data_gaps}" if data_gaps else "")
    frame["confidence_caveat"] = frame["confidence_caveat"].astype(str) + "; news impact evidence is proxy/correlation context."
    return frame


def build_news_aware_scenario_matrix(asset_type: str, asset: str, horizon: str = "1w", news_or_events=None, **kwargs) -> tuple[pd.DataFrame, object]:
    base, base_status = route_scenario_request(asset_type, asset, horizon=horizon, **kwargs)
    context, impact_status = integrate_news_market_impact(news_or_events or [], fetch_market_data=False)
    evidence = context.get("impact_table")
    enriched = add_news_impact_to_scenario_evidence(base, news_or_events or evidence)
    valid, issues = validate_scenario_output(enriched[SCENARIO_COLUMNS] if all(column in enriched.columns for column in SCENARIO_COLUMNS) else enriched)
    if not valid:
        return enriched, error_result(source="news-aware scenario matrix", provider="scenario_engine", error="; ".join(issues))
    status = combine_statuses([status for status in [base_status, impact_status] if status is not None], provider="scenario_engine", source="news-aware scenario matrix")
    return enriched, status


def build_macro_energy_scenario_evidence(source_mode: str = "auto") -> dict[str, Any]:
    from .energy_market_impact import build_energy_scenario_evidence
    from .macro_regime_engine import build_macro_regime_ai_context
    from .openbb_energy_backend import build_energy_dashboard_payload
    from .openbb_macro_backend import build_macro_rates_dashboard_payload
    from .shipping_chokepoint_engine import build_chokepoint_market_impact_payload

    macro_payload = build_macro_rates_dashboard_payload(source_mode=source_mode)
    energy_payload = build_energy_dashboard_payload(source_mode=source_mode)
    return {
        "macro_regime": build_macro_regime_ai_context(macro_payload),
        "energy_risk": build_energy_scenario_evidence(energy_payload, macro_payload),
        "chokepoint_risk": build_chokepoint_market_impact_payload(),
        "source_mode": source_mode,
        "caveat": "Scenario evidence is proxy/contextual research data, not prediction certainty.",
    }
