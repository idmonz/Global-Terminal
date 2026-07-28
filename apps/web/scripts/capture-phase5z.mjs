import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3045";
const expectedRuntime = process.env.GT_EXPECT_RUNTIME || "online";
const label = String(process.env.PHASE5Z_LABEL || expectedRuntime).replace(/[^a-zA-Z0-9_-]/g, "_");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase5z_market_discovery_${label}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
const consoleErrors = [];
const pageErrors = [];
const results = [];

page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(`${page.url()} :: ${message.text()}`);
});
page.on("pageerror", (error) => pageErrors.push(`${page.url()} :: ${error.message}`));

const baseParams = new URLSearchParams({
  view: "market-map",
  mode: "live-if-available",
  sector: "all",
  industry: "all",
  country: "all",
  exchange: "all",
  eligibility: "all",
  freshness: "all",
  marketCap: "all",
  return1d: "all",
  return1m: "all",
  volatility: "all",
  rsi: "all",
  trend: "all",
  valuation: "all",
  quality: "all",
  rank: "balanced",
  display: "heatmap",
  group: "sector",
  size: "market_cap",
  color: "return_1d_pct",
  selected: "AAPL",
  compare: "",
});

try {
  await visitMap(page, baseParams);
  results.push(await capture(page, "market-map-desktop"));
  const desktop = result("market-map-desktop");
  assert(desktop.mapState === "ready", `desktop map state is ${desktop.mapState}`);
  assert(desktop.tiles === desktop.rows, `tile/row mismatch ${desktop.tiles}/${desktop.rows}`);
  assert(desktop.filterCount >= 14, `expected at least 14 filters, got ${desktop.filterCount}`);
  assert(desktop.universeCells >= 6, `universe truth strip is incomplete: ${desktop.universeCells}`);
  assert(desktop.grouping === "sector", `default grouping is ${desktop.grouping}`);
  assert(desktop.sizeMetric === "market_cap", `default size metric is ${desktop.sizeMetric}`);
  assert(desktop.colorMetric === "return_1d_pct", `default color metric is ${desktop.colorMetric}`);
  assert(desktop.firstTileTop <= 870, `first heatmap tile starts too low: ${desktop.firstTileTop}`);
  assert(!desktop.horizontalOverflow, "desktop discovery overflows horizontally");

  if (expectedRuntime === "online") {
    assert(desktop.runtimeState === "online", `expected online runtime, observed ${desktop.runtimeState}`);
    assert(desktop.rows > 60, `real discovery breadth did not exceed old ceiling: ${desktop.rows}`);
    assert(desktop.listingCoverage > 60, `official listing coverage too small: ${desktop.listingCoverage}`);
    assert(desktop.taxonomyCoverage >= 60, `taxonomy coverage regressed: ${desktop.taxonomyCoverage}`);
    assert(desktop.observations > 60, `official observations too small: ${desktop.observations}`);
  } else {
    assert(desktop.runtimeState === "offline", `expected offline runtime, observed ${desktop.runtimeState}`);
    assert(desktop.runtimeFallback, "offline route does not expose fallback");
    assert(desktop.listingCoverage === 0, `offline fixture claims official listings: ${desktop.listingCoverage}`);
  }

  const preferredGroup = page.locator(".market-map-sector > header button:not([disabled])").filter({ hasText: "Information Technology" });
  const groupButton = await preferredGroup.count()
    ? preferredGroup.first()
    : page.locator(".market-map-sector > header button:not([disabled])").first();
  const groupName = (await groupButton.innerText()).trim();
  await groupButton.click();
  await page.waitForFunction((name) => new URL(window.location.href).searchParams.get("sector") === name, groupName);
  results.push(await capture(page, "market-map-hierarchy"));
  const hierarchy = result("market-map-hierarchy");
  assert(new URL(hierarchy.url).searchParams.get("sector") === groupName, "sector drilldown was not preserved");
  assert(hierarchy.groupCount > 0, "industry drilldown has no groups");

  await selectControl(page, "Size", "equal");
  await selectControl(page, "Color", "relative_volume");
  await page.waitForFunction(() => document.querySelector(".market-map-heatmap")?.getAttribute("data-heatmap-size") === "equal");
  results.push(await capture(page, "market-map-encoding"));
  const encoding = result("market-map-encoding");
  assert(encoding.sizeMetric === "equal", `size metric did not change: ${encoding.sizeMetric}`);
  assert(encoding.colorMetric === "relative_volume", `color metric did not change: ${encoding.colorMetric}`);

  await page.getByRole("button", { name: "Up one level", exact: true }).click();
  await page.waitForFunction(() => new URL(window.location.href).searchParams.get("sector") === "all");
  await page.locator("#market-map-query").fill("AAPL");
  await page.locator(".market-map-search button[type=submit]").click();
  await page.waitForFunction(() => Number(document.querySelector('[data-market-map-state="ready"]')?.getAttribute("data-market-map-rows") || 0) === 1);
  await page.locator(".market-map-tile").click();
  await page.waitForFunction(() => new URL(window.location.href).searchParams.get("selected") === "AAPL");
  results.push(await capture(page, "market-map-aapl-selected"));

  if (expectedRuntime === "online") {
    await page.getByRole("link", { name: "Open workstation", exact: true }).click();
  } else {
    const offlineOrigin = new URLSearchParams(baseParams);
    offlineOrigin.set("query", "AAPL");
    offlineOrigin.set("size", "equal");
    offlineOrigin.set("color", "relative_volume");
    const assetParams = new URLSearchParams({
      view: "asset",
      symbol: "AAPL",
      assetClass: "equity",
      interval: "1d",
      range: "3mo",
      surface: "overview",
      mode: "live-if-available",
      origin: "market-map",
      originState: offlineOrigin.toString(),
    });
    await page.goto(`${baseUrl}/?${assetParams.toString()}`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  }
  await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 90_000 });
  await page.waitForFunction(() => ["ready", "fallback", "error"].includes(document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") || ""));
  results.push(await capture(page, "aapl-from-market-map"));
  const aapl = result("aapl-from-market-map");
  assert(aapl.chartState === "ready" || aapl.chartState === "fallback", `AAPL chart state is ${aapl.chartState}`);
  assert(aapl.returnLinks > 0, "AAPL workstation has no Market Map return action");

  await page.getByRole("link", { name: "Return to saved screen state", exact: true }).click();
  await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 90_000 });
  const returned = new URL(page.url());
  assert(returned.searchParams.get("query") === "AAPL", "return route lost query");
  assert(returned.searchParams.get("size") === "equal", "return route lost size metric");
  assert(returned.searchParams.get("color") === "relative_volume", "return route lost color metric");
  assert(returned.searchParams.get("selected") === "AAPL", "return route lost selected symbol");

  const cacheParams = new URLSearchParams(baseParams);
  cacheParams.set("mode", "cache");
  await visitMap(page, cacheParams);
  results.push(await capture(page, "market-map-cache"));
  const cache = result("market-map-cache");
  assert(cache.rows > 0, "cache route has no rows");

  await page.setViewportSize({ width: 390, height: 844 });
  await visitMap(page, baseParams);
  results.push(await capture(page, "market-map-mobile"));
  const mobile = result("market-map-mobile");
  assert(mobile.rows > 0, "mobile route has no rows");
  assert(!mobile.horizontalOverflow, "mobile discovery overflows horizontally");

  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto(`${baseUrl}/?view=asset&symbol=ZZZZ&assetClass=equity&mode=live-if-available`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 90_000 });
  results.push(await capture(page, "unsupported-symbol"));
  const unsupported = result("unsupported-symbol");
  assert(unsupported.unknownSymbolStates > 0, "unsupported symbol does not expose an honest unavailable state");
  assert(!unsupported.containsAppleIdentity, "unsupported symbol leaked AAPL identity");

  assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
  assert(pageErrors.length === 0, `page errors: ${pageErrors.join(" | ")}`);

  const report = { baseUrl, expectedRuntime, outputDirectory, results, consoleErrors, pageErrors };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function visitMap(target, params) {
  await target.goto(`${baseUrl}/?${params.toString()}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await target.waitForSelector('[data-market-map-state="ready"]', { timeout: 180_000 });
  await target.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
  });
  await target.waitForTimeout(700);
}

async function selectControl(target, label, value) {
  const control = target.locator(".market-map-display-controls label").filter({ hasText: label }).locator("select");
  await control.selectOption(value);
  await target.waitForFunction(([key, expected]) => new URL(window.location.href).searchParams.get(key) === expected, [
    label.toLowerCase() === "size" ? "size" : "color",
    value,
  ]);
}

async function capture(target, id) {
  const inspection = await target.evaluate(() => {
    const root = document.querySelector('[data-market-map-state]');
    const heatmap = document.querySelector(".market-map-heatmap");
    const heatmapRect = heatmap?.getBoundingClientRect();
    const tileRect = document.querySelector(".market-map-tile")?.getBoundingClientRect();
    const runtimeText = document.querySelector(".runtime-health-chip strong")?.textContent?.trim().toLowerCase() || "";
    return {
      url: window.location.href,
      containsAppleIdentity: document.body.innerText.includes("Apple Inc"),
      runtimeState: runtimeText === "online" ? "online" : runtimeText === "offline" ? "offline" : runtimeText || "unknown",
      runtimeFallback: Boolean(document.querySelector(".runtime-fallback-notice"))
        || document.body.innerText.toLowerCase().includes("static fixture fallback")
        || document.body.innerText.toLowerCase().includes("runtime-fallback"),
      mapState: root?.getAttribute("data-market-map-state") || "",
      rows: Number(root?.getAttribute("data-market-map-rows") || 0),
      observations: Number(root?.getAttribute("data-market-map-observations") || 0),
      listingCoverage: Number(root?.getAttribute("data-market-map-listing-coverage") || 0),
      taxonomyCoverage: Number(root?.getAttribute("data-market-map-taxonomy-coverage") || 0),
      tiles: document.querySelectorAll(".market-map-tile").length,
      groupCount: document.querySelectorAll(".market-map-sector").length,
      filterCount: document.querySelectorAll(".market-map-filter-deck select").length,
      universeCells: document.querySelectorAll(".market-map-universe-strip > div").length,
      grouping: heatmap?.getAttribute("data-heatmap-group") || "",
      sizeMetric: heatmap?.getAttribute("data-heatmap-size") || "",
      colorMetric: heatmap?.getAttribute("data-heatmap-color") || "",
      heatmapTop: Math.round(heatmapRect?.top || 0),
      firstTileTop: Math.round(tileRect?.top || 0),
      chartState: document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") || "",
      returnLinks: Array.from(document.querySelectorAll("a")).filter((node) => node.textContent?.includes("Return to saved screen state")).length,
      unknownSymbolStates: document.querySelectorAll('[data-symbol-workstation-state="unknown-symbol"], .symbol-unknown-state, .asset-unsupported-state').length
        + (document.body.innerText.toLowerCase().includes("unknown symbol") ? 1 : 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
  const screenshot = path.join(outputDirectory, `${id}.png`);
  await target.screenshot({ path: screenshot, fullPage: false });
  return { id, ...inspection, screenshot, screenshotBytes: (await stat(screenshot)).size };
}

function result(id) {
  return results.find((row) => row.id === id);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
