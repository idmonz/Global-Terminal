# GOAL 12A Spec

## Scope

Goal 12A adds a research-only Options Pricing & Quant Model Lab on top of the Goal 11F Research OS.

## Options core

- European call/put Black-Scholes pricing.
- Black-76 futures option pricing.
- Garman-Kohlhagen FX option pricing.
- Delta, gamma, vega, theta, rho, and carry/dividend sensitivity fields.
- Implied-volatility solver with explicit convergence status and no fabricated value on failure.
- Payoff templates: single option, covered call profile, protective put profile, vertical spread, straddle, and strangle.
- Scenario grids for price, volatility, time decay, rates, PnL from supplied premium, and Greeks.

## Quant Model Lab core

- Model registry.
- Model snapshot schema.
- Local deterministic diagnostic payloads.
- Placeholder-safe categories for future correlation, volatility, regime, mean-reversion, cointegration, factor, foundation-model, and action-less simulation work.

## Integrations

- Options Lab page: `pages/24_Options_Quant_Model_Lab.py`.
- Research Tool Center tools and workflow actions.
- Command Palette and Terminal Router commands.
- Report Inbox attachments.
- Strategy-as-Git artifacts.
- Provider capability/caveat panels.

## Non-goals

No live chain ingestion by default, broker routing, order workflow, autonomous trading, heavy ML runtime, OpenBB dependency, Heston/SABR calibration, production optimizer, or external source vendoring.

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.
