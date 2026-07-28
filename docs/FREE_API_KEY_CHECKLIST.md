# Free API Key Checklist

| Provider | Purpose | Env Var | Setup Steps | Required | No-Key Fallback | Pages | Caveat |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SEC EDGAR | Filings/company facts | `SEC_USER_AGENT` | Add descriptive user-agent locally | Yes | No | Financial Terminal | Required for SEC requests |
| NWS | US weather points/alerts | `NWS_USER_AGENT` | Add descriptive user-agent locally | Yes | No | Energy / War Room | Required for NWS requests |
| FRED | US macro | `FRED_API_KEY` | Add free key if available | No | Yes | Macro | Fallback may be limited |
| EIA | Energy stats | `EIA_API_KEY` | Add free key if available | No | Yes | Energy | Some endpoints require key |
| Alpha Vantage | Equity fundamentals/dividend breadth | `ALPHAVANTAGE_API_KEY` | Get a free key at Alpha Vantage, add it to `.env`, then run a Watchlist Research Snapshot or open Financials | No | Yes | Watchlist / Symbol Workstation | Standard free service is documented as 25 requests/day. A five-symbol snapshot spends at most 5 overview calls and reads cache/LKG first; target-price fields are excluded |
| Finnhub | Equity earnings/company news | `FINNHUB_API_KEY` | Register a free key at Finnhub, add it to `.env`, then run a Watchlist Research Snapshot or open Catalysts | No | Yes | Watchlist / Symbol Workstation | A five-symbol snapshot spends at most 5 earnings and 5 news calls, honors cache first, and surfaces HTTP 429 without hiding saved rows |
| NASA FIRMS | Fire/hotspot context | `NASA_FIRMS_MAP_KEY` | Add free MAP_KEY | Yes | No | War Room | Never connected without key |
| AISStream | AIS stream | `AISSTREAM_API_KEY` | Add key and test probe | Yes | No | War Room | Never live without key and probe |
| OpenSky | Flight tracking | `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET` | Add OAuth credentials if available | No | Yes | War Room | Optional for base launch |
| CoinGecko | Crypto prices | `COINGECKO_API_KEY` | Add optional key | No | Yes | Crypto | Keyless fallback is rate-limited |
| BOK ECOS | Korea macro | `BOK_ECOS_API_KEY` | Add free key if available | No | Yes | Macro | Terms must be verified |
| OpenDART | Korea filings | `OPENDART_API_KEY` | Add free key if available | No | Yes | Financial Terminal | Terms must be verified |
| KOSIS | Korea statistics | `KOSIS_API_KEY` | Add free key if available | No | Yes | Macro | Terms must be verified |
| KRX | Korea market data | `KRX_API_KEY` | Add key if available | No | Yes | Korea Desk | Terms must be verified |
