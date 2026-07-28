import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5o_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
const errors = { console: [], page: [] };
page.on("console", (message) => { if (message.type() === "error") errors.console.push(message.text()); });
page.on("pageerror", (error) => errors.page.push(error.stack || error.message));

try {
  const baseParams = new URLSearchParams({
    view: "market-map",
    mode: "fixture",
    sector: "all",
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
    selected: "AAPL",
    compare: "",
  });
  await page.goto(`${baseUrl}/?${baseParams.toString()}`, { waitUntil: "networkidle", timeout: 120_000 });
  await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 60_000 });

  const heatmap = await inspect(page);
  assert(heatmap.rows >= 20, `fixture discovery is too small: ${heatmap.rows}`);
  assert(heatmap.tiles >= 20, `heatmap tile coverage is too small: ${heatmap.tiles}`);
  assert(heatmap.modelButtons === 4, `expected four rank models, got ${heatmap.modelButtons}`);
  assert(heatmap.filterCount >= 10, `expected composable filters, got ${heatmap.filterCount}`);
  assert(heatmap.width >= 1200, `desktop discovery workspace too narrow: ${heatmap.width}`);
  assert(heatmap.scrollWidth <= heatmap.viewportWidth, `desktop overflow ${heatmap.scrollWidth}/${heatmap.viewportWidth}`);
  const heatmapPath = path.join(outputDirectory, "market-discovery-heatmap-desktop.png");
  await page.screenshot({ path: heatmapPath, fullPage: false });

  await page.locator(".market-map-filter-deck label").filter({ hasText: "Market cap" }).locator("select").selectOption("mega");
  await page.waitForURL((url) => url.searchParams.get("marketCap") === "mega");
  const filtered = await inspect(page);
  assert(filtered.rows > 0 && filtered.rows < heatmap.rows, `market-cap filter did not narrow rows: ${filtered.rows}/${heatmap.rows}`);

  await page.getByRole("button", { name: "table", exact: true }).click();
  await page.waitForURL((url) => url.searchParams.get("display") === "table");
  const tableRows = await page.locator(".market-map-ranked-table tbody tr").count();
  assert(tableRows === filtered.rows, `ranked table row count mismatch ${tableRows}/${filtered.rows}`);
  const tablePath = path.join(outputDirectory, "market-discovery-ranked-table.png");
  await page.screenshot({ path: tablePath, fullPage: false });

  await page.getByRole("button", { name: "factors", exact: true }).click();
  await page.waitForURL((url) => url.searchParams.get("display") === "factors");
  const factorCards = await page.locator(".market-map-factor-grid > button").count();
  assert(factorCards > 0, "factor attribution view is empty");
  const factorPath = path.join(outputDirectory, "market-discovery-factor-attribution.png");
  await page.screenshot({ path: factorPath, fullPage: false });

  const nameInput = page.locator(".market-map-saved-screens input");
  await nameInput.fill(`Phase 5O ${Date.now()}`);
  await page.getByRole("button", { name: "Save current", exact: true }).click();
  await page.waitForFunction(() => document.querySelector(".market-map-saved-screens")?.textContent?.includes("Saved locally."), null, { timeout: 30_000 });
  const savedOptions = await page.locator(".market-map-saved-screens select option").count();
  assert(savedOptions >= 2, "saved-screen API did not return the created screen");

  await page.getByRole("button", { name: "heatmap", exact: true }).click();
  await page.waitForURL((url) => url.searchParams.get("display") === "heatmap");
  await page.locator(".market-map-tile").first().click();
  const selected = new URL(page.url()).searchParams.get("selected");
  await page.getByRole("link", { name: "Open workstation", exact: true }).click();
  await page.waitForSelector('[data-symbol-workstation-state]', { timeout: 60_000 });
  const workstationUrl = new URL(page.url());
  assert(workstationUrl.searchParams.get("origin") === "market-map", "workstation route lost market-map origin");
  assert(workstationUrl.searchParams.get("originState")?.includes("marketCap%3Dmega") || workstationUrl.searchParams.get("originState")?.includes("marketCap=mega"), "workstation route lost filter state");
  await page.getByRole("link", { name: "Return to saved screen state", exact: true }).click();
  await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 60_000 });
  const returnedUrl = new URL(page.url());
  assert(returnedUrl.searchParams.get("marketCap") === "mega", "return journey lost market-cap filter");
  assert(returnedUrl.searchParams.get("selected") === selected, "return journey lost selected symbol");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  const mobile = await inspect(page);
  assert(mobile.scrollWidth <= mobile.viewportWidth, `mobile overflow ${mobile.scrollWidth}/${mobile.viewportWidth}`);
  assert(mobile.width >= 350, `mobile discovery panel too narrow: ${mobile.width}`);
  const mobilePath = path.join(outputDirectory, "market-discovery-mobile.png");
  await page.screenshot({ path: mobilePath, fullPage: true });

  await page.setViewportSize({ width: 1600, height: 1000 });
  baseParams.set("mode", "live-if-available");
  baseParams.set("marketCap", "all");
  baseParams.set("display", "heatmap");
  await page.goto(`${baseUrl}/?${baseParams.toString()}`, { waitUntil: "networkidle", timeout: 180_000 });
  await page.waitForFunction(() => Number(document.querySelector('[data-market-map-state="ready"]')?.getAttribute("data-market-map-rows") || 0) >= 50, null, { timeout: 180_000 });
  const live = await inspect(page);
  assert(live.rows >= 50, `live-if-available path returned only ${live.rows} rows`);
  const liveEvidence = await page.locator(".market-map-selected").innerText();
  assert(liveEvidence.includes("live/fresh") || liveEvidence.includes("cached"), "live evidence panel does not expose provider state");
  const livePath = path.join(outputDirectory, "market-discovery-live-data.png");
  await page.screenshot({ path: livePath, fullPage: false });

  const screenshotBytes = {};
  for (const [key, file] of Object.entries({ heatmap: heatmapPath, table: tablePath, factors: factorPath, mobile: mobilePath, live: livePath })) {
    screenshotBytes[key] = (await stat(file)).size;
    assert(screenshotBytes[key] > 15_000, `${key} screenshot unexpectedly small`);
  }
  assert(errors.console.length === 0, `console errors: ${errors.console.join(" | ")}`);
  assert(errors.page.length === 0, `page errors: ${errors.page.join(" | ")}`);

  const report = {
    baseUrl,
    heatmap,
    filtered,
    tableRows,
    factorCards,
    savedOptions,
    selected,
    mobile,
    live,
    screenshotBytes,
    browserConsoleErrorCount: errors.console.length,
    browserPageErrorCount: errors.page.length,
  };
  await writeFile(path.join(outputDirectory, "phase5o-browser-report.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function inspect(targetPage) {
  return targetPage.locator('[data-market-map-state="ready"]').evaluate((root) => {
    const rect = root.getBoundingClientRect();
    return {
      rows: Number(root.getAttribute("data-market-map-rows") || 0),
      tiles: root.querySelectorAll(".market-map-tile").length,
      modelButtons: root.querySelectorAll(".market-map-model-strip button").length,
      filterCount: root.querySelectorAll(".market-map-filter-deck select").length,
      width: Math.round(rect.width),
      viewportWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
