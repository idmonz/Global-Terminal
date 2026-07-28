# Phase 5J Product Contract

Updated: 2026-06-21

## User Journey

`AAPL workstation or Product Nav -> Options Quant -> expiry -> chain/IV/Greeks/exposure/scenario -> source and assumption inspection`

## Canonical Route

```text
/?view=options-quant&symbol=AAPL&expiry=<date>&surface=<chain|iv|greeks|exposure|scenario>&optionType=<all|call|put>&moneyness=<all|itm|atm|otm>&selected=<contract>&compare=<expiries>&mode=<mode>
```

## First Viewport

Desktop must show:

1. symbol, underlying, expiry, chain status, provider, and fetched time;
2. compact expiry/type/moneyness/surface controls;
3. a dense calls/strike/puts chain or the selected analysis view;
4. selected-contract context;
5. a compact source/assumption rail.

Repository-wide envelope counts and contract diagnostics must not own the first viewport.

## Interaction

- Controls update URL state without replacing the selected symbol.
- Chain rows select a contract.
- Calls and puts remain visually distinguishable without relying on color alone.
- Missing values render as `-`, never zero.
- Exposure and surface tabs remain explicit unavailable states until evidence gates pass.
- Returning to AAPL or Market Map preserves runtime mode.

## Visual Semantics

- Chain: calls left, strike center, puts right, with bid/ask/last/volume/OI/IV.
- IV: strike on X, provider IV on Y, separate call/put series.
- Greeks: delta/gamma/vega/theta by strike with unit labels.
- Exposure: assumption-dependent gamma exposure by strike.
- Scenario: selected-contract price matrix across bounded spot and volatility shocks.

No surface is a recommendation, order ticket, or observed dealer-position claim.
