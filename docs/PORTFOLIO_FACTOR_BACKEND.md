# Portfolio Factor Backend

Modules:

- `lib/openbb_technical_backend.py`
- `lib/openbb_fundamental_factor.py`
- `lib/openbb_rates_factor.py`
- `lib/openbb_options_factor.py`
- `lib/openbb_factor_backend.py`
- `lib/portfolio_factor_router.py`

The backend provides technical, value, quality, growth, profitability, rates/macro, and options activity scores with factor coverage, source confidence, data quality penalty, and data gap reports.

Options gamma remains proxy-labeled unless official provider gamma is present.
# Goal 10 Update

`build_portfolio_factor_inputs()` is restored in `lib.portfolio_quant_lab` as a compatibility helper. Goal 10 adds strategy data quality scoring that combines factor coverage, source confidence, sample length, missing values, proxy dependence, and OOS availability.
