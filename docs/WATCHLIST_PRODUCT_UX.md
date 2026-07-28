# Watchlist Product UX

The watchlist now includes a summary strip, source freshness strip, command quick-add flow, product table columns, detail panel, news/event grid, alert-builder payload, alert timeline, RMI/volatility/heatmap tabs, optional TradingView supplement, and raw payload expander.

Missing context remains unavailable rather than fabricated.


## Goal 11D quick-add execution

Watchlist quick-add now routes through `run_research_workflow_action(ADD_WATCHLIST_ITEM)`, records activity, and refreshes local workspace state. Command result cards carry target page, caveat, data required, output type, and research-only flags.
