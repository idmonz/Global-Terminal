# Goal 12C Security Audit

Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions.

Security controls added:

- `research_report_sanitizer.escape_report_identifier` escapes HTML/script content and redacts local paths.
- `escape_csv_formula_text` prefixes formula-like CSV cells before escaping.
- report table sanitization is used by option-chain reports.
- demo data is separated by explicit demo mode.
- release excludes external archives, private data, cache data, local uploaded CSVs, DB files, secrets, model weights, and pycache.
- optional statsmodels use is guarded with fallback; no Torch/TensorFlow/HuggingFace dependency is introduced.
