# Phase 5P Preflight Report

Updated: 2026-06-22

## Verdict

The Phase 5O baseline is green and Phase 5P is justified. The current War Map is a useful current-state map, but its timeline filters only the loaded rows and its compare selector changes URL state without reading captured historical observations or calculating diffs.

## Repository Boundary

- Authoritative product root: `Global Terminal`.
- The longer legacy sibling path contains only control metadata and is not the product source tree.
- Streamlit remains the internal lab; `lib/` is reusable domain/provider logic; FastAPI is the local API boundary; Next.js is the B2C product.
- No Git metadata, CI/CD, hosted auth, billing, managed database, distributed cache, or production observability service is present.

## Baseline Evidence

- Python compile: passed.
- Smoke imports: passed.
- Full Python regression: passed at 100 percent with one existing Starlette/httpx deprecation warning and two existing cointegration collinearity warnings.
- Web fixture/runtime test: passed, 25 fixtures.
- ESLint: passed.
- Next.js 16.2.9 production build: passed.
- npm high-severity audit: zero vulnerabilities.
- Release ZIP: 1,416 selected source files and 1,417 entries including the manifest.
- Existing War Map visual check: 8 rendered markers, 15 loaded tiles, 1,023x642 desktop map, 358x567 mobile map, nonblank fallback, zero browser console errors.

## Browser Path

The in-app browser bootstrap failed before navigation because required browser sandbox metadata was absent from this session. The repository's installed `playwright-core` and local Chrome path are the verified fallback for Phase 5P screenshots and interaction assertions.

## External Audit Baseline

- archives: 22;
- files: 45,996;
- text candidates: 35,193;
- counted text lines: 9,561,357;
- indexed symbols: 221,593;
- read errors: 0.

This is a mechanical inventory, not a claim that every line was manually understood. Exact paths used for timeline/map behavior receive a separate semantic and license review.

## Phase 5P Acceptance Gap

1. No project-captured historical map snapshot exists.
2. No append-only, deduplicated map snapshot persistence exists.
3. No deterministic event/layer/provider/news/asset diff exists.
4. No replay payload or snapshot API exists.
5. The current compare UI is schema-ready decoration rather than historical comparison.
6. URL state uses legacy `timeline`, `compare`, and `event` keys rather than bounded snapshot IDs.
7. Local-private historical state is not yet represented in the product or release boundary tests.

The implementation phase may proceed.
