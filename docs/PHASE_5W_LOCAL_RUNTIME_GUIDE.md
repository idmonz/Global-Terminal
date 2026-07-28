# Phase 5W Local Runtime Guide

Date: 2026-06-30

## Quick Start

From the repository root:

```powershell
python scripts/start_local_product.py --production --wait-seconds 60
```

Then open:

```text
http://127.0.0.1:3000/
```

The script starts or reuses:

- FastAPI: `http://127.0.0.1:8000`
- Next.js: `http://127.0.0.1:3000`

## Development Mode

```powershell
python scripts/start_local_product.py --wait-seconds 60
```

Development mode uses `next dev`. It is useful while editing, but visual QA should use production mode because Fast Refresh can reload the page while screenshots are being captured.

## Dry Run

```powershell
python scripts/start_local_product.py --dry-run
```

Dry run prints commands, URLs, and environment overrides without starting processes. It does not print secret values.

## Expected Runtime Chip

When the API is reachable, the top bar should show:

```text
Runtime API
online
37 routes / 250 providers
```

Counts can change as routes/providers are added. They should not be hard-coded into product logic.

When FastAPI is offline, the product should continue rendering deterministic fallback rows, but the runtime chip and fallback notices must make that state visible.

## API Setup

FastAPI dependencies are optional:

```powershell
python -m pip install -r requirements-api.txt
```

Free-first providers are preferred. Optional API keys should stay in `.env` and must never be printed, committed, serialized into fixtures, or sent to public AI tools.

## Port Conflicts

The launcher does not kill unrelated processes. If a port is occupied and the expected health check fails, close the unrelated process or choose another port:

```powershell
python scripts/start_local_product.py --api-port 8010 --web-port 3010
```

The web product expects the API base URL to match:

```powershell
$env:GLOBAL_TERMINAL_API_BASE_URL="http://127.0.0.1:8010"
$env:NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL="http://127.0.0.1:8010"
```

The launcher sets these overrides for its child processes.
