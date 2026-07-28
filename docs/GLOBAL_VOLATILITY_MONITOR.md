# Global Volatility Monitor

`lib/global_volatility_monitor.py` builds a volatility risk board from supplied market rows.

## Outputs

- Volatility ranking with z-score, drawdown state, volatility state, and risk score.
- Volatility cards and heatmap.
- Global state: watch, elevated, or severe.

## Method

The monitor uses realized volatility z-scores and drawdown severity. It is source-labeled research context, not a forecast.
