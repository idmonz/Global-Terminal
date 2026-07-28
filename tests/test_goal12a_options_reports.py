from lib.options_report_generator import generate_options_iv_report, generate_options_pricing_report, generate_options_scenario_report

INPUT = {"option_type": "call", "underlying_price": 100, "strike": 100, "time_to_expiry_years": 1, "risk_free_rate": 0.05, "volatility": 0.2, "premium": 10.45}


def test_options_pricing_report_payload_has_required_sections():
    report = generate_options_pricing_report(INPUT, persist=False)
    assert report["report_type"] == "options_pricing_report"
    assert "Options and model outputs are research calculations only" in report["markdown_body"]
    assert "## Greeks" in report["markdown_body"]


def test_options_scenario_and_iv_reports_are_local():
    scenario = generate_options_scenario_report(INPUT, persist=False)
    iv = generate_options_iv_report(INPUT, persist=False)
    assert scenario["payload"]["scenario_count"] > 0
    assert iv["payload"]["converged"] is True
    assert scenario["research_only"] and iv["research_only"]
