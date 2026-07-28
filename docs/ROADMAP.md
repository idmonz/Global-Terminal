# Global Terminal Canonical Roadmap

Updated: 2026-07-27

## Ultimate Goal

Build a commercially credible B2C market intelligence workstation that serious users want to open every day. It must combine:

- market discovery and heatmaps;
- equity, ETF, crypto, options, macro, commodity, and portfolio research;
- global event, map, news, and geopolitical intelligence;
- source-transparent quantitative calculations and reports;
- fast command navigation and configurable workspaces;
- honest live/cache/stale/proxy/unavailable data states.

The product is not a trading system. It does not place orders, approve trades, control brokerage accounts, or issue personalized investment instructions.

## Product Boundary

```text
Streamlit = internal lab and regression reference
lib/      = reusable provider, domain, quant, scoring, and report engines
FastAPI   = API boundary, optional locally and deployable later
Next.js   = commercial B2C web product
fixtures  = deterministic development/demo fallback
```

## Current State

Phase 1 through Phase 5E.3 produced a strong horizontal foundation:

- keyless/free-first providers and runtime cache;
- provider health, feed, and layer registries;
- JSON-safe `phase_2b.v1` envelopes;
- optional FastAPI getters/routes;
- deterministic fixtures;
- Next.js shell with 20 workspaces;
- Lightweight Charts and Leaflet foundations;
- market, equity, crypto, financial, options, screener, map/news/event, report, graph, provider, and command contracts;
- extensive Python and web regression tests.

Phase 5F audited the result and corrected release packaging. The engineering foundation is real, but the commercial product remains fixture-heavy and only partially reproduces Streamlit workflows. See:

- `docs/PHASE_5F_CURRENT_STATE_AUDIT.md`
- `docs/PHASE_5F_STREAMLIT_TO_WEB_PARITY_MATRIX.md`
- `docs/PHASE_5F_WEB_TERMINAL_PRODUCT_BLUEPRINT.md`
- `docs/PHASE_5F_IMPLEMENTATION_PLAN.md`

Phase 5G through Phase 5Y then converted important vertical journeys into product-first web surfaces and runtime operation:

- Market Home -> AAPL/BTCUSDT symbol intelligence with real chart renderers and honest runtime fallback;
- Market Home -> Global Risk Map -> event provenance/news/asset context with real USGS/news runtime rows, URL state, density handling, mobile layout, and map-renderer fallback.
- Market Home -> Market Map -> filter/rank/select/compare with 60 delayed public equity rows, documented metrics, URL state, and deterministic fixture fallback.
- AAPL/Product Nav -> Options Quant -> chain/IV/Greeks/exposure/scenario with delayed public provider rows, quality gates, assumption labels, URL state, and deterministic fallback.
- Product Nav -> Portfolio And Risk -> valuation/allocation/performance/drawdown/risk/correlation/factors/attribution/stress with delayed public histories, privacy gates, URL-safe view state, and deterministic fictional fallback.
- Product Nav -> Research Memory -> local-private notes/watchlists/reports/source history with sanitized export and origin return links.
- Global Search/Market Map/Watchlists -> Universal Symbol Workstation -> 90 bounded equity/ETF/crypto identities with provider capability, per-symbol cache/fixture isolation, and honest unsupported states.
- Universal Symbol Workstation -> Source-Backed Symbol Intelligence -> OHLCV/candlestick/volume, technical/risk/comparison panes, exact-title news, financial availability, crypto derivatives, and market-clock truth.
- Market Map -> Market Discovery -> saved local screens -> Symbol Workstation -> return with composable filters, four transparent rank models, factor attribution, and live/cache/fixture provenance.
- Global Risk Map -> Historical Risk Replay -> source-preserving local snapshots, two-window diffs, and inspected map replay visuals.
- Market Home -> Daily Brief -> claim ledger -> source drawer -> local capture/review with private notes excluded from URLs, fixtures, release, and optional AI inputs.
- Daily Brief -> source-bound chart panels -> clean-room research perspectives -> source drawer with inspected desktop/mobile visuals.
- Local Runtime -> one-command launcher -> FastAPI/Next production server -> visible Runtime API health chip with production visual proof.
- AAPL Symbol Workstation -> Alpha Vantage/Finnhub free-first financial/news breadth -> controlled online/offline screenshot matrix.

Phase 5Z through Phase 6O moved discovery onto 333 official-listing-matched
identities, materialized the compact Market Map read path, added SEC company
facts, activated exact provider-backed workstations, made delivery progressive,
completed a bounded five-symbol Watchlist research/change journey, and composed
exact chart, financial, catalyst, source, and saved-change evidence in one
synchronized analyst workspace, then added observed provider health, panel
freshness SLOs, and a bounded exact-workspace refresh queue. The web product is
no longer only a contract gallery. It is still incomplete: operations remain
process-local, map history and verified layers are shallow, and hosted
commercial identity and delivery are absent. Phase 6J/6K now provide an
honest process-local identity, tenant isolation, explicit account-owned research,
and a source-aware change inbox. Phase 6L adds a storage-independent repository,
bounded offline synchronization conformance, and versioned visual proof. Phase
6M now unifies saved Watchlist, catalyst, exact-news, Daily Brief,
provider-health, and War Map evidence into one source-aware daily review loop.
Phase 6N adds one explicit quota-aware source-backed observation run, atomic
snapshot/diff persistence, partial/LKG continuity, and a fully inspected
desktop/390px recovery/account/drilldown matrix. Phase 6O adds a transparent
tenant-safe Alert Manager, stored-observation evaluation, trigger history,
bounded opt-in local worker, and its own visual/performance/RLS evidence.
Hosted product repositories and automatically scheduled monitoring are still
not claimed.

## Current Verdict

- Architecture: sound.
- Data truth: generally strong.
- Release composition: reconciled.
- Web design language: promising.
- Daily user value: improving, but incomplete.
- Commercial readiness: not ready.

Do not call a phase complete merely because a contract, fixture, or route exists. Future completion requires a useful user journey, runtime/failure behavior, and inspected visual output.

## Canonical Product Views

1. Home / Daily Market
2. Market Map / Heatmap
3. Asset Symbol Workstation
4. Crypto Workstation
5. Options Quant
6. Screener
7. Portfolio And Risk
8. Global War Room
9. Reports And Research Memory
10. Terminal / Command Workspace

## Delivery Roadmap

### Phase 6A: Materialized Snapshot And Company Facts

Status: completed as a scoped product/platform slice on 2026-07-01.

- 137-row Market Map materializes outside the web request path;
- compact response is 746,784 bytes and warm local curl p50 is about 57 ms;
- atomic retention, single-flight refresh, last-known-good fallback, health, ETag,
  and 304 semantics are implemented;
- AAPL exposes 44 reviewed SEC facts and 8 final visual earnings rows;
- online/stale/offline desktop/mobile visual gates pass.

### Phase 6B: Broad Universe, Taxonomy, And Scheduled Refresh

Status: completed as a scoped product/platform slice on 2026-07-01.

- discovery expanded from 137 to 333 official-listing-matched rows;
- all 333 rows have source-aware sector classification, while only 60 have
  reviewed industry labels;
- one local/provider sector conflict remains explicit;
- snapshot response remains below 900 KB with detail sidecars;
- one-shot/loop scheduler, overlap protection and bounded refresh history exist;
- online/stale/offline visual and performance budgets pass.

### Phase 6C: Dynamic Broad-Symbol Workstation Activation

Status: completed as a scoped product/runtime slice on 2026-07-02.

- exact workstation activation increased from 60/333 to 333/333;
- runtime directory additively contains 363 equity/ETF/crypto identities;
- selected-symbol history, technical, financial, SEC, news, and source context
  use bounded capability plans and symbol-scoped cache/LKG;
- TSLA, JNJ, TTE, and TMUS pass exact non-AAPL desktop proof; TSLA passes mobile,
  SEC-facts, cache, failure, offline, and Market Map return proof;
- warm exact HTTP p50/p95 is approximately 181/250 ms;
- ETag 304, isolated 404, no broad rebuild, no cross-symbol fallback, full
  Python/web/build/audit, and visual gates pass.

### Phase 6D: Watchlist Desk And Materialized Workstation Delivery

Status: completed as a scoped daily-use product/runtime slice on 2026-07-02.

- named local-private CRUD, ordering, exact selection, and private reason
  exclusion are first-class web/API capabilities;
- bounded five-symbol materialization completed with 62 OHLCV rows each in one
  provider call and no broad-universe rebuild;
- summary/chart/financial/news/source routes preserve exact identity;
- Watchlist SSR is approximately 48 KB versus the 1.07 MB direct full
  workstation comparison;
- online/failure/network-blocked offline desktop/mobile visual gates pass.

### Phase 6E: Progressive Symbol Workstation And Advanced Watchlist

Status: completed as a scoped performance/daily-use slice on 2026-07-03.

- direct asset document fell from 1,071,676 to 56,112 bytes;
- compact summary plus chart-core/technicals/detail panel contracts preserve
  exact identity, OHLCV, provenance, ETag, and compatibility routes;
- warm AAPL useful chart is 753 ms; summary/chart-core p95 is 28.4/147.6 ms;
- same-origin runtime proxy removes stale public build-time API dependence;
- advanced Watchlist Price/Performance/Risk/Financial/Technical modes,
  temporary sorting, and grouping use existing cache with zero mode-change
  provider calls;
- desktop/mobile/unknown/blocked-network visual gates pass;
- unrelated ProductNav RSC prefetch is disabled.

### Phase 6F: Bounded Research Snapshot And Catalyst Monitor

Status: completed as a scoped daily research/catalyst slice on 2026-07-03.

- one five-symbol snapshot has a hard 16-call ceiling and reads provider cache
  before calls are spent;
- Alpha Vantage overview supplies fundamentals/dividend fields, Finnhub supplies
  earnings and strict company news, and yfinance supplies one batched history;
- saved Price/Performance/Risk/Financials/Technicals/Catalysts modes have zero
  request-time row fan-out;
- Watchlist -> exact TSLA Catalyst panel -> source clock -> stateful return is
  proven on desktop and mobile;
- 429 and blocked-runtime tests retain saved rows with explicit status;
- final AAPL summary p50/p95 is 28.64/35.15 ms, desktop/mobile useful charts are
  660/536 ms, and accessibility checks pass.

### Phase 6G: Research Snapshot Diff, Refresh Operations, And Alert Readiness

Status: completed as a scoped saved-change review slice on 2026-07-03.

- `research_snapshot_diff.v1` compares the latest two completed same-list
  snapshots with stable IDs, exact before/after evidence, and zero provider
  calls;
- the Watchlist Change Inbox filters price, performance, fundamental, event,
  exact-news, and source-state changes and preserves list/filter/change state
  through exact-symbol drilldown and return;
- refresh operations separate latest attempt from last success and expose
  overlap, budget, cache/LKG/failure counts, next eligibility, disabled
  background status, and kill-switch truth;
- opt-in change alerts remain local preview-only with dedupe, cooldown,
  acknowledgement, expiry, and kill-switch gates;
- five-symbol diff p95 is 0.95 ms, diff payload is 3.7 KB, initial HTML is
  78.6 KB, and saved inbox interaction makes zero provider calls;
- desktop/mobile, filtered-empty, exact drilldown/return, offline saved
  evidence, Phase 6E/6F regressions, and release gates pass.

### Phase 6H: Synchronized Analyst Workspace

Status: completed as a scoped composed-research slice on 2026-07-03.

- `analyst_workspace.v1` composes exact identity and progressive panel
  references without duplicating heavy rows;
- desktop renders chart plus financial, catalyst, and source panes; mobile
  fetches only the selected panel;
- exact symbol/timeframe synchronization, in-flight dedupe, ETag, same-symbol
  LKG, local layout save/reset, keyboard focus, and stateful Change Inbox return
  pass;
- initial HTML is 83.5 KB, manifest is 11.8 KB, chart-core p95 is 66.1 ms,
  hidden mobile requests and RSC prefetch are zero;
- live AAPL proof rendered 62 yfinance rows, source-aware financials, stale
  catalyst truth, and five provenance rows.

### Phase 6I: Live Research Operations And Freshness SLOs

Status: completed as a scoped local research-operations slice on 2026-07-04.

- `research_operations.v1` reconciles exact-panel observations with Runtime
  Health without promoting configured-only providers;
- exact refresh is capped at eight planned provider operations with
  idempotency, overlap protection, bounded history, no blind retry, and
  same-symbol LKG;
- retrieval and market/event clocks, last attempt, last success, and next safe
  retry remain separate;
- final operations read is 26.9 KB at 83.9 ms p95; cached chart-core is 22.9 ms
  p95 after removing duplicate observation writes;
- desktop/mobile, queued/running/partial, stale/LKG, rate-limit, overlap,
  offline/recovery, and Phase 6E/6F/6G/6H regression proof pass;
- the worker remains process-local and does not claim hosted scheduling,
  delivery, broker action, auth, billing, or tenant isolation.

### Phase 6J: Commercial Identity And Tenant-Safe Persistence

Status: completed as a scoped identity/isolation slice on 2026-07-10.

- anonymous/local use remains provider-call-free and fully usable;
- `identity_tenancy.v1` separates process-local test identity, tenant, role,
  entitlement, storage truth, offline state, and hosted unavailability;
- tenant-qualified storage, optimistic versions, bounded export/deletion,
  rotating sessions, CSRF, strict same-origin proxy, redirects, and rate limits
  are implemented;
- Account A save/restore/conflict/sign-out and Account B isolation pass in
  production Chrome and repository/HTTP tests;
- local preference p95 is 18.99 ms after closing SQLite connections and caching
  schema initialization; initial Analyst HTML remains 86.3 KB;
- optional Supabase SQL/RLS exists, but no hosted provider was configured or
  contacted and no hosted-success claim is made.

### Phase 6K: Tenant-Owned Research Desk And In-App Alert Inbox

Status: completed as a scoped local tenant-owned research journey on 2026-07-10.

- lazy account research preserves anonymous/local use and makes zero account
  calls until explicitly opened;
- bounded preview excludes private notes, requires selected-row consent, stores
  a receipt, deduplicates repeated import, and reports optimistic conflict;
- tenant-owned exact symbols open the existing Analyst Workspace with source,
  clocks, change evidence, and return context;
- opt-in saved-change rules create a deduplicated in-app inbox with cooldown,
  expiry, kill switch, review, acknowledge, retention, export, and cleanup;
- Account B sees empty collections and receives 404 for Account A opaque IDs;
- desktop/mobile/offline production Chrome, 973 Python tests, release gates,
  and all performance budgets pass;
- Supabase/RLS remains optional and unverified; external delivery, billing,
  broker action, and hosted workers remain unavailable.

### Phase 6L: Hosted Tenancy Proof And Account Research Sync

Status: local-conformance branch completed on 2026-07-10. The later 2026-07-14
Phase 6N hosted handoff established CLI linkage, account bootstrap, deployment,
and schema evidence; complete recovery proof is still not claimed.

- Phase 6K account routes now depend on a repository Protocol rather than the
  concrete SQLite class;
- SQLite, deterministic fake, and fail-closed Supabase sync adapters share a
  bounded `tenant_research_sync.v1` snapshot contract;
- explicit consent, 25-record/30KB bounds, idempotency, retry, cancellation,
  same/local-newer/remote-newer/conflict/deletion reconciliation, audit, and
  local outage continuity pass;
- Watchlist Desk's crushed 58px Research rail is now 10.5rem and measured at
  168px without overflow;
- the new Attention queue ranks unreviewed material changes and source
  degradation without adding push noise;
- Account A/B queue isolation, desktop/mobile screenshots, 25-record
  reconciliation p95 7.875ms, 76.6KB initial HTML, and zero sync provider calls
  pass;
- At Phase 6L close, Supabase CLI/Docker proof was absent. The Phase 6N hosted
  handoff later supplied linkage, backup, migration, schema, and
  password-authenticated observation RLS evidence, while recovery remains open.

### Phase 6M: Unified Attention Desk And Daily Review Loop

Status: completed local-first on 2026-07-13; historical Phase 6M hosted A/B
isolation is verified, but full persistence/recovery readiness and benchmark
parity are not claimed.

- composes Watchlist changes, catalysts, exact news, Daily Brief claims,
  provider degradation, and geopolitical transmission evidence into one
  source-aware attention feed;
- exposes meaningful changes since last review with severity, source health,
  watchlist, change-kind, and time filters;
- preserves exact drilldown and return state across Analyst Workspace, News,
  Daily Brief, and War Map;
- adds local/account review, acknowledge, snooze, checkpoint, conflict, audit,
  and policy controls without
  email/SMS/push or autonomous action;
- proves 1007 tests, zero triage-time provider calls, compose p95 41.776ms,
  80,155B initial HTML, 168px desktop navigation, 390px critical-first layout,
  A/B isolation, conflict/offline recovery, and versioned screenshots;
- provides historical basic Phase 6M tenant bootstrap/CRUD/A-B RLS evidence;
  the later Phase 6N handoff expands the hosted schema to 18 tables while full
  conflict, revocation, recovery, export/deletion, audit, and latency evidence
  remains open.

### Phase 6N: Source-Backed Observation Runs And Live Attention Materialization

Status: completed for the scoped local-first contract on 2026-07-14. Hosted
schema deployment and authenticated A/B observation database conformance are
complete. Recovery and production-adapter evidence remain open, so full hosted
persistence and benchmark parity are not claimed.

- one explicit five-symbol/16-operation bounded run now materializes fresh,
  cached, stale, partial, and unavailable saved observations separately from
  Attention triage;
- a controlled AAPL run completed from yfinance, Alpha Vantage, and Finnhub
  evidence; same-day replay and cache-only paths added zero calls;
- stable idempotency, cancellation, quota/session planning, exact source clocks,
  atomic valid-row persistence, partial ledgers, and LKG retention are present;
- Attention compose/filter/review/drilldown remains at zero provider calls;
- local p95 planning is 1.706ms, five-symbol persist/diff is 23.781ms,
  run-summary payload is 3,528B, and initial Attention HTML is 89,554B;
- the approved-machine handoff and independent verifier pass with 23 personally
  inspected screenshots, corrected 390px critical-first ordering, full
  failure/recovery/account/drilldown proof, visible focus/live region, zero
  overflow, zero unexpected browser errors, and zero provider calls;
- all 1,038 Python tests, Node/build/audit/runtime smoke, final external audit,
  and a secret-clean 1,749-entry release pass;
- hosted observation migration, RLS schema, least-privilege grants, anonymous
  denial, clean reset, local A/B isolation, and the secure password-authenticated
  hosted A/B matrix now pass; the recovery drill remains required.

### Phase 6N-V: Observation Journey Visual Closure

Status: completed on 2026-07-14.

- the production visual harness ran through the approved-machine handoff;
- progress/complete desktop, 390px critical-first, six recovery states,
  runtime offline, account A/B/conflict/local retention, exact
  News/Brief/Map/Analyst drilldown-return, and Phase 6H-6M regressions pass;
- `phase6n.visual.v1` is registered with 23 images and an independent verifier;
- release, benchmark, harness, and all-28 external audits were reconfirmed.

### Phase 6O: Watchlist Alert Rules And Scheduled In-App Monitoring

Status: completed for the scoped local-first product contract on 2026-07-15.

- `watchlist_alert_manager.v1` consolidates deterministic price, percent-move,
  material-change, and source-degradation rules with explicit schedules,
  lifecycle, cooldown/dedupe, clocks, trigger evidence, and bounded history;
- Rules, History, and Runs form a dense web product reachable from Watchlist
  and Attention, with exact Analyst/News/Brief/Map return;
- manager reads and manual stored-observation evaluation make zero provider
  calls; the bounded local worker is disabled until explicit opt-in;
- due-plan/evaluation/read p95 are 9.087/42.921/21.353ms, payload is 44,676B,
  and initial HTML is 44,984B;
- `phase6o.visual.v1` passes with 18 inspected desktop/mobile/state images,
  168px rail, first mobile trigger y=560, visible focus/live status, and zero
  overflow, unexpected errors, or provider requests;
- local actual PostgreSQL RLS and linked-project anonymous denial pass, and the
  Phase 6O migration is remote-aligned;
- password-authenticated Phase 6O hosted A/B now passes; hosted scheduling is
  still explicitly unavailable until a deployed scheduler is exercised;
- email/SMS/push/webhooks, broker action, opaque AI rules, and autonomous
  behavior remain unavailable.

### Phase 6P: Hosted Account Repository And Recovery Cutover

Status: completed for the scoped hosted account repository and recovery
cutover on 2026-07-16. Hosted recurring scheduling remains unverified and
disabled.

- execute and close the secure Phase 6O password-authenticated hosted A/B
  matrix before promoting any readiness flag;
- replace the hard-coded unavailable Supabase repository boundary with a
  user-session-scoped implementation for Watchlist, Attention, observations,
  and Alert Manager without exposing server credentials;
- preserve local-first continuity while proving sign-in, sign-out, new-session
  restore, optimistic conflict, idempotency, export/delete, Account B
  isolation, and generic failure behavior;
- add backup/restore and API/database outage-recovery evidence with no duplicate
  or lost audit rows;
- expose repository/SLO health honestly; configured keys alone remain
  unverified;
- defer hosted Cron and external notification delivery until the account data
  plane passes all Phase 6P security, recovery, visual, and release gates.

Observed implementation:

- server-derived Supabase identity now uses an opaque HttpOnly application
  session and never exposes Supabase tokens or accepts client tenant scope;
- a bounded RLS account document persists Watchlist, Attention, observation,
  and Alert Manager projections with optimistic versions, idempotency receipts,
  immutable audit, export/import/delete, and local-first queued recovery;
- local and linked migrations align through `20260715180000`; three account
  tables and two RPCs reject anonymous access;
- full Python, web build/audit, local performance, release security, six-image
  desktop/mobile visual, and 28-archive audits pass;
- Phase 6N hosted A/B, Phase 6O hosted Alert Manager A/B, and Phase 6P hosted
  document A/B pass. Hosted read p50/p95 is 188.366/286.160ms and idempotent
  RPC p50/p95 is 190.557/221.860ms over 10 network-inclusive samples with zero
  market-provider calls;
- the final two-repository owner run uses a real Supabase session and
  server-derived tenant, writes one hosted recovery marker, restores the exact
  marker into a fresh local repository, proves Account B isolation, deletes the
  marker, and reconciles cleanup. It completes in 17.845 seconds with zero
  sign-in retries, diagnostic calls, market-provider calls, or secret/identifier
  output;
- independent redacted-summary validation finds zero hits across 22 configured
  sensitive values. Phase 6P therefore closes, while hosted recurring jobs,
  external notification delivery, and production SLO claims remain unavailable.

### Phase 6Q: Hosted Observation Scheduler And Alert Operations Pilot

Status: local implementation and conformance completed; Account A/B hosted RLS
passed on 2026-07-28; real
hosted deployment evidence remains blocked, disabled, and unverified.

- choose one free-first hosted runner after an explicit deployment/security
  preflight; do not build multiple unused cloud paths;
- reuse the Phase 6N observation and Phase 6O Alert Manager engines for one
  bounded saved-Watchlist schedule;
- add atomic due claims, expiring leases, at-least-once invocation with
  idempotent effects, quota caps, kill switch, LKG/failure truth, and immutable
  operator audit;
- persist one actual tenant-qualified source-backed scheduled result through
  the Phase 6P account data plane and prove Account B isolation;
- expose compact last/next run, source, freshness, quota, and recovery truth in
  the existing Alert/Operations product surface;
- require a real hosted invocation, overlap/retry suppression, failure/recovery,
  visual proof, full gates, and safe unschedule/cleanup before setting
  `hosted_scheduler_verified=true`;
- keep email/SMS/push/webhooks, broker action, billing, recommendations, and
  autonomous financial actions unavailable.

Observed implementation:

- one `hosted_scheduler_operations.v1` contract now covers disabled/enabled/
  paused/killed state, timezone/DST due windows, atomic claim, expiring lease,
  heartbeat, bounded attempt, deterministic idempotency, source/quota clocks,
  LKG, audit, and cleanup;
- the selected private GitHub Actions worker restores the Phase 6P account
  document into a temporary repository and reuses the Phase 6N observation and
  Phase 6O alert engines; no second evaluator or browser service key exists;
- the additive migration passes local Supabase lint and real PostgreSQL
  transactional Account A/B RLS, overlap, replay, provider-failure/LKG, kill,
  lease recovery, audit, and cleanup conformance;
- Alert Manager exposes a compact Hosted schedule journey with explicit
  consent, next/last run, source, quota, LKG, pause/retry/kill/recover/delete,
  and persistent `hosted-unverified` truth;
- 24 desktop/mobile/state/regression screenshots pass an independent verifier;
  initial HTML is 49,002 bytes, scheduler read/compose p95 is 11.412ms over 200
  samples, and page/control paths make zero provider calls;
- both first-party workflows now use reviewed full commit SHA pins, and a
  secret-free/minimum-permission `Quality gate` runs the Python, web, fixture,
  release, and dependency audit commands once published; a first-party
  validator rejects mutable/unreviewed actions, write permissions,
  `pull_request_target`, missing timeouts, and quality-CI secret use;
- bounded weekly Dependabot policies cover GitHub Actions, npm, and pip; action
  changes require explicit pin-registry review rather than silent tag drift;
- the linked Supabase project is remote-aligned through the base scheduler and
  two schedule-recreation hardening migrations; anonymous reads/RPC execution
  are denied 5/5 and the read-only preflight reports
  `remote_migration_applied=true`;
- a catalog-resolved partial unique boundary fixes the lifecycle defect where
  one soft-deleted pilot schedule permanently blocked replacement; actual local
  PostgreSQL now proves create/delete/recreate/delete in one rollback-safe run;
- the owner-run user-JWT Account A/B hosted harness now proves distinct tenant
  scope, zero cross-tenant schedule/run/audit rows, forge denial, optimistic
  conflict, immutable audit, deleted-schedule replacement, exact account
  document restoration, unchanged operator controls, and zero provider calls;
  an independent freshness/privacy verifier accepts the redacted evidence;
- GitHub CLI 2.96.0 is installed, and a repeatable Git publish audit passes all
  1,834 candidate files with zero configured-value leaks, forbidden paths, or
  unreviewed token-pattern hits; the audit is part of the secret-free quality
  workflow;
- all 28 external ZIP fingerprints remain unchanged under the clean-room
  matrix: 51,305 files, 10,596,233 lines, 249,590 symbols, zero read errors;
- deployment is not ready: no Git commit/private remote/GitHub authentication,
  deployed default-branch quality/scheduler workflow, protected environment-
  secret evidence, or real job history exists. Do not close Phase 6Q or set the
  hosted verification flag until the deployed owner handoff passes.

### Phase 5F: Audit And Reconciliation

Status: completed as an audit/reconciliation phase on 2026-06-19. Python/web/release gates pass; the unresolved map nonblank visual gate is explicitly carried into Phase 5H.

Goals:

- reconcile documented and released architecture;
- quantify Streamlit-to-web parity;
- index and license-classify the refreshed external set;
- define product blueprint, design system, provider plan, and vertical roadmap.

### Phase 5G: Market Home To Symbol Intelligence

Status: completed as a vertical MVP slice on 2026-06-19.

Deliver one complete journey:

- useful market home;
- URL-backed equity and crypto symbols;
- live/cache/stale quote and chart paths;
- fundamentals/news/event/provider context;
- heatmap/screener click-through;
- desktop/mobile nonblank visual proof.

Observed result: Market Home, canonical AAPL/BTCUSDT routes, timeframe/surface persistence, real Lightweight Charts rendering, unknown-symbol protection, runtime fallback, chart fallback, responsive QA, harness tests, and release inclusion are present. Broad live symbol coverage and provider-backed interval/range remain open.

### Phase 5H: Global Map Intelligence

Status: completed as a usable MVP slice on 2026-06-20.

Deliver a map-first workflow with real USGS/news/weather layers, clustering, layer health, timeline/compare state, linked news/assets, and explicit unavailable premium/credentialed layers.

Observed result: `/?view=war-room-map` is a product-first map route; successful runtime smoke showed 29 source-backed markers, USGS provider coordinates, linked source/asset context, explicit OpenSky OAuth failure, URL-backed layers/timeline/event/compare state, density clustering above 60 rows, and inspected desktop/mobile/fallback captures. Historical compare overlays, broad weather overlays, AIS, valid OpenSky flight rows, sanctions, and durable map snapshots remain open.

### Phase 5I: Screener And Market Map

Status: completed as a usable MVP slice on 2026-06-20.

Deliver provider-backed universe filters, ranked results, hierarchical heatmap, comparison/scatter, and symbol drilldown.

Observed result: `/?view=market-map` now renders 60 live/cache yfinance instruments when the provider succeeds, with separate static taxonomy status, sector hierarchy, market-cap sizing, one-day return coloring, transparent ranking, risk/return scatter, ranked table, selected-instrument context, comparison state, and URL persistence. Desktop/mobile/fixture captures are nonblank and inspected. The universe is not an authoritative full S&P 500, the layout is not a squarified treemap, and only AAPL currently links to a verified equity workstation.

### Phase 5J: Options And Quant

Status: completed as a usable research MVP slice on 2026-06-21.

Deliver chain ingestion, quality checks, Greeks, IV surface, scenarios, and evidence-bound GEX research. Keep execution and recommendations out of scope.

Observed result: `/?view=options-quant` now uses the existing free yfinance path and project-native quant engines. Final live/cache evidence exposed 23 expiries, 267 accepted contract rows across the selected analysis window, 44 strikes in the selected expiry, 65 rendered IV points after interaction, 80 selected-expiry Greeks rows in the API snapshot, gated volatility-surface readiness, assumption-dependent gamma exposure, and 15 scenarios. Desktop/mobile/fixture visuals and URL state are verified. yfinance reliability/terms, missing bid/ask quote timestamps, European-model approximation, and explicit rate/dividend/multiplier/dealer-sign assumptions remain visible limits.

### Phase 5K: Portfolio And Risk

Status: completed as a strong privacy-safe research MVP on 2026-06-21.

Migrate holdings, performance, drawdown, factors, attribution, stress, correlation, and report capture from the Streamlit lab.

Observed result: `/?view=portfolio-risk` now provides seven fictional demo holdings, source-labeled delayed public valuation/history, 249 final live/cache complete observations, allocation, performance/drawdown, six-asset correlation, four public proxy factors, reconciled attribution, nine bounded stresses, URL-safe state, holdings-free guarded snapshot metadata, and inspected desktop/tablet/mobile/fallback output. Arbitrary private input, multi-currency FX, cash-flow IRR, licensed factors, tax lots and broker sync remain absent.

### Phase 5L: Research Memory

Status: completed as a local-first privacy-safe research workflow on 2026-06-22.

Deliver watchlists, alerts, reports, notes, source history, and local-first persistence.

Observed result: `/?view=research-memory&collection=demo-research&surface=inbox&mode=demo` now provides a product-first Inbox, Watchlists, Notes, Reports and immutable Sources ledger. Schema v4 adds bounded local-private memory CRUD and append-only source history over the existing SQLite/watchlist/report substrate. Search terms use POST bodies, period/model mismatches block comparison, workstation origins use opaque allow-listed IDs, and sanitized export removes titles, note bodies, symbols, holdings, attachments, account data and local paths. Deterministic demo, local first-run, desktop/tablet/mobile, source-history and origin-save captures were inspected. Hosted sync/auth, delivery alerts, external AI for private context, arbitrary attachment search and multi-user tenancy remain unavailable.

### Phase 5M: Universal Symbol Coverage

Status: completed as a strong multi-symbol workstation slice on 2026-06-22.

Turn the current AAPL/BTCUSDT product routes into a searchable, source-aware multi-symbol workstation with bounded free-first equity/ETF/crypto coverage, watchlist-to-symbol navigation, interval/range contracts, and honest unsupported-symbol states.

Observed result: 60 reviewed equities, 10 ETFs, and 20 crypto pairs are searchable. AAPL, MSFT, SPY, BTCUSDT, and ETHUSDT open isolated canonical workstations with yfinance/Binance runtime history or explicit fixture/cache/failure states. Interval/range controls, source truth, Market Map/watchlist/Research Memory drill-through, desktop/tablet/mobile captures, and intraday chart timestamp handling are verified. The registry remains bounded/static rather than authoritative, and deep technical, financial, exact-news, comparison, and derivatives panels remain open.

### Phase 5N: Source-Backed Symbol Intelligence Depth

Status: completed as a strong source-backed internal-beta slice on 2026-06-22.

Deepen the universal workstation with candlestick/volume/technical panes, source-backed financial availability and exact-symbol news, crypto funding/basis/open-interest context, comparison overlays, URL-safe panel state, and benchmark-grade visual evidence.

Observed result: asset routes now default to live-if-available and distinguish retrieval time from last market observation. AAPL/MSFT/SPY/BTCUSDT/ETHUSDT expose source-backed OHLCV, candlestick/line and volume, SMA/EMA, RSI, MACD, volatility/drawdown, aligned comparison, strict title-matched news, equity/ETF financial availability, and Binance funding/basis/open interest. A global table CSS leak that compressed the desktop plot to 288px was fixed; final 1600px evidence shows a 1,018px price plot inside a 1,096px chart shell. Desktop/full-page/tablet/mobile/fallback/unknown QA passed.

### Phase 5O: Market Discovery And Saved Screens

Status: completed as a strong source-aware internal-beta slice on 2026-06-22.

Observed result: the bounded Market Map now combines one batch market-history request and one batch Yahoo screener snapshot. Live evidence returned 60 market rows, 55 financial matches, 55 balanced/financial-coverage eligible rows, and 60 momentum/risk-adjusted eligible rows. Ten filters, four versioned rank models, contribution reconciliation, heatmap/table/scatter/factor views, local-private schema-v5 saved-screen CRUD, and stateful workstation return are implemented. Desktop/mobile/live captures passed with zero browser errors. Full-market membership, licensed fundamentals, streaming, arbitrary formulas, and hosted screen sync remain absent.

### Phase 5P: Historical Global Risk Replay And Map Layers

Status: completed as a strong internal-beta slice on 2026-06-22.

Observed result: schema-v6 local-private snapshots preserve project-captured markers, layers, providers, news, assets and source evidence. Content-addressed capture deduplicates identical normalized inputs, retention is explicit, and two-window diffs separate material changes from fetch-clock refreshes. The product route now combines timeline density, active/compare/truth clocks, five-domain diffs, added/changed/removed markers and source inspection. Desktop/tablet/mobile/fallback/local capture evidence is nonblank and error-free. Uncaptured history, AIS, verified flight, sanctions, hosted sync and commercial operations remain unavailable.

### Phase 5Q: Daily Briefing And Source-Bound Research Automation

Status: completed as a source-bound daily-use MVP on 2026-06-23.

Observed result: `/?view=daily-brief` now composes current market, map, news, provider, and local watchlist evidence into a claim-ledger-first daily brief. Every material claim references a source-register ID, missing or unverified provider coverage becomes a gap claim, and fetch-clock-only refreshes are separated from material claim changes. SQLite schema v7 adds append-only local-private brief captures with semantic deduplication, review status, retention metadata, and private review-note exclusion from API/fixture/release surfaces. The web route provides source drawer, changed-since-prior summary, local capture/review controls, deterministic fictional fixture fallback, and desktop/tablet/mobile screenshots. Optional Gemini remains public-sanitized and validator-bound rather than a private-context writer. Delivery scheduling, hosted sync, email/push, authoritative macro calendar breadth, and broad live source expansion remain absent.

### Phase 5R: Provider-Backed Daily Brief Depth And Chart Drilldowns

Status: completed as a focused Daily Brief depth slice on 2026-06-23.

Observed result: `/?view=daily-brief` now includes source-bound chart panels and clean-room research perspectives above the claim ledger. Three chart panels, three research-lens cards, 24 mini chart bars, 14 claims and 7 source rows rendered in final cache-mode visual evidence with no desktop/mobile overflow and zero browser errors. The contract validator now checks chart/perspective source and claim references. Deterministic fixture export is faster through an in-process masked-payload cache, and the prior conservative `sk-` false-positive fixture ID was removed. This is a useful cockpit improvement, but it is not full provider breadth: macro/rates/commodity/Korean-market depth and benchmark-grade multi-chart layouts remain future work.

The refreshed external set includes `TradingAgents-main.zip`. Phase 5R adopted only the analyst-role and evidence-review behavior clean-room as deterministic, non-advisory `research_perspectives`; trader, order, target, stop-loss, sizing, portfolio-manager approval and simulated-execution semantics remain rejected.

### Phase 5S: Whole-Product Feature Exposure

Status: completed as a visibility and navigation correction slice on 2026-06-23.

Observed result: the user critique was accepted as correct. The web product had strong engines and many vertical routes, but the first screen still hid too much of the Streamlit-era functionality. Phase 5S added a Market Terminal Cockpit to the home route, expanded product navigation to 12 visible destinations, routed data-heavy pages to `live-if-available` by default, reframed hard-coded `AAPL`/`BTCUSDT` nav labels as `Stock Market`/`Crypto Market`, and rebuilt Command Workspace as a product shell with launch cards, source boundaries, command result previews and no contract-diagnostics fallback. Final visual QA showed home with 24 chart surfaces, 30 heatmap tiles, 2 news/risk rows, 6 command rows, no overflow, and zero browser errors; Command Workspace showed 19 command rows and 17 source/boundary rows.

This is not full benchmark parity. BTCUSDT first-run cache charting, options visualization, dedicated news route depth, map/news/layer interaction density, and several Streamlit-to-web parity gaps remain open.

See:

- `docs/PHASE_5S_PRODUCT_EXPOSURE_REPORT.md`
- `docs/PHASE_5S_VISUAL_QA_REPORT.md`
- `docs/PHASE_5S_EXTERNAL_EVIDENCE_LEDGER.md`
- `docs/PHASE_5S_PROVIDER_KEY_READINESS.md`

### Phase 5T: Data-Depth And Interaction Bottleneck Closure

Status: completed as a focused bottleneck-closure phase on 2026-06-24.

Phase 5T was explicitly about visible product depth, not adding another hidden contract.

Observed Phase 5T-A result:

- BTC cache route visual QA: 35 chart surfaces and nonblank chart rows.
- BTC cache-miss fallback visual QA: 35 chart surfaces, 48 chart rows, `cache-miss/fixture-fallback`, `fixture`.
- BTC fixture route visual QA: 35 chart surfaces, 48 chart rows, `fixture`.
- Browser console errors: 0.
- Page errors: 0.
- Horizontal overflow: false.

Observed Phase 5T-B result:

- `/?view=options-quant&mode=cache&symbol=AAPL` now defaults to an analytics overview rather than a table-only chain surface.
- Options desktop and mobile show IV smile, Greeks strip, gamma exposure proxy and payoff/scenario grid with visible source/quality/assumption boundaries.
- `/?view=news&mode=cache` now renders a dedicated Source-Backed News Workspace rather than a generic contract viewer.
- News cache mode shows an explicit no-verified-news state when no public-feed rows are available.
- News fixture mode shows story/event cluster, selected row, source freshness, regional cards, impact matrix and timeline.
- Final visual QA covers home, BTC cache/live/fixture/fallback, Options cache/fixture/mobile, News cache/fixture/mobile, War Map and Command with zero console/page errors and no horizontal overflow.

See:

- `docs/PHASE_5T_BOTTLENECK_AUDIT.md`
- `docs/PHASE_5T_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5T_VISUAL_QA_REPORT.md`
- `docs/PHASE_5T_EXTERNAL_EVIDENCE_LEDGER.md`
- `docs/PHASE_5T_STREAMLIT_WEB_PARITY_TABLE.md`

Phase 5T does not complete benchmark parity. The next visible bottleneck is the War Map: the route has map surfaces, markers and source truth, but still does not match WorldMonitor/worldview-style first-viewport map/news/layer/source co-presence.

### Phase 5U: Map-First War Room Operations Desk

Status: completed as a visible War Map layout-depth slice on 2026-06-30.

Targeted the user's strongest remaining visible complaint: the map was real, but it was still pushed below replay controls and did not yet read as a WorldMonitor/worldview-like intelligence surface.

Observed result:

- `/?view=war-room-map` now renders a compact source boundary and compact replay toolbar before the map, then puts the Leaflet/fallback map, layer controls and event inspector ahead of the detailed replay timeline and diff strip.
- Final visual QA shows cache desktop map top at `391px` instead of the pre-5U `576px` baseline, and mobile map top at `550px` instead of the pre-5U `947px` baseline.
- Cache desktop evidence shows ready map state, 2 markers, 12 layer rows, 1 event inspector, 2 event rows, 1 related-reporting row and 7 market-transmission links with no overflow or browser/page errors.
- Fixture and fallback modes remain deterministic and explicitly labeled; no unavailable provider was promoted to live.
- The route is closer to WorldMonitor/worldview behavior, but live layer breadth and event density remain below benchmark.

See:

- `docs/PHASE_5U_BOTTLENECK_AUDIT.md`
- `docs/PHASE_5U_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5U_VISUAL_QA_REPORT.md`
- `docs/PHASE_5U_EXTERNAL_EVIDENCE_LEDGER.md`
- `docs/PHASE_5U_STREAMLIT_WEB_PARITY_TABLE.md`

### Phase 5V: Unified Symbol Intelligence Workstation

Status: completed as a visible symbol-workstation depth slice on 2026-06-30.

Targeted the user's remaining visible complaint that stock, crypto and intelligence tabs from the Streamlit lab still did not feel like a TradingView/OpenBB-grade commercial workstation.

Observed result:

- `/?view=asset` now renders a compact desk strip before the chart with source state, chart rows, compare overlap, exact-news count and financial/options or derivatives boundary.
- Runtime fallback diagnostics moved below the workstation so the first viewport is product-first rather than warning-first.
- Static catalog fallback now recomputes same-catalog comparison when a requested compare symbol exists, explicitly labeled as fixture/static rather than live.
- The right rail includes a compact source ledger; overview adds news/event links, comparison, source posture, equity options bridge, crypto derivatives card and ETF/fund boundary card.
- Equity `Options` is a real symbol surface that links into Options Quant without claiming OPRA-grade coverage or execution.
- Phase 5V visual QA passed for AAPL, MSFT, SPY, BTCUSDT, ETHUSDT, mobile AAPL/BTCUSDT, AAPL options surface and unknown symbol fallback.
- Cache/fixture visual evidence shows desktop chart top at `549px` and mobile chart top at `770px`, with 48 comparison overlap rows, source ledger, 6 context cards, no horizontal overflow and zero browser/page errors.
- With the optional FastAPI backend running on `127.0.0.1:8000`, `live-if-available` AAPL rendered cached/latest-session runtime data with 63 OHLCV rows, 63 SPY comparison overlap rows and 3 exact-symbol news rows.
- The route is closer to TradingView/OpenBB/Bloomberg-style symbol-workstation behavior, but full earnings/estimates/calendar depth, broader licensed fundamentals, richer watchlists and always-on runtime orchestration remain open.

See:

- `docs/PHASE_5V_PREFLIGHT_AND_BOTTLENECKS.md`
- `docs/PHASE_5V_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5V_VISUAL_QA_REPORT.md`

### Phase 5W: Local Runtime Orchestration And Live Provider Depth

Status: completed as a local runtime orchestration slice on 2026-06-30.

Targeted the next user-visible problem: the commercial web product becomes source-backed only when the optional FastAPI runtime is also running.

Observed result:

- `GET /api/runtime-health` now returns a JSON-safe `runtime_health` envelope with FastAPI availability, route count, provider count, launcher command, and caveats.
- The Next.js top bar now shows a compact `Runtime API` chip. In final production visual evidence it displayed `online`, `api-importable`, `37 routes / 250 providers`.
- `scripts/start_local_product.py` starts or reuses FastAPI and Next, waits for API/web readiness, supports production/dev/dry-run modes, and does not print secrets.
- Final production visual QA showed home and AAPL runtime chips online, AAPL chart state `ready`, 184 chart points, 35 canvas elements in direct probe, no horizontal overflow, and zero browser errors.
- War Map and BTCUSDT runtime marker checks returned HTTP 200 with runtime reachable markers.
- This phase did not broaden all providers. Earnings/calendar/SEC depth, verified AIS/flight/sanctions, richer macro/rates/commodity/Korean feeds, and hosted operations remain open.

See:

- `docs/PHASE_5W_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5W_LOCAL_RUNTIME_GUIDE.md`
- `docs/PHASE_5W_VISUAL_QA_REPORT.md`

### Phase 5X: Provider Breadth, Offline QA, And Daily-Use Depth

Status: completed as an equity provider-breadth and runtime-truth slice on 2026-06-30.

Targeted the next benchmark bottleneck: the local runtime was visible and launchable, but AAPL/equity Financials and News still lacked obvious free-first provider breadth and controlled offline/online screenshots.

Observed result:

- `lib/equity_provider_breadth.py` adds first-party Alpha Vantage and Finnhub adapters with TTL cache, stale fallback, missing-key, rate-limit and provider-error states.
- AAPL live smoke returned Alpha Vantage overview `live/fresh` with 16 normalized fields, Finnhub profile `live/fresh` with 8 fields, Alpha Vantage news `live/fresh` with 8 rows and Finnhub company news `live/fresh` with 8 rows.
- AAPL Financials now shows a first-viewport `Free provider breadth` panel beside core valuation rows; AAPL News merged 11 deduped company/news rows in final visual evidence.
- `apps/web/scripts/capture-phase5x.mjs` captures Home, AAPL Financials, AAPL News, BTCUSDT, unknown symbol, mobile Financials and an intentionally invalid API-base offline state.
- Online production visual QA passed on `127.0.0.1:3040`; offline visual QA passed on `127.0.0.1:3041` with `runtime-api-offline` and AAPL fallback chart readiness.
- Refreshed external inventory covers 28 archives, 51,305 files, 39,622 text candidates, 10,596,233 lines, 249,590 symbols and zero read errors.
- This phase did not solve WorldMonitor/worldview map depth, Finviz full-universe heatmap, earnings/calendar/SEC company facts or commercial hosted operations.

See:

- `docs/PHASE_5X_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5X_VISUAL_QA_REPORT.md`
- `docs/PHASE_5X_EXTERNAL_AUDIT_AND_BENCHMARK_REPORT.md`
- `docs/PHASE_5X_TEST_AND_RELEASE_REPORT.md`
- `docs/PHASE_5X_NEXT_GOAL_RATIONALE.md`

### Phase 5Y: WorldMonitor/worldview Map Intelligence Depth

Status: completed as a map/news/event intelligence slice on 2026-07-01.

Targeted the next benchmark bottleneck: the War Map existed and had source truth,
but event/news/asset interactions were too broad, shallow and slow.

Observed result:

- `map_news_event_fusion.v2` exposes per-marker event contexts, the complete
  deduplicated normalized news set, bounded match methods, direct graph edges,
  connected assets and explicit no-match states.
- Coordinate-derived broad regions are display context, not news-match evidence.
- The Next.js map adds a prioritized event rail, direct source/News actions,
  transmission paths and map-to-symbol return continuity.
- Map interaction preserves URL state locally and no longer refetches the full live
  provider set on every event click.
- Current map is the default; replay is entered only with an explicit snapshot time.
- Final online evidence showed 37 markers, 29 source-backed markers, 40 normalized
  news rows, ready desktop/mobile maps and zero browser errors.
- Controlled offline evidence showed runtime offline, source-backed 0, two
  fixture/proxy events and a still-usable map/news/AAPL journey.
- Cold runtime fusion remains slow, and verified AIS/flight/sanctions/broad weather
  coverage remains unavailable.

See:

- `docs/PHASE_5Y_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5Y_VISUAL_QA_REPORT.md`
- `docs/PHASE_5Y_EXTERNAL_AUDIT_AND_BENCHMARK_REPORT.md`
- `docs/PHASE_5Y_TEST_AND_RELEASE_REPORT.md`
- `docs/PHASE_5Y_NEXT_GOAL_RATIONALE.md`

### Phase 5Z: Authoritative Market Discovery And Heatmap Breadth

Status: completed as a source-authority, breadth, performance, and discovery slice
on 2026-07-01.

Observed result:

- online breadth increased from 60 to 137 official-listed rows using one broad Yahoo
  snapshot, official Nasdaq Trader listing identity, and the existing batched
  history boundary;
- listing, delayed observation, history/rank factors, and local taxonomy are separate
  evidence layers; no full-index membership is claimed;
- final observed taxonomy coverage is 60/137, with 77 rows explicitly unclassified;
- 14 filters, sector-to-industry drilldown, independent size/color controls,
  selected evidence, and URL-stable workstation return form a complete journey;
- online, cache, API-offline, desktop, mobile, encoding, hierarchy, supported, and
  unsupported captures pass with zero browser/page errors and no page overflow;
- cached local HTTP response is approximately 0.43-0.46 seconds for a 1.87 MB
  envelope after removing FastAPI recursive encoding overhead;
- no request-time per-symbol provider fan-out was introduced.

This remains below Finviz full-market depth and authoritative taxonomy. Synchronous
cold composition, payload size, background refresh, SEC company facts, and
earnings/calendar depth move to Phase 6A.

See:

- `docs/PHASE_5Z_EXTERNAL_AUDIT_AND_BENCHMARK_REPORT.md`
- `docs/PHASE_5Z_UNIVERSE_AND_TAXONOMY_CONTRACT.md`
- `docs/PHASE_5Z_IMPLEMENTATION_REPORT.md`
- `docs/PHASE_5Z_VISUAL_QA_REPORT.md`
- `docs/PHASE_5Z_TEST_AND_RELEASE_REPORT.md`
- `docs/PHASE_5Z_NEXT_GOAL_RATIONALE.md`

### Phase 6A: Materialized Market Snapshot And Company-Facts Depth

Status: completed on 2026-07-01. See `docs/PHASE_6A_IMPLEMENTATION_REPORT.md`.

- serve read-optimized stored market snapshots instead of composing broad providers
  synchronously for each cold request;
- add refresh-job health, duration, row-count, error, stale, and last-success state;
- split summary/map rows from on-demand detail and add conditional HTTP caching;
- add official SEC company facts with unit, period, form, filed-date, and provenance
  preservation;
- add provider-backed earnings/calendar availability or explicit unavailable state;
- retain online/stale/offline truth and the Market Map -> Symbol Workstation journey;
- prove performance, payload size, data truth, desktop/mobile visuals, and release
  gates.

### Later Commercial Platform Track

Add auth, billing, entitlements, hosted persistence, background refresh, alert delivery, observability, privacy controls, backups, and deployment SLOs.

See `docs/PHASE_5Q_COMMERCIAL_PLATFORM_READINESS.md` for the current system-design, frontend, API, storage, auth, hosting, CI/CD, security, rate-limit, cache/CDN, observability, testing, and scaling gap analysis.

## Design And Benchmark Policy

Every visual phase must:

1. inspect the current rendered desktop and mobile product;
2. select relevant official/product benchmarks;
3. state behavior to adopt and assets/code not to copy;
4. implement first-party or properly licensed components;
5. wait for charts/maps to render;
6. verify nonblank output, responsiveness, focus, errors, and data truth;
7. save screenshots and a mismatch report.

## External Reference Policy

- AGPL, NASA, missing-license, and unclear source: behavior-only.
- MIT/Apache source: direct adaptation only after exact-path and notice review.
- External datasets, models, fonts, images, and templates: separate rights review.
- `external.zip` is a duplicate container and is not double-counted.
- Full mechanical inventory is not equivalent to semantic review of every line.

## Definition Of Done

A product slice is complete only when:

- the user can finish the intended workflow;
- real/cache/stale/unavailable states are correct;
- deterministic fixtures are secret-safe;
- focused and broad regression tests pass;
- web test, lint, build, audit, and runtime smoke pass;
- desktop/mobile output is personally inspected;
- chart/map readiness and nonblank checks pass;
- license, security, provenance, and no-advice gates pass;
- release packaging still represents the documented architecture.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
