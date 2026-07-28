# Phase 6J Preflight And Threat Model

Updated: 2026-07-10

## Baseline

- Python 3.14.5, Node 24.16.0, npm 11.13.0.
- 946 Python tests passed with one TestClient deprecation and two existing
  cointegration warnings.
- Compileall, import smoke, web fixture/runtime checks, ESLint, Next.js 16.2.9
  production build, and npm high-severity audit passed.
- Baseline release contained 1,619 entries.
- 28 external archives were present and re-audited: 18 direct-use-allowed,
  6 behavior-only, 3 needs-review, 1 blocked.
- Supabase URL/anon/service-role values are not configured.

## Official Guidance Applied

OpenAI's 2026 harness guidance recommends a short `AGENTS.md` as a map, detailed
repository-local execution plans, mechanically checked knowledge, strict
architectural boundaries, and treating failures as missing harness capability.
Phase 6J adds `docs/PLANS.md`, a versioned active plan, `docs/SECURITY.md`, and a
harness validator.

Official references:

- https://openai.com/index/harness-engineering/
- https://openai.com/index/unrolling-the-codex-agent-loop/
- https://openai.com/business/guides-and-resources/how-openai-uses-codex/
- https://openai.com/index/running-codex-safely/

Supabase requires RLS on exposed tables and recommends cookie-backed SSR auth;
its SSR helper remains beta. This phase therefore keeps Supabase optional and
defines SQL/RLS plus an adapter boundary without adding the SDK.

- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://supabase.com/docs/guides/auth/server-side
- https://supabase.com/docs/guides/deployment/shared-responsibility-model

OWASP multi-tenant guidance requires server-derived tenant context, composite
tenant/resource lookups, repository-layer authorization, opaque IDs, isolated
caches/sessions, rate limits, and audit evidence.

- https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html

## Threats And Controls

| Threat | Phase 6J control |
|---|---|
| IDOR/BOLA | Repository lookup always includes session tenant |
| Client-selected tenant | Reject tenant/user fields in mutation bodies |
| CSRF | Same-origin check plus session-bound CSRF header/cookie |
| Session theft | Opaque random cookie, server stores hash, httpOnly/SameSite |
| Session fixation | New session ID on sign-in; revoke on sign-out |
| Open redirect | Relative allowlist only |
| Cross-tenant cache | Tenant included in every storage/cache key |
| Lost update | Required expected version and explicit conflict |
| Secret leakage | No tokens/keys/cookies in JSON, logs, fixtures, or release |
| Fake hosted state | Supabase remains unavailable until live isolation proof |
| Brute-force/local abuse | Bounded process-local rate limiter |

## Non-Goals

- Password storage or custom password cryptography.
- Real payment collection, subscriptions, tax, or checkout.
- Hosted notification delivery or worker installation.
- Broker connectivity or autonomous action.
