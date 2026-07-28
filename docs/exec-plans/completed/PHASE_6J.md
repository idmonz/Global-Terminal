# Phase 6J Execution Plan

Updated: 2026-07-10
Status: completed

## Objective

Deliver one honest account-owned Analyst Workspace preference journey while
preserving anonymous/local use and proving cross-tenant isolation.

## Scope

1. Agent harness upgrade and threat model.
2. Identity/session/entitlement contracts.
3. Tenant-scoped preference repository and adapter boundary.
4. FastAPI auth/account routes and same-origin Next proxy.
5. Compact Analyst Workspace account/sync surface.
6. Security, performance, visual, regression, and release evidence.

## Acceptance

- Anonymous mode makes no auth-provider call and stays useful.
- Local test identity is explicitly process-local, never hosted.
- Server derives tenant identity from the session.
- Account A cannot read, update, delete, or export Account B data.
- Writes require CSRF and expected version.
- Sign-out revokes the session and returns to local mode.
- Provider outage retains local layout without claiming sync.
- Supabase remains unavailable until configured and live-tested.
- No checkout, payment, broker, or autonomous action exists.

## Progress

- [x] Phase 6I and durable goal read.
- [x] Six repository skills and root/web harness read.
- [x] Official OpenAI, Supabase, and OWASP guidance reviewed.
- [x] Baseline Python/web/release gates passed.
- [x] External audit rerun for all 28 archives.
- [x] Failing contract/security tests captured before implementation.
- [x] Backend and storage implementation.
- [x] Web account journey implemented and build-verified.
- [x] Visual/performance proof and prior-phase browser regressions.
- [x] Reports and Phase 6K next goal selected from evidence.

## Decisions

- No Supabase SDK in domain code.
- Use a deterministic local test identity adapter only when explicitly enabled.
- Store only hashes of opaque process-local session identifiers.
- Keep local browser layout independent from account sync until explicit save.
- Real hosted authentication is not claimed in this phase.

## Verification

- Focused Phase 6J/security/storage tests passed.
- Full Python suite passed after updating the value-free environment allowlist.
- Compileall, import smoke, 32-fixture export, harness validator, web test,
  ESLint, Next production build, and npm audit passed.
- Production Chrome Phase 6J account/isolation/offline/security suite passed.
- Production Chrome Phase 6H and Phase 6I regressions passed.
- All Phase 6J performance budgets passed.
- Release security inspection found zero forbidden entries and zero exact
  configured-value occurrences.
