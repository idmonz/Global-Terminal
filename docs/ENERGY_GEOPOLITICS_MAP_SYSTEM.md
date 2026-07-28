# Energy Geopolitics Map System

`lib/energy_geopolitics_map.py` builds the Energy Geopolitics map payload.

## Layers

- Oil chokepoints
- Shipping/chokepoint proxy layer
- Weather/natural risk layer
- Energy news event layer
- Energy asset impact panel
- Shipping data-quality table

## Data Truth

- Static chokepoints are proxy exposure layers.
- NOAA AccessAIS is historical-only.
- AISStream live AIS is unavailable unless configured and probed.
- EIA/FRED style provider gaps remain visible and nonfatal.
- Energy asset impact is research context and proxy-labeled where appropriate.
