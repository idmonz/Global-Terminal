# Environment Variable Setup

Copy `.env.example` to `.env` for local-only provider setup. The example file is included in release and contains blank placeholders only.

## Optional provider variables

- `FRED_API_KEY`
- `EIA_API_KEY`
- `BLS_API_KEY`
- `NASA_FIRMS_MAP_KEY`
- `AISSTREAM_API_KEY`
- `OPENSKY_CLIENT_ID`
- `OPENSKY_CLIENT_SECRET`
- `COINGECKO_API_KEY`
- `BOK_ECOS_API_KEY`
- `OPENDART_API_KEY`
- `KOSIS_API_KEY`
- `KRX_API_KEY`
- `SEC_USER_AGENT`
- `NWS_USER_AGENT`

Do not commit `.env` or provider keys. Release packaging includes `.env.example` and excludes local secret files.

## OpenSky

OpenSky uses OAuth2 client credentials for authenticated API calls.

Set both values together:

```env
OPENSKY_CLIENT_ID=
OPENSKY_CLIENT_SECRET=
```

Legacy names `OPENSKY_USERNAME` and `OPENSKY_PASSWORD` are treated as aliases by the local env loader, but new setup should use `OPENSKY_CLIENT_ID` and `OPENSKY_CLIENT_SECRET`.
