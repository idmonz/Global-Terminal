# Phase 8 AI Visual Terminal Report

## Implemented

- `lib/ai_providers.py`: provider selection and calls for Anthropic, Gemini, Groq, OpenRouter, Ollama, and deterministic rule-based fallback.
- `lib/ai_prompts.py`: neutral financial research prompt templates.
- `lib/ai_safety.py`: forbidden-language filtering, allowed market-context terms, disclosure append, and secret redaction.
- `lib/ai_analysis.py`: neutral analysis functions for overview, stocks, ETFs, crypto, energy/geopolitics, portfolio risk, screeners, and scenarios.
- `lib/overview.py`: Overview Terminal data builder.
- `lib/map_viz.py`: event, chokepoint, country-risk, route-proxy, and region maps.
- `lib/fundamentals.py`: financial statement normalization, growth, margin, valuation, and balance quality helpers.
- `lib/options_flow.py`: yfinance options chain, put/call ratios, max-pain proxy, gamma exposure proxy, and caveats.
- `lib/screeners.py` and `lib/bond_data.py`: multi-asset screeners and bond/rate proxy metrics.

## UI Updates

- `app.py` now opens directly into an Overview Terminal.
- Stock Analyzer includes Price & Technicals, Financial Overview, Valuation, Options & Gamma Proxy, News & AI, and Scenario tabs.
- ETF, Macro, News, Crypto, Energy/Geopolitics, Scenario Lab, Market Pulse, and Data Quality pages now expose Phase 8 AI/source-status controls where appropriate.
- `pages/13_Screener.py` adds stock, ETF, crypto, bond/rates, commodity, and cross-asset screener workflows.

## Safety

- No LLM call is made on page load.
- Missing keys return structured warnings and fallback behavior.
- Prompt context expanders are redacted.
- Output is cleaned and validated before display.
