from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot
from lib.options_model_selector import build_row_pricing_input, infer_option_pricing_model_for_row

UNKNOWN = {"underlying":"MYST","option_type":"call","expiry":"2026-07-15","timestamp":"2026-06-15","strike":100,"underlying_price":100,"bid":5,"ask":6,"source":"unit"}


def test_goal12d_unknown_without_model_does_not_build_pricing_input():
    payload = infer_option_pricing_model_for_row(UNKNOWN)
    assert payload["ok"] is False
    assert payload["model"] in {"manual", "unknown", "manual_unknown"}
    try:
        build_row_pricing_input(UNKNOWN)
    except ValueError as exc:
        assert "pricing_skipped_missing_model" in str(exc)
    else:
        raise AssertionError("unknown row priced silently")


def test_goal12d_unknown_with_explicit_model_override_prices_with_caveat():
    inp = build_row_pricing_input({**UNKNOWN, "model":"black_scholes"})
    assert inp["model"] == "black_scholes"
    assert "user_supplied_model_override" in inp["caveats"]


def test_goal12d_crypto_remains_caveated_but_allowed():
    inp = build_row_pricing_input({**UNKNOWN, "asset_class":"crypto", "underlying":"BTC"})
    assert inp["model"] == "black_scholes"
    assert "crypto_option_uses_black_scholes_style_caveat" in inp["caveats"]


def test_goal12d_chain_iv_counts_skipped_unknown_as_no_solution():
    chain = build_option_chain_snapshot(rows=[UNKNOWN])
    iv = build_chain_iv_snapshot(chain)
    assert iv["no_solution_count"] == 1
    assert iv["rows"][0]["iv_status"] == "pricing_skipped_missing_model"
    assert iv["rows"][0]["mid_iv"] is None
