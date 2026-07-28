# Signal Fusion System

## Module

`lib/signal_fusion.py`

## Purpose

Create deterministic, testable multi-source signal fusion without adding heavy ML dependencies or provider requirements.

## Functions

- `normalize_signal()`
- `fuse_market_signals()`
- `fuse_news_signals()`
- `fuse_energy_signals()`
- `fuse_crypto_signals()`
- `build_signal_convergence_table()`

## Signals

Supported signal families include:

- Market price moves.
- Volatility regime.
- Breadth deterioration.
- Crypto derivatives crowding.
- Oil and geopolitical risk proxies.
- News severity.
- Source freshness.
- Data gaps.

## Interpretation

Signal fusion is heuristic. It helps show convergence and disagreement across available evidence. It is not an official score, prediction model, or directive.
