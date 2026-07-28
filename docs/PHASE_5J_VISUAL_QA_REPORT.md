# Phase 5J Visual QA Report

Updated: 2026-06-21

## Method

The in-app Browser connection failed because the browser runtime lacked required sandbox metadata. Per the repository skill, visual QA fell back to the existing `playwright-core` harness controlling installed production Chrome against `next start` and local FastAPI.

Command:

```powershell
npm.cmd --prefix apps/web run visual:phase5j
```

## Baseline

- `review_workspace/phase5j_visual/baseline-options-desktop.png`
- `review_workspace/phase5j_visual/baseline-options-mobile.png`

The old first viewport was a contract-diagnostics page with 193 coverage gaps, no option chain, and workspace navigation before analysis.

## Final Evidence

- `review_workspace/phase5j_visual/options-live-chain-desktop.png`
- `review_workspace/phase5j_visual/options-live-iv-desktop.png`
- `review_workspace/phase5j_visual/options-live-chain-mobile.png`
- `review_workspace/phase5j_visual/options-fixture-scenario.png`

## Automated Assertions

- live/cache contract rows: 267;
- selected-expiry strike rows: 44;
- chain table width: 860px;
- IV chart source points: 65 after interaction;
- mobile viewport/product width: 390px/350px with no horizontal product overflow;
- fixture contract rows: 42;
- fixture scenario rows: 15;
- URL preserved expiry, surface, option type, moneyness, selected contract, compare expiry, symbol, and mode;
- browser console errors: 0.

Interaction URL:

`/?view=options-quant&symbol=AAPL&mode=live-if-available&surface=iv&optionType=put&moneyness=atm&expiry=2026-06-24&selected=AAPL260624P00292500&compare=2026-06-22`

## Defects Found And Corrected

1. Contract diagnostics owned the first viewport. Added a product-first route.
2. The centered sticky strike column intercepted quote clicks. Removed the incorrect `left:50%` sticky overlay.
3. Mobile top-bar, navigation, and runtime banner pushed analysis below the first viewport. Added an options-specific compact mobile shell and active-first navigation.
4. The visual harness used checkbox state after router replacement. Changed the authoritative assertion to persisted URL state.
5. A 350px padded product width was initially misclassified as overflow. Corrected the assertion while retaining the 390px maximum check.

## Personal Inspection

Desktop chain and IV screenshots are dense but readable, source truth is secondary to analysis, selected-contract context fits without overlap, and red/green are limited to option-side/data semantics. The mobile screenshot exposes symbol, underlying, expiry, quality, filters, analysis tabs, and the chain heading in the first viewport. The fixture scenario clearly states fixture mode and remains useful rather than blank.

## Residual Visual Risk

The chain uses horizontal scrolling on narrow screens. The IV view is a first-party SVG line chart rather than a full interactive volatility surface. No 3D surface is shown because the data and interaction value do not justify it in this slice.
