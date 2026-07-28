# Phase 5I Product Contract

Updated: 2026-06-20

## User Journey

`Market Home -> Market Map -> filter/sort -> select -> compare -> supported workstation`

## Canonical Route

```text
/?view=market-map&mode=<mode>&assetClass=equity&sector=<sector>&freshness=<state>&sort=<metric>&direction=<asc|desc>&query=<text>&selected=<symbol>&compare=<symbols>
```

## First Viewport

Desktop must show:

1. concise product/runtime truth;
2. search, sector, freshness, and sort controls;
3. breadth summary;
4. a large hierarchical heatmap;
5. selected-instrument context.

It must not show repository-wide contract diagnostics.

## Interaction Contract

- Heatmap tile selects an instrument and updates `selected`.
- Sector/freshness/search/sort update URL state.
- Compare accepts up to four symbols and updates `compare`.
- Risk/return scatter selects the same instrument context.
- Ranked rows put missing metrics last and display `-`, never zero.
- Only verified product workstations become links. In this slice AAPL is the verified equity route; other symbols remain selectable research rows without fake workstation support.

## Visual Semantics

- Heatmap size: runtime market cap; fixture relative weight.
- Heatmap color: one-day return.
- Scatter X: annualized realized volatility.
- Scatter Y: one-month return.
- Rank: 55% one-month return percentile, 30% inverse-volatility percentile, 15% drawdown-resilience percentile.

Ranks are descriptive research calculations, not recommendations.

## Failure States

- live fetch success: `live/fresh`;
- within 10-minute runtime cache: `cached`;
- refresh failure within one hour: `stale` with the failure in `data_gap`;
- no usable provider/cache rows: explicit unavailable;
- deterministic fixture mode: synthetic metrics visibly labeled fixture.

