# Phase 5Z Preflight And Bottleneck Report

Updated: 2026-07-01

## Objective

Deliver a complete daily-use discovery journey:

```text
Market Map
-> universe and source truth
-> sector/industry hierarchy, filter and rank
-> selected symbol evidence
-> supported Symbol Workstation
-> return with Market Map state preserved
```

The slice must improve real discovery breadth. A larger fixture, a cosmetic heatmap,
or an unverified symbol list does not satisfy Phase 5Z.

## Baseline Gates

Before product edits:

- collected tests: 847 across 437 test files;
- full `pytest -q -x`: passed;
- existing warnings: one Starlette/httpx TestClient deprecation and two
  cointegration collinearity warnings;
- web fixture/runtime validation: passed, 27 fixtures;
- ESLint: passed;
- Next.js production build: passed;
- npm high-severity audit: zero vulnerabilities;
- baseline release ZIP: 1,498 entries, approximately 4.19 MB;
- forbidden release entries: zero;
- web and backend sources: present.

## Current Market Map Baseline

Observed production route:

`/?view=market-map&mode=live-if-available`

Contract/API observation:

- runtime instruments: 60;
- ranked rows: 60;
- balanced-model financial coverage: 54;
- sectors: 10;
- response size: approximately 0.99 MB;
- uncached `period=6mo` API request: 4,178 ms;
- immediately repeated cached request: 1,105 ms.

Visual observation:

- default live heatmap displayed 54 rows because the balanced model silently removed
  ineligible rows;
- ten filters and four rank models were present;
- selected evidence and source status were present;
- desktop and mobile had no horizontal overflow;
- symbol-workstation return state worked;
- browser console and page errors were zero.

Baseline evidence:

`review_workspace/phase5o_visual/`

## External And Official Evidence

The Phase 5Z archive inventory completed successfully:

- archives: 28;
- entries: 51,305;
- indexed non-vendored text files: 38,623;
- indexed lines: 8,742,912;
- skipped vendored text files: 556;
- skipped oversized text files: 38.

The inventory is mechanical evidence, not semantic or legal approval.

Scoped license findings:

- OpenStock and OpenBB: AGPL-3.0, behavior only;
- yfinance: Apache-2.0, existing dependency boundary only;
- FinanceDatabase, ai-website-cloner-template and superloopy: MIT;
- no external source, symbol rows, taxonomy rows, screenshots or visual assets will
  be copied.

Current official source probes:

- Nasdaq Trader `nasdaqlisted.txt`: HTTP 200, approximately 343 KB;
- Nasdaq Trader `otherlisted.txt`: HTTP 200, approximately 526 KB;
- SEC company ticker JSON: HTTP 403 in this environment, therefore unavailable and
  not usable as live evidence.

Nasdaq Trader exposes current-day listing identity, test-issue, ETF, financial-status
and file-creation fields. It does not provide sector/industry taxonomy or index
membership. Those dimensions must remain independently sourced and labeled.

## Primary Product Bottlenecks

1. The 60-row local list is presented alongside live observations without an
   authoritative listing identity contract.
2. Local sector/industry metadata is reference/static, not current index membership.
3. The default rank model hides six observation rows instead of showing their
   ineligibility reason.
4. There is no sector -> industry drilldown state.
5. Heatmap size and color metrics are fixed.
6. Current CSS partitioning is useful but does not expose broad listing coverage,
   unclassified taxonomy or dynamic legend semantics.
7. Market-map selection and filters still use Next router replacement and can cause
   unnecessary server work.
8. Broadening history with per-symbol calls would create an unacceptable N+1 path.

## Phase 5Z Implementation Decision

Build a first-party, clean-room contract that separates three truths:

- official listing directory identity from Nasdaq Trader;
- delayed public market observations from one Yahoo screener batch plus existing
  batched history;
- local reviewed sector/industry taxonomy with explicit reference/static status.

Use the broad Yahoo snapshot for market-cap, price, one-day change and liquidity
heatmap coverage. Enrich the existing 60 rows with historical/rank factors. Preserve
all broad rows and show rank eligibility rather than removing them.

## Performance Budgets

- no per-symbol provider requests in the Market Map request path;
- at most one Nasdaq-listed fetch, one other-listed fetch, one Yahoo screener fetch
  and one existing batch-history fetch per cold composition;
- listing and Yahoo snapshots must use TTL/stale cache and single-flight behavior;
- cache-mode interaction must not request live providers;
- filter, hierarchy, size/color metric and selection changes must remain client-side;
- target cached API response below 1.5 seconds in the local environment;
- no horizontal overflow at 1600px and 390px;
- no browser console or page errors.

## Acceptance Evidence Required

- parser/cache/provenance and missing-value tests;
- broad heatmap row count greater than the old 60-row ceiling when provider succeeds;
- official listing coverage and local taxonomy coverage displayed separately;
- sector/industry and size/color state in the URL;
- supported symbol round trip without AAPL leakage;
- online, cache and API-invalid desktop/mobile screenshots;
- full Python/web/security/release gates.

## Final Reconciliation

The scoped implementation resolved the identified product bottlenecks:

- visible online breadth increased from 60 to 137 official-listed rows;
- all broad rows remain visible by default while rank ineligibility is explicit;
- official listing and local taxonomy authority are separated;
- sector-to-industry hierarchy and independent size/color controls are implemented;
- filter and selection changes use local URL state without provider reload;
- provider requests remain batched with no per-symbol request fan-out.

The first repeated API measurement with PowerShell showed 2.66 seconds because
PowerShell's response handling and FastAPI recursive encoding dominated the large
payload. Profiling showed cached contract composition at approximately 0.25-0.40
seconds. Returning the already JSON-safe envelope through one compact JSON response
reduced measured local `curl` delivery to approximately 0.43-0.46 seconds, meeting
the preflight cached-response budget.

The remaining 1.87 MB payload and fresh-process cold composition are carried into
Phase 6A materialization and summary/detail separation.
