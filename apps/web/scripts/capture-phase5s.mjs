import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const runLabel = sanitizeLabel(process.env.PHASE5S_LABEL || "final");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase5s_${runLabel}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

const routes = [
  { id: "home", url: "/?view=home&mode=cache", waitFor: ".market-terminal-cockpit, .market-product-home" },
  { id: "market-map", url: "/?view=market-map&mode=cache", waitFor: '[data-product-view="market-map-screener"]' },
  { id: "aapl-asset", url: "/?view=asset&symbol=AAPL&assetClass=equity&mode=cache", waitFor: '[data-product-view="asset-workspace"]' },
  { id: "btc-asset", url: "/?view=asset&symbol=BTCUSDT&assetClass=crypto&mode=cache", waitFor: '[data-product-view="asset-workspace"]' },
  { id: "options", url: "/?view=options-quant&mode=cache&symbol=AAPL", waitFor: '[data-product-view="options-quant-workstation"]' },
  { id: "war-map", url: "/?view=war-room-map&mode=cache", waitFor: '[data-product-view="global-risk-map"]' },
  { id: "daily-brief", url: "/?view=daily-brief&mode=cache&period=morning", waitFor: '[data-product-view="daily-brief-workstation"]' },
  { id: "research-memory", url: "/?view=research-memory&mode=demo", waitFor: '[data-product-view="research-memory-workstation"]' },
  { id: "command", url: "/?view=command-workspace&mode=cache", waitFor: ".command-workspace-view, .terminal-command-product" },
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
    await page.waitForTimeout(350);
    const inspection = await inspect(page);
    const screenshotPath = path.join(outputDirectory, `${route.id}-desktop.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    const stats = await stat(screenshotPath);
    results.push({ ...route, ...inspection, screenshot: screenshotPath, screenshotBytes: stats.size });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${baseUrl}/?view=home&mode=cache`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.waitForSelector(".market-terminal-cockpit, .market-product-home", { timeout: 180_000 });
  await page.waitForTimeout(350);
  const mobileInspection = await inspect(page);
  const mobilePath = path.join(outputDirectory, "home-mobile.png");
  await page.screenshot({ path: mobilePath, fullPage: true });
  const mobileStats = await stat(mobilePath);
  results.push({
    id: "home-mobile",
    url: "/?view=home&mode=cache",
    ...mobileInspection,
    screenshot: mobilePath,
    screenshotBytes: mobileStats.size,
  });

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
    const visible = (selector) => Array.from(document.querySelectorAll(selector)).filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 2 && rect.height > 2;
    }).length;
    return {
      title: document.title,
      h1: document.querySelector("h1")?.textContent?.trim() || "",
      h2: document.querySelector("h2")?.textContent?.trim() || "",
      productNavLinks: visible(".product-nav-link"),
      statusPills: visible(".status-pill"),
      charts: visible("canvas, .finance-chart, .chart-card, .daily-mini-chart, .chart-spec-card"),
      maps: visible(".leaflet-container, .leaflet-war-map, .war-map-canvas-fallback, [data-renderer='leaflet-war-map']"),
      heatmapTiles: visible(".market-heatmap-tile, .market-map-tile"),
      newsRows: visible(".market-news-row, .news-row, .fusion-news-row, .cockpit-news-item"),
      commandRows: visible(".command-result-card, .command-row, .terminal-command-card, .cockpit-command-strip a"),
      sourceRows: visible(".status-row, .source-row, .daily-source-card, .boundary-row"),
      hasTerminalCockpit: Boolean(document.querySelector(".market-terminal-cockpit")),
      hasCommandProduct: Boolean(document.querySelector(".terminal-command-product")),
      hasContractDiagnosticsText: text.includes("Contract diagnostics"),
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
      bodyTextLength: text.length,
    };
  });
}

function sanitizeLabel(value) {
  return String(value).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 48) || "final";
}
