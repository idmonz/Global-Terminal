# Schema Normalization System

`lib/schema_normalizer.py` provides tolerant normalizers for prices, quotes, financial statements, ratios, estimates, ETF holdings, options, macro/rates, energy, shipping, technical indicators, news, and screeners.

Rules:

- Never crash on missing columns.
- Normalize common date, symbol, ticker, and numeric fields.
- Preserve source/proxy/estimated flags in DataFrame attrs.
- Return `(DataFrame, list[DataGap])`.
- Do not fabricate unavailable data.
