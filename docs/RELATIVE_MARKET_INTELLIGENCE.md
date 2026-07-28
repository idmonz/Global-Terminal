# Relative Market Intelligence

`lib/relative_market_intelligence.py` ranks supplied market rows against a benchmark for research context.

## Outputs

- RMI table with symbol, relative score, relative state, benchmark, source, and freshness.
- RMI cards for average, leaders, and laggards.
- RMI heatmap using the shared heatmap engine.

## Method

The score blends recent return versus benchmark with a volatility penalty. It is a research ranking only and does not produce trading directives.
