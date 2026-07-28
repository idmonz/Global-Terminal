# No-Key Provider Integration

Goal 10 adds project-native provider adapters for free or no-key public sources.

## Providers

- SEC EDGAR: requires `SEC_USER_AGENT`.
- Treasury Fiscal Data: no key.
- World Bank: no key.
- SDMX public APIs: no key, endpoint-dependent.
- GDELT: no key.
- USGS Earthquake: no key.
- Open-Meteo: no key.
- NWS: requires `NWS_USER_AGENT`.
- NOAA AccessAIS: historical-only, never live AIS.
- Binance public: no key.
- DefiLlama: no key.
- CoinGecko public: no-key fallback, rate-limited, optional `COINGECKO_API_KEY`.

Free public data sources may have rate limits, delayed updates, schema changes, or usage restrictions. Source status and freshness should be verified before relying on outputs.

## Goal 10B Layer Labels

No-key/free providers now feed provider health heatmaps, source freshness indicators, map layers, and split probe scripts. NOAA AccessAIS stays historical-only. AISStream, OpenSky, NASA FIRMS, SEC user-agent, and NWS user-agent gaps remain visible without blocking base launch.
