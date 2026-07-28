import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const runLabel = sanitizeLabel(process.env.PHASE5T_LABEL || "final");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase5t_${runLabel}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

const routes = [
  { id: "home", url: "/?view=home&mode=cache", waitFor: ".market-terminal-cockpit" },
  { id: "btc-cache", url: "/?view=asset&symbol=BTCUSDT&assetClass=crypto&mode=cache", waitFor: '[data-product-view="asset-workspace"]' },
  { id: "btc-cache-miss-fallback", url: "/?view=asset&symbol=BTCUSDT&assetClass=crypto&mode=cache&range=6mo", waitFor: '[data-product-view="asset-workspace"]' },
  { id: "btc-live", url: "/?view=asset&symbol=BTCUSDT&assetClass=crypto&mode=live-if-available", waitFor: '[data-product-view="asset-workspace"]' },
  { id: "btc-fixture", url: "/?view=asset&symbol=BTCUSDT&assetClass=crypto&mode=fixture", waitFor: '[data-product-view="asset-workspace"]' },
  { id: "options", url: "/?view=options-quant&mode=cache&symbol=AAPL", waitFor: '[data-product-view="options-quant-workstation"]' },
  { id: "options-fixture", url: "/?view=options-quant&mode=fixture&symbol=AAPL", waitFor: '[data-product-view="options-quant-workstation"]' },
  { id: "news", url: "/?view=news&mode=cache", waitFor: '[data-product-view="news-workspace"]' },
  { id: "news-fixture", url: "/?view=news&mode=fixture", waitFor: '[data-product-view="news-workspace"]' },
  { id: "war-map", url: "/?view=war-room-map&mode=cache", waitFor: '[data-product-view="global-risk-map"]' },
  { id: "command", url: "/?view=command-workspace&mode=cache", waitFor: ".terminal-command-product" },
];

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const consoleErrors = [];
const pageErrors = [];
const results = [];

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(`${page.url()} :: ${message.text()}`);
  });
  page.on("pageerror", (error) => pageErrors.push(`${page.url()} :: ${error.message}`));

  for (const route of routes) {
    await page.goto(`${baseUrl}${route.url}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector(route.waitFor, { timeout: 180_000 });
    await page.waitForTimeout(450);
    const inspection = await inspect(page);
    const screenshotPath = path.join(outputDirectory, `${route.id}-desktop.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    const stats = await stat(screenshotPath);
    results.push({ ...route, ...inspection, screenshot: screenshotPath, screenshotBytes: stats.size });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${baseUrl}/?view=asset&symbol=BTCUSDT&assetClass=crypto&mode=cache`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 180_000 });
  await page.waitForTimeout(450);
  const mobileInspection = await inspect(page);
  const mobilePath = path.join(outputDirectory, "btc-cache-mobile.png");
  await page.screenshot({ path: mobilePath, fullPage: true });
  const mobileStats = await stat(mobilePath);
  results.push({
    id: "btc-cache-mobile",
    url: "/?view=asset&symbol=BTCUSDT&assetClass=crypto&mode=cache",
    ...mobileInspection,
    screenshot: mobilePath,
    screenshotBytes: mobileStats.size,
  });

  const mobileRoutes = [
    { id: "options-mobile", url: "/?view=options-quant&mode=cache&symbol=AAPL", waitFor: '[data-product-view="options-quant-workstation"]' },
    { id: "news-mobile", url: "/?view=news&mode=fixture", waitFor: '[data-product-view="news-workspace"]' },
  ];
  for (const route of mobileRoutes) {
    await page.goto(`${baseUrl}${route.url}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector(route.waitFor, { timeout: 180_000 });
    await page.waitForTimeout(450);
    const inspection = await inspect(page);
    const screenshotPath = path.join(outputDirectory, `${route.id}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const stats = await stat(screenshotPath);
    results.push({ ...route, ...inspection, screenshot: screenshotPath, screenshotBytes: stats.size });
  }

  const summary = {
    runLabel,
    baseUrl,
    outputDirectory,
    consoleErrorCount: consoleErrors.length,
    pageErrorCount: pageErrors.length,
    results,
    consoleErrors,
    pageErrors,
  };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));

  const btcCache = results.find((row) => row.id === "btc-cache");
  if (!btcCache || btcCache.chartRows <= 0 || btcCache.charts <= 0) {
    console.error("BTC cache route did not render chart rows.");
    process.exitCode = 1;
  }
  const btcFallback = results.find((row) => row.id === "btc-cache-miss-fallback");
  if (!btcFallback || btcFallback.chartRows <= 0 || btcFallback.charts <= 0 || !btcFallback.hasFixtureFallbackText || btcFallback.symbolState !== "cache-miss/fixture-fallback") {
    console.error("BTC cache-miss fixture fallback did not render with labeled chart rows.");
    process.exitCode = 1;
  }
  const options = results.find((row) => row.id === "options");
  if (!options || options.optionsPanels < 4 || options.hasContractDiagnosticsText) {
    console.error("Options route did not render a product-grade analytics workspace.");
    process.exitCode = 1;
  }
  const news = results.find((row) => row.id === "news");
  const newsHasStoriesOrHonestGap = news && (news.newsStoryRows > 0 || news.newsEmptyStates > 0);
  if (!news || !newsHasStoriesOrHonestGap || news.productNavLinks <= 0 || news.hasContractDiagnosticsText) {
    console.error("News route did not render a product-grade story/source workspace.");
    process.exitCode = 1;
  }
  const newsFixture = results.find((row) => row.id === "news-fixture");
  if (!newsFixture || newsFixture.newsStoryRows < 1 || newsFixture.newsClusters < 1 || newsFixture.hasContractDiagnosticsText) {
    console.error("News fixture route did not render story clusters and source context.");
    process.exitCode = 1;
  }
  const optionsMobile = results.find((row) => row.id === "options-mobile");
  if (!optionsMobile || optionsMobile.optionsPanels < 4 || optionsMobile.horizontalOverflow) {
    console.error("Options mobile route did not render responsive analytics panels.");
    process.exitCode = 1;
  }
  const newsMobile = results.find((row) => row.id === "news-mobile");
  if (!newsMobile || newsMobile.newsStoryRows < 1 || newsMobile.productNavLinks <= 0 || newsMobile.horizontalOverflow) {
    console.error("News mobile route did not render responsive story/source rows.");
    process.exitCode = 1;
  }
  if (consoleErrors.length || pageErrors.length) {
    process.exitCode = 1;
  }
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const text = document.body.innerText || "";
    const chartRows = Number(document.querySelector("[data-symbol-workstation-state]")?.getAttribute("data-chart-rows") || 0);
    const visible = (selector) => Array.from(document.querySelectorAll(selector)).filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 2 && rect.height > 2;
    }).length;
    return {
      title: document.title,
      h1: document.querySelector("h1")?.textContent?.trim() || "",
      h2: document.querySelector("h2")?.textContent?.trim() || "",
      productNavLinks: visible(".product-nav-link"),
      charts: visible("canvas, .finance-chart, .finance-chart-shell, .symbol-analysis-card, .chart-spec-card"),
      maps: visible(".leaflet-container, .leaflet-war-map, .war-map-canvas-fallback, [data-renderer='leaflet-war-map']"),
      optionsPanels: visible(".options-quant-workstation, .options-section, .options-card, .iv-surface, .options-overview-surface, [data-options-analytics-panels]"),
      newsRows: visible(".market-news-row, .news-row, .fusion-news-row, .cockpit-news-item, .symbol-news-compact-row, .news-workspace-row, .news-cluster-card, .news-source-row, .news-filter-chip"),
      newsStoryRows: visible(".news-workspace-row"),
      newsClusters: visible(".news-cluster-card"),
      newsSources: visible(".news-source-row"),
      newsEmptyStates: visible(".news-empty-state"),
      commandRows: visible(".command-result-card, .command-row, .terminal-command-card"),
      chartRows,
      symbolState: document.querySelector("[data-symbol-workstation-state]")?.getAttribute("data-symbol-workstation-state") || "",
      marketDataStatus: document.querySelector("[data-symbol-workstation-state]")?.getAttribute("data-market-data-status") || "",
      hasFixtureFallbackText: text.includes("fixture fallback") || text.includes("Deterministic fallback") || text.includes("phase5t.symbol_fixture_fallback"),
      hasNoPlottableText: text.includes("No plottable chart points"),
      hasContractDiagnosticsText: text.includes("Contract diagnostics"),
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
      bodyTextLength: text.length,
    };
  });
}

function sanitizeLabel(value) {
  return String(value).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 48) || "final";
}
