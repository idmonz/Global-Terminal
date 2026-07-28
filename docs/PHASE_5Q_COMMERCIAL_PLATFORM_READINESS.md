# Phase 5Q Commercial Platform Readiness

Updated: 2026-06-23

## Current Boundary

- Streamlit: internal lab and regression reference.
- `lib/`: reusable provider, normalization, research, quant and persistence engines.
- FastAPI: optional local API boundary.
- Next.js: commercial B2C product surface.
- Fixtures: deterministic demo and test fallback.
- SQLite: local-private memory only.

## What Improved In 5Q

- Daily-use route added instead of another contract gallery.
- Claim/source/gap/readiness information is visible in the first workflow.
- Local private capture and review state exists for daily research artifacts.
- Optional AI is constrained to public-sanitized evidence and validator gates.
- Release hygiene excludes local DB content and `.env` values.

## Remaining Commercial Gaps

| Area | Status after 5Q | Next need |
|---|---|---|
| System design | Good local modular boundary | Deployment architecture and SLOs |
| Frontend | Strong internal-beta verticals | More chart density, layout composition, user presets |
| APIs/backend | Optional FastAPI routes | Auth-aware hosted API, rate limits, job queues |
| Database/storage | Local SQLite only | Hosted tenant storage, backups, encryption, retention controls |
| Auth/permission | Absent | Account model, roles, entitlements |
| Billing | Absent | Subscription and feature gates |
| Hosting/cloud | Local only | Production deploy target and environment management |
| CI/CD | Absent in this filesystem snapshot | Automated tests/build/release gates |
| Security | Good local secret/release hygiene | Threat model, CSP, audit logs, dependency policy |
| Rate limiting | Provider-specific and local cache only | API gateway and provider-budget controls |
| Caching/CDN | Runtime cache and fixtures | Edge/static CDN and cache invalidation rules |
| Error tracking/logs | Local test output only | Structured logs, error tracking, alerting |
| Monitoring/alerts | Absent | Health probes, uptime, provider freshness alerts |
| Testing | Strong local regression/visual gates | CI-backed cross-browser and contract monitoring |
| Scaling | Not attempted | Background refresh and horizontally safe cache/store |

## Phase 5R Commercial Direction

The next step should not be auth or billing yet. The product still needs a richer daily workflow powered by visible fresh data and charts. Phase 5R should deepen provider-backed Daily Brief content before adding commercial shell infrastructure.
