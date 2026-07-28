# Hotspot Scoring Caveats

## Module

`lib/hotspot_scoring.py`

## Functions

- `compute_region_hotspot_score()`
- `compute_asset_hotspot_score()`
- `compute_chokepoint_hotspot_score()`
- `build_hotspot_leaderboard()`

## What The Score Means

Hotspot scores are 0-100 heuristic visualization scores. They combine available proxy evidence such as:

- News counts.
- High-severity headline counts.
- Market stress.
- Asset volatility.
- Chokepoint risk proxy.
- Source/data-gap penalties.

## What The Score Does Not Mean

- It is not an official intelligence assessment.
- It is not a live conflict, shipping, or vessel-tracking score.
- It is not a prediction model.
- It is not personalized financial advice.

## Required Labels

Any UI using hotspot scoring should label the output as:

- Heuristic.
- Estimated.
- Source-dependent.
- Unavailable when inputs are missing.
