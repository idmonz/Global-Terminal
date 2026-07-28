from lib.options_greeks import black_scholes_greeks, build_greek_units_table, scale_greeks_by_contract


def test_contract_scaled_greeks_units():
    greeks = black_scholes_greeks("call", 100, 100, 30/365, 0.01, 0.2)
    scaled = scale_greeks_by_contract(greeks, contract_multiplier=100, quantity=2, underlying_price=100)
    assert scaled["contract_delta"] == greeks["delta"] * 200
    assert scaled["contract_vega_1pct"] == greeks["vega"] * 0.01 * 200
    assert scaled["notional_delta_approx"] is not None
    assert any(row["field"] == "rho_1bp" for row in build_greek_units_table())
