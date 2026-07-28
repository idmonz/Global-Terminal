# Phase 5S Provider Key Readiness

Updated: 2026-06-23

## Rule

The project may read `.env` provider names locally, but documentation, fixtures, screenshots, release archives and API payloads must never expose secret values.

Configured credentials do not equal live data. A provider is promoted to `live/fresh` only after a successful provider fetch produces verified rows.

## Keys Present Locally

Only key names were inspected:

- `AISSTREAM_API_KEY`
- `BLS_API_KEY`
- `BOK_ECOS_API_KEY`
- `COINGECKO_API_KEY`
- `EIA_API_KEY`
- `FRED_API_KEY`
- `GEMINI_API_KEY`
- `KOSIS_API_KEY`
- `KRX_API_KEY`
- `NASA_FIRMS_MAP_KEY`
- `NWS_USER_AGENT`
- `OPENDART_API_KEY`
- `OPENSKY_CLIENT_ID`
- `OPENSKY_CLIENT_SECRET`
- `SEC_USER_AGENT`

## Free / Free-Tier Provider Policy

The current `.env.example` already includes placeholder entries for the free-first providers most relevant to the roadmap:

- FRED, EIA, BLS, NASA FIRMS, NWS;
- AISStream and OpenSky;
- CoinGecko and keyless Binance public endpoints;
- BOK ECOS, OpenDART, KOSIS and KRX;
- SEC User-Agent;
- Gemini for optional free-first AI.

Phase 5T should use these keys only through source-specific fetch functions and should add missing placeholder variables to `.env.example` before any new provider is required.

## Phase 5T Provider Acceptance

- BTCUSDT/ETHUSDT chart reliability must use Binance public history or deterministic fixture fallback honestly.
- OpenSky must remain unavailable/configured-unverified until OAuth and `/states/all` both succeed.
- AISStream must remain unavailable/configured-unverified until a verified feed row is available.
- Korean market providers must be added as explicit free-first candidates, not silently claimed live.
