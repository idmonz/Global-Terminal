from lib.options_payoff import payoff_summary, single_option_payoff
from lib.options_strategy_templates import build_strategy_payoff, list_option_strategy_templates


def test_single_call_payoff_long_profile():
    assert single_option_payoff("call", 120, 100, premium=5, contract_multiplier=1) == 15
    assert single_option_payoff("call", 90, 100, premium=5, contract_multiplier=1) == -5


def test_payoff_summary_contains_breakeven():
    result = payoff_summary([{"option_type": "call", "strike": 100, "premium": 5, "contract_multiplier": 1}], [90, 100, 105, 110])
    assert 105 in result["breakeven_points"]
    assert result["research_only"] is True


def test_strategy_templates_build():
    names = {row["template"] for row in list_option_strategy_templates()}
    assert {"covered_call", "protective_put", "vertical_spread", "straddle", "strangle"}.issubset(names)
    built = build_strategy_payoff("straddle", {"strike": 100, "call_premium": 5, "put_premium": 4, "price_grid": [80, 100, 120], "contract_multiplier": 1})
    assert built["strategy_template"] == "straddle"
