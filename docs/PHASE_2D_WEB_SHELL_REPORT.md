# Phase 2D Web Shell Report

Updated: 2026-06-16

## Outcome

Branch taken: `web-shell-buildable`.

The local web toolchain is available, so this slice created the first fixture-backed Next.js shell under `apps/web`.

## Toolchain Gate

```bash
node --version
# v24.16.0

npm --version
# 11.13.0

npx --version
# 11.13.0
```

`create-next-app@latest` resolved to `create-next-app@16.2.9` and scaffolded a TypeScript App Router project with npm.

## Shell Scope

The shell consumes the checked-in Phase 2C static fixtures from:

```bash
static/api-fixtures/
```

Consumed fixtures:

- `manifest.json`
- `war-room.json`
- `news.json`
- `provider-health.json`
- `layers.json`
- `feeds.json`
- `ai-providers.json`

The shell renders:

- Top command/status bar.
- Left workspace rail.
- Central contract-driven work panel.
- Right caveat, unavailable, error, and source-status rail.
- Bottom provider/freshness strip.

## Contract Boundary

The web shell validates the common Phase 2B envelope:

- `contract_version`
- `payload_type`
- `generated_at`
- `data`
- `summary`
- `source_status`
- `unavailable`
- `errors`
- `caveats`

The contract version remains `phase_2b.v1`. Live FastAPI wiring is disabled by default. Static fixtures are development payloads and do not claim live AIS, OpenSky, sanctions, premium market data, or premium crypto analytics.

## Security And Dependency Review

The initial `create-next-app` install reported two moderate PostCSS advisories through `next -> postcss@8.4.31`.

This slice added an npm override so Next resolves to the patched PostCSS version already compatible with the Tailwind toolchain:

```json
"overrides": {
  "next": {
    "postcss": "8.5.15"
  }
}
```

Confirmed dependency state:

```bash
npm ls postcss
# @tailwindcss/postcss -> postcss@8.5.15 overridden
# next@16.2.9 -> postcss@8.5.15 deduped

npm audit
# found 0 vulnerabilities
```

## Verification

Python contract checks:

```bash
python -m pytest tests/test_api_fixture_export.py tests/test_api_backend_routes.py tests/test_api_contracts.py -q
# ....s......... [100%]

python -m py_compile app.py lib/api_contracts.py lib/api_contract_panels.py backend/api/app.py scripts/export_api_fixtures.py
# passed
```

Web checks:

```bash
npm --prefix apps/web test
# Validated 7 phase_2b.v1 fixtures

npm --prefix apps/web run lint
# passed

npm --prefix apps/web run build
# passed
```

Runtime check:

```bash
npm --prefix apps/web run dev -- --port 3000
Invoke-WebRequest http://localhost:3000/?view=provider-health
Invoke-WebRequest http://localhost:3000/?view=ai-providers
Invoke-WebRequest http://localhost:3000/?view=war-room
```

The rendered HTML contains the expected Phase 2D workspace headings and no `Create Next App` starter-page marker.
The runtime shell renders `static/api-fixtures` as the fixture source label and does not expose local absolute paths.

The in-app browser connector was attempted, but the `iab` browser was unavailable in this session. Local HTTP runtime checks were used as the fallback.

## Runtime Status

- FastAPI remains optional and is not added to base requirements.
- OpenSky remains `missing-key` unless OAuth credentials and a real `/states/all` fetch succeed.
- Gemini remains free-first. Google Search grounding remains opt-in and disabled in the fixture summary.
- `OPENAI_API_KEY` is not required.

## Next Step

Wire optional FastAPI reads behind an explicit feature flag or environment setting while preserving the checked-in fixture fallback as the default development mode.
