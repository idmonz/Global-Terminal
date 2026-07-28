# Layer Registry

`lib/layer_registry.py` defines the War Room layer registry.

## Required Fields

Each layer includes:

- `layer_id`
- `label`
- `domain`
- `icon`
- `source`
- `provider`
- `is_available`
- `is_estimated`
- `is_optional`
- `requires_key`
- `freshness_status`
- `caveat`

## Layer Types

- Geopolitical: conflicts, protests, sanctions, elections/policy, diplomatic tension.
- Energy/infrastructure: chokepoints, optional pipelines/LNG/storage/refinery layers, outage proxies.
- Natural/weather: optional earthquake, fire, storm, and climate anomaly layers.
- Market/finance: indices, FX, rates, commodities, crypto, volatility.
- Crypto: OI/funding stress and liquidation pressure proxy; unavailable optional stablecoin/exchange stress layers.
- OSINT optional: AIS unavailable marker, flight tracking unavailable marker, live webcams placeholder, optional WorldMonitor adapter.

Unavailable layers are not hidden. They remain visible as unavailable or optional with caveats.
