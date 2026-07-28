from __future__ import annotations

ALERT_SCOPES = {
    "price", "return", "volatility", "crypto_derivatives", "provider", "source_freshness",
    "war_room", "energy", "weather", "earthquake", "portfolio", "strategy", "report",
    "watchlist_change",
}
ALERT_OPERATORS = {"above", "below", "crosses_above", "crosses_below", "equals", "not_equals", "contains", "status_is", "stale_for"}


def validate_alert_scope(scope: str) -> str:
    normalized = str(scope or "price").lower().strip()
    if normalized not in ALERT_SCOPES:
        raise ValueError(f"Unsupported alert scope: {scope}")
    return normalized


def validate_alert_operator(operator: str) -> str:
    normalized = str(operator or "above").lower().strip()
    if normalized not in ALERT_OPERATORS:
        raise ValueError(f"Unsupported alert operator: {operator}")
    return normalized


def build_alert_rule_template(scope: str = "price", metric: str = "close", operator: str = "above", threshold: str | float = "") -> dict[str, str]:
    return {"scope": validate_alert_scope(scope), "metric": str(metric), "operator": validate_alert_operator(operator), "threshold": str(threshold)}
