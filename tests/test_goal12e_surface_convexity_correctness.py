from lib.options_surface_price_checks import check_option_price_convexity_by_strike


def surface(points):
    return {"points": points, "source_snapshot": {"source": "fixture"}}


def test_goal12e_normal_convex_call_curve_is_not_flagged():
    s = surface([
        {"expiry": "2026-07-15", "option_type": "call", "strike": 90, "mid_price": 15},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 100, "mid_price": 7},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 110, "mid_price": 2},
    ])
    assert check_option_price_convexity_by_strike(s)["anomaly_count"] == 0


def test_goal12e_middle_call_price_above_chord_is_flagged():
    s = surface([
        {"expiry": "2026-07-15", "option_type": "call", "strike": 90, "mid_price": 15},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 100, "mid_price": 13},
        {"expiry": "2026-07-15", "option_type": "call", "strike": 110, "mid_price": 8},
    ])
    out = check_option_price_convexity_by_strike(s)
    assert out["anomaly_count"] == 1
    row = out["anomalies"][0]
    assert row["price"] == 13
    assert row["linear_bound"] == 11.5
    assert row["strike"] == 100
    assert row["expiry"] == "2026-07-15"
    assert row["option_type"] == "call"
    assert row["check"] == "option_price_convexity_by_strike"
    assert row["research_only"] is True


def test_goal12e_same_convexity_logic_for_put_rows():
    s = surface([
        {"expiry": "2026-07-15", "option_type": "put", "strike": 90, "mid_price": 2},
        {"expiry": "2026-07-15", "option_type": "put", "strike": 100, "mid_price": 13},
        {"expiry": "2026-07-15", "option_type": "put", "strike": 110, "mid_price": 15},
    ])
    assert check_option_price_convexity_by_strike(s)["anomaly_count"] == 1


def test_goal12e_sparse_surface_returns_unavailable_caveat():
    out = check_option_price_convexity_by_strike(surface([
        {"expiry": "2026-07-15", "option_type": "call", "strike": 100, "mid_iv": 0.2},
    ]))
    assert out["caveat"] == "price_check_unavailable"
    assert out["anomaly_count"] == 0
