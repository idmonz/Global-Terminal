# Data Sources

## Goal 7 Provider Center

`lib/provider_registry.py` centralizes market, crypto, news/OSINT, geopolitics, natural/weather, AIS/shipping, flight, and prediction-market provider metadata. `pages/17_Data_Provider_Center.py` exposes capability, configuration, health, freshness, and gap views.

## Free/Public

- yfinance: equities, ETFs, indexes, crypto spot proxies, energy futures, financial statements, info fields, and option chains when available.
- Binance public USD-M Futures endpoints: open interest, funding, taker ratio, long/short ratios, and recent trades.
- CoinGecko public endpoints: crypto market overview.
- DefiLlama public APIs: TVL, protocols, stablecoins, DEX volume, and fees when reachable.
- GDELT and public RSS feeds: geopolitical and energy news proxy.
- Static CSV universes: S&P 500 seed, Nasdaq 100 seed, Korea watchlist.
- Static chokepoint and route proxies: map visualization when live provider data is unavailable.
- Heuristic news intelligence builders: local classification of public feed rows by severity, region, asset channel, credibility, and freshness.
- Heuristic radar/fusion builders: local 0-100 visualization scales for market radar, signal convergence, and hotspot leaderboards.
- Portfolio Quant Lab: user-supplied portfolio rows plus yfinance price history when a backtest is explicitly run.

## Optional Keys

- `EIA_API_KEY`: EIA petroleum fundamentals.
- `WORLD_MONITOR_BASE_URL` / `WORLD_MONITOR_KEY`: optional WorldMonitor adapter endpoints.
- `AISSTREAM_API_KEY`, `MARINETRAFFIC_API_KEY`, `VESSELFINDER_API_KEY`: optional AIS/shipping providers. Live AIS remains unavailable without configured/tested providers.
- `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET`, `ADSB_API_KEY`: optional flight providers. OpenSky uses OAuth2 client credentials for `/states/all`; legacy `OPENSKY_USERNAME` / `OPENSKY_PASSWORD` are accepted as local aliases only. Live flight tracking remains unavailable without configured/tested providers.
- `COINGLASS_API_KEY`, `CRYPTOQUANT_API_KEY`, `GLASSNODE_API_KEY`, `KAIKO_API_KEY`: optional crypto intelligence providers.
- `ANTHROPIC_API_KEY`: Anthropic Claude.
- `GEMINI_API_KEY`: Google Gemini. Defaults to the low-cost/free-tier-first `gemini-3.1-flash-lite` model when no `AI_MODEL` override is set.
- `GROQ_API_KEY`: Groq.
- `OPENROUTER_API_KEY`: OpenRouter.
- `OLLAMA_BASE_URL`: local Ollama OpenAI-compatible API.

Missing or rate-limited feeds return `DataResult` warnings and do not fabricate production data.

## Estimated / Proxy Layers

- Market radar scores are heuristic visualization proxies.
- Signal fusion scores are heuristic convergence summaries.
- Hotspot scores are heuristic and not official intelligence assessments.
- Chokepoint and route maps are static proxies unless a real provider is configured.
- Live AIS or vessel flow is unavailable without a real AIS provider.
- Gamma exposure is a proxy and not dealer-confirmed.

See `docs/DATA_SOURCE_LIMITATIONS.md` for caveats.
## Goal 6 Data Sources

- War Room: normalized public/news inputs when supplied, local static chokepoint registry, route exposure proxy arcs, recent `DataResult` telemetry, and heuristic country/hotspot scoring.
- Financial Terminal: yfinance company info, reported income statement, balance sheet, cash flow, ratios, and earnings dates when available.
- News Market Impact: deterministic entity/keyword/region asset mapping, optional yfinance price history for observed related market moves, and data-gap rows when price history is not supplied.
- Optional providers: FMP, Alpha Vantage, Finnhub, Polygon, AIS, flight tracking, webcam, and WorldMonitor adapter layers are visible as optional/unavailable unless configured.

Goal 6 does not fabricate unavailable financial estimates, segment revenue, geographic revenue, live vessel flow, live flight tracking, or official country risk scores.

## Goal 8 OpenBB Optional Backend

- OpenBB is an optional external dependency installed with `requirements-openbb.txt`.
- Optional OpenBB/provider keys are listed in `.env.example`; real values are never displayed.
- Native yfinance, FRED, EIA, Binance, CoinGecko, DefiLlama, and local modules remain the base data layer.
- OpenBB-backed fields are labeled by source mode, provider status, fallback behavior, and caveat.
- Estimates, ownership, peer, options, ETF exposure, and segment/geography fields remain data gaps unless provider-supplied.

## Goal 9 Source Routing

The internal endpoint catalog and provider router now define native providers, optional OpenBB candidate paths, optional provider keys, proxy permissions, and downstream pages.

Shipping/chokepoint, gamma, rates, and some energy outputs remain proxy-labeled unless official provider data is configured.
# Goal 10 Update

Goal 10 adds a no-key/free provider catalog and lightweight adapters for SEC EDGAR, Treasury Fiscal Data, World Bank, SDMX public APIs, GDELT, USGS Earthquake, Open-Meteo, NWS, NOAA AccessAIS, Binance public, DefiLlama, and CoinGecko public fallback. SEC and NWS require user-agent environment variables. NOAA AccessAIS is historical-only. CoinGecko keyless fallback is rate-limited.

Provider status is surfaced through Data Provider Center and `lib.provider_probe_runner` dry-run diagnostics.

## Goal 10B Data Source Truth Labels

Goal 10B adds shared freshness and truth labels across overview, heatmaps, maps, provider probes, and page payloads: live, fresh, aging, stale, unknown, proxy, estimated, historical-only, missing-key, unavailable, inferred location, and low-confidence geocode.

NOAA AccessAIS remains historical-only. AISStream, OpenSky, NASA FIRMS, and NWS-style keyed layers remain missing-key or unavailable until the relevant credentials and probes are present. TradingView widgets are optional external visual supplements only.

## Goal 11 Update

Goal 11 adds a local Personal Research Operating System layer. It stores private workspace state in SQLite under `data/private/`, adds watchlist/alerts/reports/strategy decision-log workflows, links OSINT/provider context to watchlist records, and remains manual, research-only, and release-hygiene controlled. No external source code, external folders, private DBs, secrets, live trading, broker execution, or background automation are included in release artifacts.


## Goal 11B source snapshots

Reports and alerts use source snapshots and provider/data-quality memory. Missing or stale provider context is labeled instead of fabricated.
