# Phase 2D Web Shell

Fixture-backed Next.js shell for the Global Macro + Equity + Crypto + Commodity + Geopolitical Risk Terminal.

## Data Source

The shell reads checked-in Phase 2C fixtures from:

```bash
static/api-fixtures/
```

Live FastAPI wiring is intentionally off by default. The first shell validates and renders the shared `phase_2b.v1` envelope contract before any live backend dependency is introduced.

## Commands

```bash
npm run dev
npm run lint
npm test
npm run build
```

`npm test` validates every fixture consumed by the shell has:

- `contract_version`
- `payload_type`
- `generated_at`
- `data`
- `summary`
- `source_status`
- `unavailable`
- `errors`
- `caveats`

## Fixture Views

- Manifest / backend readiness
- War Room summary
- News summary
- Provider Health
- Layers
- Feeds
- AI provider readiness

Unavailable and error rows remain visible in the right rail and bottom freshness strip. Fixtures are development payloads, not claims of live AIS, OpenSky, sanctions, premium market data, or premium crypto analytics.
