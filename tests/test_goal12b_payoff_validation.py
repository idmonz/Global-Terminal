import pytest
from lib.options_advanced_payoffs import custom_multi_leg_payoff, validate_payoff_grid, validate_payoff_leg


def test_payoff_validation_rejects_bad_grid_and_leg():
    with pytest.raises(ValueError):
        validate_payoff_grid([100, 0])
    assert validate_payoff_leg({"option_type":"bad","strike":100,"position":"long"})["ok"] is False
    result = custom_multi_leg_payoff([{"option_type":"bad","strike":100,"premium":1,"position":"long"}], [90,100])
    assert result["ok"] is False
