# Phase 6K Preflight And Threat Model

Updated: 2026-07-10

## Baseline

- Python 3.14.5, Node 24.16.0, npm 11.13.0.
- Full 962-test Python baseline passed with one existing TestClient deprecation
  and two existing cointegration collinearity warnings.
- Web fixture/runtime validation, ESLint, Next.js 16.2.9 production build, and
  npm high-severity audit passed; npm reported zero vulnerabilities.
- Baseline release contained 1,642 entries. Exact configured-value scan checked
  15 values and found zero hits and zero forbidden entries.
- Harness validator passed with six repository skills and one active Phase 6K
  plan.
- All 28 external archives were re-audited: 18 direct-use-allowed, 6
  behavior-only, 3 needs-review, and 1 blocked.
- Alpha Vantage, Finnhub, Gemini, and OpenSky credentials are present by name
  only. Supabase URL, anon key, and service-role key are absent.

## Existing Capability

Phase 6D-6I already supplies local watchlist CRUD, bounded materialization,
saved snapshot diffs, preview-only change alerts, exact Analyst Workspace
links, source clocks, and operations truth. Phase 6K will not duplicate those
engines. It adds an isolated tenant-owned storage/service boundary and a real
account journey above them.

## Official Guidance

- OpenAI harness engineering recommends repository-local plans, mechanically
  enforced architecture, depth-first user journeys, browser-legible evidence,
  and feeding failures into the harness:
  https://openai.com/index/harness-engineering/
- OpenAI's current orchestration guidance keeps tasks and durable state in a
  repository-visible control plane:
  https://openai.com/index/open-source-codex-orchestration-symphony/
- Supabase requires RLS on exposed-schema tables. Its SSR auth uses cookies and
  the `@supabase/ssr` helper remains beta:
  https://supabase.com/docs/guides/database/postgres/row-level-security
  https://supabase.com/docs/guides/auth/server-side
- Supabase local development requires a container runtime and must not be
  exposed publicly. No local or hosted Supabase stack is available here:
  https://supabase.com/docs/guides/local-development
- OWASP requires session-derived tenant context, composite tenant/resource
  lookups, repository authorization, per-tenant limits, and complete deletion:
  https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html
- State-changing cookie-authenticated requests require CSRF tokens and defense
  in depth such as Origin verification and SameSite cookies:
  https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- Non-blocking save/import/inbox feedback uses `role=status`; warnings use
  accessible error messaging without unnecessary focus theft:
  https://www.w3.org/WAI/WCAG22/Understanding/status-messages

## Clean-Room Adoption

- Finviz: adopt rapid list scanning and ranked information density only.
- OpenBB: adopt source-aware context and explicit widget/state boundaries only.
- Korean terminal reference: adopt change/evidence/review co-presence only.
- Supabase/Helix: architecture and behavior evidence only in this slice.
- OpenBB/WorldMonitor/OpenStock: behavior-only under the existing audit stance.
- No external source, image, font, dataset row, model, or trade dress is copied.

## Threats And Controls

| Threat | Phase 6K control |
|---|---|
| Automatic local-data upload | Preview is read-only; confirm requires explicit consent |
| Private-note disclosure | Import candidates omit watch reasons/private bodies by construction |
| Client-selected tenant | Session context is authoritative; identity fields are rejected |
| IDOR/BOLA | Every repository query uses tenant plus opaque resource ID |
| Import replay/duplication | Tenant-scoped idempotency receipt and source fingerprint |
| Lost update | Expected version and explicit 409 conflict |
| Cross-tenant inbox leak | Tenant-qualified rule, inbox, export, delete, and acknowledgement |
| Alert flood | Opt-in, kill switch, bounded scan, dedupe, cooldown, expiry |
| Forged mutation | Same-origin, CSRF, bounded JSON, session, rate limit |
| Fake delivery | External email/SMS/push/webhook remains unavailable |
| Secret/private release leak | Public sanitizer and exact-value ZIP inspection |

## Non-Goals

- Hosted Supabase success, email/SMS/push/webhook delivery, checkout, billing,
  collaboration, broker integration, or autonomous action.
