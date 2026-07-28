# OpenBB Setup Guide

OpenBB is optional.

```powershell
pip install -r requirements-openbb.txt
```

Optional provider keys can be placed in a local `.env` or environment variables. `.env.example` lists blank placeholders only.

Common optional keys:

- `FMP_API_KEY`
- `FRED_API_KEY`
- `EIA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FINNHUB_API_KEY`
- `POLYGON_API_KEY`
- `TIINGO_API_KEY`
- `TRADIER_API_KEY`
- `INTRINIO_API_KEY`

Do not commit real keys. Missing keys must appear as data gaps, not crashes.
