# Energy / Shipping / Chokepoint Backend

Modules:

- `lib/openbb_energy_backend.py`
- `lib/openbb_shipping_backend.py`
- `lib/shipping_chokepoint_engine.py`
- `lib/energy_market_impact.py`

Energy routes use native EIA when configured, optional OpenBB where available, and yfinance proxies when labeled. Shipping/chokepoint outputs default to static metadata and proxy risk scoring.

No live AIS is claimed unless an explicit provider is configured and tested.
