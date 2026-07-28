from lib.options_surface_arbitrage import (
    build_price_based_surface_arbitrage_report,
    check_call_put_parity_diagnostics,
    check_call_vertical_price_monotonicity,
    check_option_price_convexity_by_strike,
    check_put_vertical_price_monotonicity,
    check_calendar_price_monotonicity,
)


def surface(points):
    return {"points": points, "source_snapshot": {"source": "unit", "freshness": "fixture"}}


def test_goal12d_call_and_put_price_monotonic_violations_detected():
    s = surface([
        {"expiry": "2026-07-15", "option_type": "call", "strike": 90, "mid_price": 12},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 100, "mid_price": 13},
        {"expiry": "2026-07-15", "option_type": "put", "strike": 90, "mid_price": 11},
        {"expiry": "2026-07-15", "option_type": "put", "strike": 100, "mid_price": 10},
    ])
    assert check_call_vertical_price_monotonicity(s)["anomaly_count"] == 1
    assert check_put_vertical_price_monotonicity(s)["anomaly_count"] == 1


def test_goal12d_convexity_calendar_and_parity_are_price_based():
    s = surface([
        {"expiry": "2026-07-15", "option_type": "call", "strike": 90, "mid_price": 15, "underlying_price": 100, "time_to_expiry_years": 0.1, "risk_free_rate": 0.0, "dividend_yield": 0.0},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 100, "mid_price": 13, "underlying_price": 100, "time_to_expiry_years": 0.1, "risk_free_rate": 0.0, "dividend_yield": 0.0},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 110, "mid_price": 8, "underlying_price": 100, "time_to_expiry_years": 0.1, "risk_free_rate": 0.0, "dividend_yield": 0.0},
        {"expiry": "2026-07-15", "option_type": "put", "strike": 100, "mid_price": 4, "underlying_price": 100, "time_to_expiry_years": 0.1, "risk_free_rate": 0.0, "dividend_yield": 0.0},
        {"expiry": "2026-09-15", "option_type": "call", "strike": 100, "mid_price": 2, "underlying_price": 100, "time_to_expiry_years": 0.25, "risk_free_rate": 0.0, "dividend_yield": 0.0},
    ])
    assert check_option_price_convexity_by_strike(s)["anomaly_count"] >= 1
    assert check_calendar_price_monotonicity(s)["anomaly_count"] >= 1
    parity = check_call_put_parity_diagnostics(s)
    assert parity["paired_count"] >= 1
    assert parity["residuals"]
    assert "parity_residual" in parity["residuals"][0]


def test_goal12d_iv_only_surface_returns_price_check_unavailable_caveat():
    s = surface([
        {"expiry": "2026-07-15", "option_type": "call", "strike": 100, "mid_iv": 0.2},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 110, "mid_iv": 0.3},
    ])
    report = build_price_based_surface_arbitrage_report(s)
    assert "price_check_unavailable" in report["caveats"]
    assert report["price_check_available"] is False
