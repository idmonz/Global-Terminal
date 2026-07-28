# GOAL 12A Options Model Architecture

## Layering

1. `options_pricing_inputs.py`: normalized dataclass and research-only notice.
2. `options_validation.py`: input validation and model-specific field checks.
3. `options_pricing_models.py`: original local closed-form pricing functions.
4. `options_greeks.py`: analytic Greeks for the supported model families.
5. `options_iv_solver.py`: bisection IV solver with robust bounds and failure reasons.
6. `options_payoff.py` and `options_strategy_templates.py`: mathematical payoff templates.
7. `options_scenarios.py`: deterministic scenario and sensitivity grids.
8. `options_result_schema.py`: stable result payloads.
9. `options_report_generator.py`, `options_attachment_bridge.py`, and `options_strategy_commit_bridge.py`: Research OS integration.
10. `options_provider_capabilities.py` and `options_data_quality.py`: source/caveat layer.
11. `options_lab_page_layout.py` and `pages/24_Options_Quant_Model_Lab.py`: UI payload and Streamlit page.

## Formula coverage

- Black-Scholes: equity/index-style European options with continuous carry/dividend yield.
- Black-76: futures options using discounted futures payoff.
- Garman-Kohlhagen: FX options with domestic discounting and foreign-rate carry.

## Failure handling

- Non-positive spot/strike/time and negative/zero volatility are rejected.
- IV solver returns explicit `ok=False` and `error_reason` when missing premium, target below lower bound, target above upper bound, pricing failure, or max iterations.

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.
