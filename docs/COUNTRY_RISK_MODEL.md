# Country Risk Model

`lib/country_risk_model.py` implements a transparent heuristic country/regional instability model.

## Inputs

- Normalized event rows.
- Country or region metadata.
- Optional market stress input.
- Source freshness and data-gap penalties.

## Components

- `unrest_score`
- `conflict_score`
- `security_score`
- `information_score`
- `market_stress_score`
- `energy_chokepoint_score`
- `source_freshness_penalty`
- `data_gap_penalty`

## Output

Rows include country, ISO2/ISO3, region, 0-100 instability score, risk level, component scores, key drivers, data gaps, and caveat.

The score is heuristic and not an official intelligence, sovereign, or country-risk rating.
