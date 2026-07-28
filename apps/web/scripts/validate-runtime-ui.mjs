import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const pagePath = path.join(appRoot, "src", "app", "page.tsx");
const contractsPath = path.join(appRoot, "src", "lib", "contracts.ts");
const fixturesPath = path.join(appRoot, "src", "lib", "fixtures.ts");
const productRoutesPath = path.join(appRoot, "src", "lib", "product-routes.ts");
const cssPath = path.join(appRoot, "src", "app", "globals.css");
const leafletWarMapPath = path.join(appRoot, "src", "components", "LeafletWarMap.tsx");
const warMapReplayPath = path.join(appRoot, "src", "components", "WarMapReplayWorkspace.tsx");
const financeChartPath = path.join(appRoot, "src", "components", "FinanceChart.tsx");
const marketMapPath = path.join(appRoot, "src", "components", "MarketMapScreener.tsx");
const portfolioRiskPath = path.join(appRoot, "src", "components", "PortfolioRiskWorkstation.tsx");
const dailyBriefPath = path.join(appRoot, "src", "components", "DailyBriefWorkspace.tsx");
const symbolSearchPath = path.join(appRoot, "src", "components", "SymbolSearch.tsx");
const symbolWorkstationPath = path.join(appRoot, "src", "components", "SymbolWorkstation.tsx");
const progressiveSymbolWorkstationPath = path.join(appRoot, "src", "components", "ProgressiveSymbolWorkstation.tsx");
const analystWorkspacePath = path.join(appRoot, "src", "components", "AnalystWorkspace.tsx");
const accountWorkspacePath = path.join(appRoot, "src", "components", "AccountWorkspaceBar.tsx");
const tenantResearchDeskPath = path.join(appRoot, "src", "components", "TenantResearchDesk.tsx");
const accountProxyPath = path.join(appRoot, "src", "app", "api", "account", "[...path]", "route.ts");
const page = await readFile(pagePath, "utf8");
const contracts = await readFile(contractsPath, "utf8");
const fixtures = await readFile(fixturesPath, "utf8");
const productRoutes = await readFile(productRoutesPath, "utf8");
const css = await readFile(cssPath, "utf8");
const leafletWarMap = await readFile(leafletWarMapPath, "utf8");
const warMapReplay = await readFile(warMapReplayPath, "utf8");
const financeChart = await readFile(financeChartPath, "utf8");
const marketMap = await readFile(marketMapPath, "utf8");
const portfolioRisk = await readFile(portfolioRiskPath, "utf8");
const dailyBrief = await readFile(dailyBriefPath, "utf8");
const symbolSearch = await readFile(symbolSearchPath, "utf8");
const symbolWorkstation = await readFile(symbolWorkstationPath, "utf8");
const progressiveSymbolWorkstation = await readFile(progressiveSymbolWorkstationPath, "utf8");
const analystWorkspace = await readFile(analystWorkspacePath, "utf8");
const accountWorkspace = await readFile(accountWorkspacePath, "utf8");
const tenantResearchDesk = await readFile(tenantResearchDeskPath, "utf8");
const accountProxy = await readFile(accountProxyPath, "utf8");
const issues = [];

for (const required of [
  "loadRuntimeFixture",
  "function RuntimeModeBanner",
  "function RuntimeFallbackNotice",
  "Runtime mode:",
  "RuntimeHealthChip",
  "data-runtime-health-state",
  "function ChartAxes",
  "function paddedDomain",
  "preserveAspectRatio=\"none\"",
  "LeafletWarMap",
  "FinanceChart",
  "MarketHeatmapBoard",
  "data-renderer=\"clean-room-market-heatmap\"",
  "MapNewsEventFusionWorkspace",
  "map-fusion-view",
  "FinancialFundamentalsWorkspace",
  "OptionsQuantWorkspace",
  "ScreenerDrilldownWorkspace",
  "MarketProductHome",
  "MarketTerminalCockpit",
  "CommandLaunchpad",
  "ProgressiveSymbolWorkstation",
  "SymbolSearch",
  "SymbolWorkstation",
  "UnknownSymbolWorkspace",
  'data-product-view="market-home"',
  'data-product-view="asset-workspace"',
  'data-product-view="command-workspace"',
  'data-product-view="global-risk-map"',
  "function GlobalRiskMapProduct",
  "function MarketMapProduct",
  'data-product-view="market-map-screener"',
  'data-product-view="portfolio-risk-workstation"',
  "function PortfolioRiskProduct",
  'data-product-view="daily-brief-workstation"',
  "DailyBriefWorkspace",
]) {
  if (!page.includes(required)) {
    issues.push(`page.tsx missing runtime/chart marker: ${required}`);
  }
}

for (const required of [
  'data-phase6k-tenant-research="true"',
  "Account research",
  "Preview local import",
  "Confirm import",
  "External delivery unavailable",
  'const ACCOUNT_RESEARCH_DESK_API = "/api/account/research-desk"',
  'credentials: "same-origin"',
  'readCookie("gt_csrf")',
  'aria-live="polite"',
]) {
  if (!tenantResearchDesk.includes(required)) {
    issues.push(`TenantResearchDesk.tsx missing Phase 6K marker: ${required}`);
  }
}

for (const required of [
  'data-phase6i-research-operations="true"',
  "Refresh exact workspace",
  "/api/analyst-workspace/",
  "/operations?",
  "/refresh",
  "/api/research-operations/jobs/",
  'aria-live="polite"',
  "last-success",
  "next-safe-retry",
]) {
  if (!analystWorkspace.includes(required)) {
    issues.push(`AnalystWorkspace.tsx missing Phase 6I marker: ${required}`);
  }
}

for (const required of [
  'data-phase6j-account-workspace="true"',
  'data-account-status={accountStatus}',
  "Local layout is never uploaded automatically.",
  "Use local test identity",
  "Save account layout",
  "Restore saved",
  'role="status"',
  'credentials: "same-origin"',
  'readCookie("gt_csrf")',
]) {
  if (!accountWorkspace.includes(required)) {
    issues.push(`AccountWorkspaceBar.tsx missing Phase 6J marker: ${required}`);
  }
}

for (const required of [
  'export const dynamic = "force-dynamic"',
  "const MAX_BODY_BYTES = 16_384",
  "function allowedPath",
  "function sameOrigin",
  'joined.includes("..")',
  'request.headers.get("x-csrf-token")',
  '"Cache-Control": "no-store"',
  '"X-Content-Type-Options": "nosniff"',
  'error: "account-api-offline"',
]) {
  if (!accountProxy.includes(required)) {
    issues.push(`account proxy missing Phase 6J security marker: ${required}`);
  }
}

for (const required of [
  "type RuntimeMode = \"fixture\" | \"cache\" | \"live-if-available\"",
  "export const RUNTIME_MODES",
  "function normalizeRuntimeMode",
]) {
  if (!contracts.includes(required)) {
    issues.push(`contracts.ts missing runtime marker: ${required}`);
  }
}

for (const required of [
  "export async function loadRuntimeFixture",
  "GLOBAL_TERMINAL_API_BASE_URL",
  "include_runtime",
  "runtime-fallback",
  "RuntimeRequestContext",
  "loadRuntimeHealth",
  "/api/runtime-health",
  "SYMBOL_RUNTIME_KEYS",
  "daily-brief",
  "loadCompactSymbolSummary",
  "delivery",
]) {
  if (!fixtures.includes(required)) {
    issues.push(`fixtures.ts missing runtime loader marker: ${required}`);
  }
}

for (const required of [
  "resolveProductAssetContext",
  "canonicalAssetHref",
  'view: "asset"',
  "const EQUITY_SYMBOLS",
  "const ETF_SYMBOLS",
  "const CRYPTO_SYMBOLS",
  'fixtureKey: "symbol-workstation"',
  "interval",
  "range",
  "isRuntimeEligibleSymbol",
  'reason: supported ? null : "invalid-or-unsupported-symbol"',
]) {
  if (!productRoutes.includes(required)) {
    issues.push(`product-routes.ts missing product route marker: ${required}`);
  }
}

for (const required of [
  ".runtime-banner",
  ".runtime-banner-status",
  ".runtime-warning",
  ".runtime-health-chip",
  ".native-chart .chart-gridline",
  ".native-chart .chart-axis",
  ".native-chart .chart-zero",
  ".native-chart .chart-axis-label",
  ".finance-chart-shell",
  ".finance-chart-container",
  ".finance-chart-attribution",
  ".native-chart-fallback",
  ".market-heatmap-workspace",
  ".market-heatmap-board",
  ".market-heatmap-tile",
  ".heatmap-drilldown-link",
  ".map-fusion-view",
  ".fusion-heatmap-grid",
  ".fusion-news-stack",
  ".fundamentals-workstation",
  ".options-quant-workstation",
  ".screener-drilldown-workstation",
  ".drilldown-grid",
  ".product-workspace-grid",
  ".market-home-header",
  ".market-terminal-cockpit",
  ".cockpit-launch-grid",
  ".terminal-command-product",
  ".command-launchpad",
  ".terminal-command-card",
  ".asset-workspace-header",
  ".unknown-symbol-state",
  ".global-risk-map-product",
  ".global-map-stage",
  ".global-event-inspector",
  ".market-map-product",
  ".market-map-heatmap",
  ".market-map-ranked-table",
  ".portfolio-product",
  ".portfolio-performance-chart",
  ".portfolio-correlation-grid",
  ".portfolio-table",
  ".daily-brief-workstation",
  ".daily-claim-ledger",
  ".daily-source-drawer",
  ".symbol-search",
  ".symbol-workstation",
  ".symbol-primary-grid",
  ".progressive-symbol-workstation",
  ".progressive-panel-tabs",
  ".watchlist-advanced-toolbar",
  ".account-workspace-bar",
  ".account-sync-status.status-conflict",
]) {
  if (!css.includes(required)) {
    issues.push(`globals.css missing runtime/chart style: ${required}`);
  }
}

for (const required of [
  '"use client"',
  'data-phase6e-progressive-workstation="true"',
  'data-runtime-boundary="same-origin"',
  '"chart-core"',
  '"technicals"',
  "FinanceChart",
]) {
  if (!progressiveSymbolWorkstation.includes(required)) {
    issues.push(`ProgressiveSymbolWorkstation.tsx missing Phase 6E marker: ${required}`);
  }
}

for (const required of [
  '"use client"',
  'data-symbol-search-state="ready"',
  "canonicalAssetHref",
  'role="combobox"',
]) {
  if (!symbolSearch.includes(required)) {
    issues.push(`SymbolSearch.tsx missing product marker: ${required}`);
  }
}

for (const required of [
  'data-symbol-workstation-state={status}',
  "FinanceChart",
  "effective_interval",
  "source_register",
  "Save research snapshot",
]) {
  if (!symbolWorkstation.includes(required)) {
    issues.push(`SymbolWorkstation.tsx missing product marker: ${required}`);
  }
}


for (const required of [
  '"use client"',
  'import("leaflet")',
  'data-renderer="leaflet-war-map"',
  'leaflet.tileLayer',
  'bindPopup',
  'useSearchParams',
  'params.set("timeline"',
  'snapshotReplay ? "selected" : "event"',
  'data-map-state={mapState}',
  'toggleLayer',
]) {
  if (!leafletWarMap.includes(required)) {
    issues.push(`LeafletWarMap.tsx missing interactive map marker: ${required}`);
  }
}

for (const required of [
  '"use client"',
  'import("lightweight-charts")',
  'createChart',
  'LineSeries',
  'HistogramSeries',
  'data-renderer="lightweight-finance-chart"',
  'Charts by TradingView',
  'ResizeObserver',
  'data-chart-state={status}',
  'data-chart-points=',
]) {
  if (!financeChart.includes(required)) {
    issues.push(`FinanceChart.tsx missing finance chart marker: ${required}`);
  }
}
if (page.includes("\\n") || page.includes("`n") || css.includes("\\n") || css.includes("`n") || contracts.includes("\\n") || fixtures.includes("\\n") || financeChart.includes("\\n") || financeChart.includes("`n") || dailyBrief.includes("\\n") || dailyBrief.includes("`n")) {
  issues.push("source contains literal newline escape tokens from generated edits");
}

for (const required of [
  'data-replay-state={state}',
  'Capture observation',
  '/api/war-room-map-snapshots',
  '/api/war-room-map-replay',
  'compareTo',
  'historical_truth',
  'decorateMarkers',
]) {
  if (!warMapReplay.includes(required)) {
    issues.push(`WarMapReplayWorkspace.tsx missing replay marker: ${required}`);
  }
}

for (const required of [
  '"use client"',
  'data-portfolio-state="ready"',
  'params.set("surface"',
  'params.set("period"',
  'params.set("benchmark"',
  "portfolio-performance-chart",
  "portfolio-correlation-grid",
  "portfolio-table",
  "No external AI transmission",
]) {
  if (!portfolioRisk.includes(required)) {
    issues.push(`PortfolioRiskWorkstation.tsx missing product marker: ${required}`);
  }
}

for (const required of [
  '"use client"',
  'data-daily-brief-state={displayState}',
  'data-claim-count={claims.length}',
  'data-source-drawer={selectedClaim ? "open" : "closed"}',
  '/api/daily-brief/captures',
  'Mark reviewed',
  'Claim ledger first',
]) {
  if (!dailyBrief.includes(required)) {
    issues.push(`DailyBriefWorkspace.tsx missing product marker: ${required}`);
  }
}

for (const required of [
  '"use client"',
  'data-market-map-state="ready"',
  "Composable discovery filters",
  "Saved Screens",
  "Factor Attribution Matrix",
  "market-map-model-strip",
  "market-map-heatmap",
  "market-map-scatter",
  "market-map-ranked-table",
]) {
  if (!marketMap.includes(required)) {
    issues.push(`MarketMapScreener.tsx missing product marker: ${required}`);
  }
}

if (issues.length > 0) {
  console.error("Runtime UI validation failed");
  for (const issue of issues) {
    console.error(`- ${issue}`);
  }
  process.exit(1);
}

console.log("Validated runtime mode boundary, optional runtime loader, finance chart renderer, and native chart fallback markers");
