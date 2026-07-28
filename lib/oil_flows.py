from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .data_status import ok_result


def _last_change(series) -> float | None:
    values = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    if len(values) < 2:
        return None
    return float(values.iloc[-1] - values.iloc[-2])


def compute_inventory_pressure(crude_stocks) -> dict[str, Any]:
    change = _last_change(crude_stocks)
    if change is None:
        return {"score": 50, "label": "Data gap", "evidence": "Inventory series unavailable."}
    label = "Inventory draw pressure" if change < 0 else "Inventory build pressure" if change > 0 else "Neutral / mixed evidence"
    score = 60 if change < 0 else 40 if change > 0 else 50
    return {"score": score, "label": label, "latest_change": change, "evidence": f"Latest inventory change: {change:.2f}"}


def compute_production_pressure(production) -> dict[str, Any]:
    change = _last_change(production)
    if change is None:
        return {"score": 50, "label": "Data gap", "evidence": "Production series unavailable."}
    label = "Supply easing pressure" if change > 0 else "Supply tightening pressure" if change < 0 else "Neutral / mixed evidence"
    score = 45 if change > 0 else 55 if change < 0 else 50
    return {"score": score, "label": label, "latest_change": change, "evidence": f"Latest production change: {change:.2f}"}


def compute_import_export_balance(imports, exports) -> dict[str, Any]:
    import_change = _last_change(imports)
    export_change = _last_change(exports)
    if import_change is None or export_change is None:
        return {"score": 50, "label": "Data gap", "evidence": "Import/export series unavailable."}
    balance = import_change - export_change
    label = "Net import pressure rising" if balance > 0 else "Net export pressure rising" if balance < 0 else "Neutral / mixed evidence"
    return {"score": 50 - max(-15, min(15, balance)), "label": label, "latest_balance_change": balance}


def compute_refinery_pressure(refinery_utilization) -> dict[str, Any]:
    values = pd.to_numeric(pd.Series(refinery_utilization), errors="coerce").dropna()
    if values.empty:
        return {"score": 50, "label": "Data gap", "evidence": "Refinery utilization unavailable."}
    latest = float(values.iloc[-1])
    label = "Refinery/product tightness" if latest >= 90 else "Refinery slack" if latest <= 80 else "Neutral / mixed evidence"
    score = 60 if latest >= 90 else 40 if latest <= 80 else 50
    return {"score": score, "label": label, "latest_utilization": latest}


def compute_product_tightness(gasoline_stocks, distillate_stocks) -> dict[str, Any]:
    gas = _last_change(gasoline_stocks)
    dist = _last_change(distillate_stocks)
    if gas is None or dist is None:
        return {"score": 50, "label": "Data gap", "evidence": "Product stock series unavailable."}
    combined = gas + dist
    label = "Product tightness" if combined < 0 else "Product stock build" if combined > 0 else "Neutral / mixed evidence"
    return {"score": 60 if combined < 0 else 40 if combined > 0 else 50, "label": label, "combined_change": combined}


def compute_oil_fundamental_score_neutral(components: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [component.get("score") for component in components if isinstance(component.get("score"), (int, float))]
    if not scores:
        return {"score": 50, "label": "Data gap"}
    score = float(np.mean(scores))
    if score >= 60:
        label = "Tightening fundamental backdrop"
    elif score <= 40:
        label = "Softening fundamental backdrop"
    else:
        label = "Neutral / mixed evidence"
    return {"score": score, "label": label}


def build_chokepoint_registry() -> pd.DataFrame:
    rows = [
        ("Strait of Hormuz", "Middle East", "crude, LNG", 80, ["Iran", "Oman", "UAE"], ["Hormuz", "Iran", "tanker", "sanctions"], "Key Gulf export route"),
        ("Suez Canal", "Egypt", "crude, products, container", 55, ["Egypt"], ["Suez", "canal", "Red Sea"], "Europe-Asia shortcut"),
        ("Bab el-Mandeb", "Red Sea", "crude, products, container", 70, ["Yemen", "Djibouti", "Eritrea"], ["Bab el-Mandeb", "Red Sea", "Houthi"], "Red Sea access route"),
        ("Strait of Malacca", "Southeast Asia", "crude, LNG, container", 50, ["Malaysia", "Indonesia", "Singapore"], ["Malacca", "Singapore", "piracy"], "Asia energy artery"),
        ("Panama Canal", "Panama", "products, LNG, container", 45, ["Panama"], ["Panama Canal", "drought", "transit"], "Americas transit route"),
        ("Bosphorus", "Turkey", "crude, products", 45, ["Turkey"], ["Bosphorus", "Black Sea", "Turkey"], "Black Sea-Mediterranean route"),
        ("Dardanelles", "Turkey", "crude, products", 40, ["Turkey"], ["Dardanelles", "Black Sea", "Turkey"], "Black Sea-Mediterranean route"),
        ("Strait of Gibraltar", "Mediterranean", "crude, products, container", 35, ["Spain", "Morocco"], ["Gibraltar", "Mediterranean"], "Atlantic-Mediterranean route"),
    ]
    return pd.DataFrame(
        rows,
        columns=["name", "region", "relevant_cargo", "baseline_risk", "key_countries", "risk_keywords", "route_notes"],
    ).assign(source_status="static open-source chokepoint registry")


def compute_chokepoint_risk_proxy(news_items: pd.DataFrame | None = None, selected: str | None = None) -> tuple[pd.DataFrame, object]:
    registry = build_chokepoint_registry()
    if selected:
        registry = registry[registry["name"].eq(selected)]
    rows = []
    for _, row in registry.iterrows():
        news_count = _count_news_hits(news_items, row["risk_keywords"])
        score = min(100, float(row["baseline_risk"]) + news_count * 5)
        rows.append(
            {
                "name": row["name"],
                "region": row["region"],
                "baseline_risk": row["baseline_risk"],
                "recent_news_count": news_count,
                "shipping_disruption_score": score,
                "war_risk_tier": _risk_tier(score),
                "route_exposure": row["relevant_cargo"],
                "source_status": "estimated open-source news/chokepoint proxy",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, ok_result(frame, source="static registry + public news proxy", provider="oil_flows", is_estimated=True, warning="Live AIS unavailable in free mode. Displaying open-source chokepoint/news risk proxy.")


def _count_news_hits(news_items: pd.DataFrame | None, keywords: list[str]) -> int:
    if news_items is None or getattr(news_items, "empty", True):
        return 0
    text = " ".join(news_items.astype(str).stack().tolist()).lower()
    return sum(1 for keyword in keywords if keyword.lower() in text)


def _risk_tier(score: float) -> str:
    if score >= 75:
        return "Elevated"
    if score >= 50:
        return "Moderate"
    return "Watch"


def compute_shipping_disruption_proxy(news_items: pd.DataFrame | None = None) -> tuple[dict[str, Any], object]:
    table, status = compute_chokepoint_risk_proxy(news_items)
    score = float(table["shipping_disruption_score"].mean()) if not table.empty else 50.0
    payload = {
        "shipping_disruption_score": score,
        "source_status": "estimated open-source proxy",
        "warning": "Live AIS unavailable in free mode. Displaying open-source chokepoint/news risk proxy.",
        "data_gaps": ["Live vessel flows unavailable without an optional AIS or route-intelligence provider."],
    }
    return payload, ok_result(payload, source=status.source, provider="oil_flows", is_estimated=True, warning=payload["warning"])


def compute_oil_scenario_matrix(evidence: dict | None = None) -> tuple[pd.DataFrame, object]:
    evidence = evidence or {}
    gaps = evidence.get("data_gaps", "EIA data may be unavailable without EIA_API_KEY; live AIS unavailable in free mode.")
    rows = [
        {
            "asset_type": "energy",
            "asset": evidence.get("asset", "CL=F"),
            "horizon": evidence.get("horizon", "1m"),
            "scenario": "Tightening / geopolitical premium expansion",
            "evidence_weight": evidence.get("tightening_weight", 55),
            "supply_evidence": evidence.get("supply_evidence", "Production, exports, and chokepoint proxy are reviewed."),
            "demand_evidence": evidence.get("demand_evidence", "Product supplied and macro demand indicators are mixed."),
            "inventory_evidence": evidence.get("inventory_evidence", "Inventory draw/build pressure is evaluated from EIA when available."),
            "refinery_product_evidence": evidence.get("refinery_product_evidence", "Refinery utilization and product stocks are monitored."),
            "geopolitical_evidence": evidence.get("geopolitical_evidence", "Chokepoint and sanctions headlines can affect risk premium."),
            "technical_evidence": evidence.get("technical_evidence", "Trend and realized volatility are neutral inputs."),
            "watch_points": "EIA weekly stocks, OPEC policy, chokepoint news, WTI/Brent spread.",
            "invalidation_level": "Risk premium fades and inventories build for multiple reports.",
            "data_gaps": gaps,
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
        {
            "asset_type": "energy",
            "asset": evidence.get("asset", "CL=F"),
            "horizon": evidence.get("horizon", "1m"),
            "scenario": "Balanced range",
            "evidence_weight": 50,
            "supply_evidence": "Supply and demand evidence remains mixed.",
            "demand_evidence": "Demand indicators do not show broad pressure.",
            "inventory_evidence": "Inventories fluctuate without sustained draw/build pattern.",
            "refinery_product_evidence": "Product tightness is balanced.",
            "geopolitical_evidence": "Headline risk exists but does not dominate the tape.",
            "technical_evidence": "Range behavior and muted volatility.",
            "watch_points": "Curve shape, product cracks, DXY, rates.",
            "invalidation_level": "Break from range with confirmed fundamental catalyst.",
            "data_gaps": gaps,
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
        {
            "asset_type": "energy",
            "asset": evidence.get("asset", "CL=F"),
            "horizon": evidence.get("horizon", "1m"),
            "scenario": "Demand weakness / inventory build",
            "evidence_weight": evidence.get("weakness_weight", 45),
            "supply_evidence": "Supply availability remains adequate.",
            "demand_evidence": "Macro or product supplied deterioration can pressure demand evidence.",
            "inventory_evidence": "Inventory builds raise softening pressure.",
            "refinery_product_evidence": "Refinery slack or product builds can confirm weakness.",
            "geopolitical_evidence": "Geopolitical premium is muted or fading.",
            "technical_evidence": "Trend deterioration and rising drawdown.",
            "watch_points": "Demand data, China/US macro releases, refinery utilization.",
            "invalidation_level": "Sustained draws or supply disruption.",
            "data_gaps": gaps,
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
        {
            "asset_type": "energy",
            "asset": evidence.get("asset", "CL=F"),
            "horizon": evidence.get("horizon", "1m"),
            "scenario": "Volatility shock / headline risk",
            "evidence_weight": evidence.get("volatility_weight", 50),
            "supply_evidence": "Supply chain chokepoints and policy shocks are monitored.",
            "demand_evidence": "Demand impact can be secondary during headline windows.",
            "inventory_evidence": "Inventory confirmation may lag price reaction.",
            "refinery_product_evidence": "Refinery outages can intensify product volatility.",
            "geopolitical_evidence": "News concentration around chokepoints raises shock risk.",
            "technical_evidence": "ATR and gap risk are key diagnostics.",
            "watch_points": "Hormuz, Red Sea, sanctions, pipeline/refinery outage reports.",
            "invalidation_level": "Headline risk de-escalates and volatility compresses.",
            "data_gaps": gaps,
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
    ]
    frame = pd.DataFrame(rows)
    return frame, ok_result(frame, source="oil scenario engine", provider="oil_flows", is_estimated=True, coverage=f"{len(frame)} scenarios")


def build_unified_chokepoint_risk_payload() -> dict[str, Any]:
    from .shipping_chokepoint_engine import (
        build_chokepoint_market_impact_payload,
        build_chokepoint_risk_cards,
        build_chokepoint_war_room_layer,
        compute_shipping_disruption_proxy,
    )

    return {
        "risk_cards": build_chokepoint_risk_cards(),
        "market_impact": build_chokepoint_market_impact_payload(),
        "war_room_layer": build_chokepoint_war_room_layer(),
        "disruption_proxy": compute_shipping_disruption_proxy(),
        "caveat": "Unified chokepoint payload is static/proxy unless an explicit shipping provider is configured.",
    }
