# Phase 6Q CI And Supply-Chain Preflight

Updated: 2026-07-27

## Evidence

- The repository is on branch `main` but has no first commit or remote.
- The only workflow is the bounded Phase 6Q scheduler. Its action references
  still use mutable major-version tags.
- No pull-request quality workflow or dependency update policy exists.
- The full local suite, web build, visual matrix, release hygiene, and local
  PostgreSQL conformance pass, so this is a deployment-hardening continuation
  rather than a product-regression repair.
- Supabase CLI 2.109.1 again failed the linked migration query with remote login
  role status 544 and a connection timeout.
- Chrome reached the intended Supabase project route but is signed out. No login
  form, password, OAuth grant, SQL mutation, or remote provider request was
  submitted.

## Official Baseline

GitHub recommends least-privilege `GITHUB_TOKEN` permissions and full-length
commit SHA pinning. Official release metadata checked on 2026-07-27 reports:

- `actions/checkout` v7.0.1 at
  `3d3c42e5aac5ba805825da76410c181273ba90b1`;
- `actions/setup-python` v7.0.0 at
  `5fda3b95a4ea91299a34e894583c3862153e4b97`;
- `actions/setup-node` v7.0.0 at
  `820762786026740c76f36085b0efc47a31fe5020`.

Sources:

- https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats
- https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- https://github.com/actions/checkout/releases/tag/v7.0.1
- https://github.com/actions/setup-python/releases/tag/v7.0.0
- https://github.com/actions/setup-node/releases/tag/v7.0.0

## Decision

Add one PR/main/manual quality workflow with two bounded parallel jobs. Python
runs the harness, compile, smoke, full tests, fixture export, release build, and
archive inspection. Web runs deterministic tests, lint, production build, and
high-severity dependency audit. It receives no Supabase, market-provider, or
account secrets and must not use `pull_request_target`.

Store reviewed action identities in a first-party pin registry and fail closed
when workflow `uses:` references do not match it. Add weekly, bounded dependency
updates, but require deliberate pin-registry review for action changes.

This reduces supply-chain and deployment risk. It cannot substitute for the
missing hosted migration, GitHub environment secrets, job history, or Phase 6Q
hosted handoff evidence.
