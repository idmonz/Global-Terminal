import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5i_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";
const liveUrl = `${baseUrl}/?view=market-map&mode=live-if-available&assetClass=equity&sector=all&freshness=all&sort=rank_score&direction=desc&selected=AAPL&compare=`;

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const consoleErrors = [];

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto(`${baseUrl}/?view=screener-drilldown&mode=cache`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForSelector('[data-workspace="ScreenerDrilldownWorkspace"]', { timeout: 60_000 });
  const baselinePath = path.join(outputDirectory, "baseline-screener-diagnostics.png");
  await page.screenshot({ path: baselinePath, fullPage: false });

  await page.goto(liveUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForSelector('[data-product-view="market-map-screener"]', { timeout: 120_000 });
  await page.waitForFunction(() => {
    const root = document.querySelector('[data-market-map-state="ready"]');
    return root && Number(root.getAttribute("data-market-map-rows") || 0) >= 50;
  }, { timeout: 120_000 });

  const desktop = await inspect(page);
  assert(desktop.rows >= 50, `expected at least 50 rows, received ${desktop.rows}`);
  assert(desktop.tiles >= 50, `expected at least 50 heatmap tiles, received ${desktop.tiles}`);
  assert(desktop.tableRows >= 50, `expected at least 50 ranked rows, received ${desktop.tableRows}`);
  assert(desktop.scatterPoints >= 40, `expected broad scatter coverage, received ${desktop.scatterPoints}`);
  assert(desktop.heatmapWidth >= 700 && desktop.heatmapHeight >= 500, `heatmap is undersized: ${desktop.heatmapWidth}x${desktop.heatmapHeight}`);

  const desktopPath = path.join(outputDirectory, "market-map-live-desktop.png");
  await page.screenshot({ path: desktopPath, fullPage: false });

  const sectorSelect = page.locator('.market-map-mobile-controls label').filter({ hasText: "Sector" }).locator("select");
  await sectorSelect.selectOption({ index: 1 });
  await page.waitForURL((url) => url.searchParams.get("sector") !== "all");
  const firstTile = page.locator(".market-map-tile").first();
  await firstTile.click();
  await page.waitForURL((url) => Boolean(url.searchParams.get("selected")));
  const compareButton = page.getByRole("button", { name: /Add compare|Remove compare/ });
  if ((await compareButton.textContent())?.includes("Add")) await compareButton.click();
  await page.waitForURL((url) => Boolean(url.searchParams.get("compare")));
  const interactionUrl = page.url();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(700);
  const mobile = await inspect(page);
  assert(mobile.heatmapWidth >= 340, `mobile heatmap is too narrow: ${mobile.heatmapWidth}`);
  const mobilePath = path.join(outputDirectory, "market-map-live-mobile.png");
  await page.screenshot({ path: mobilePath, fullPage: false });

  await page.setViewportSize({ width: 1200, height: 800 });
  await page.goto(`${baseUrl}/?view=market-map&mode=fixture&sector=all&sort=rank_score&direction=desc&selected=AAPL&compare=`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 60_000 });
  const fixture = await inspect(page);
  assert(fixture.rows >= 20, "fixture fallback did not preserve a useful deterministic market map");
  const fixturePath = path.join(outputDirectory, "market-map-fixture-fallback.png");
  await page.screenshot({ path: fixturePath, fullPage: false });

  const sizes = Object.fromEntries(await Promise.all([
    ["baseline", baselinePath],
    ["desktop", desktopPath],
    ["mobile", mobilePath],
    ["fixture", fixturePath],
  ].map(async ([key, file]) => [key, (await stat(file)).size])));

  console.log(JSON.stringify({ desktop, mobile, fixture, interactionUrl, screenshotBytes: sizes, browserConsoleErrorCount: consoleErrors.length }, null, 2));
} finally {
  await browser.close();
}

async function inspect(page) {
  return page.locator('[data-market-map-state="ready"]').evaluate((root) => {
    const heatmap = root.querySelector(".market-map-heatmap");
    const rect = heatmap?.getBoundingClientRect();
    return {
      rows: Number(root.getAttribute("data-market-map-rows") || 0),
      tiles: root.querySelectorAll(".market-map-tile").length,
      tableRows: root.querySelectorAll(".market-map-ranked-table tbody tr").length,
      scatterPoints: root.querySelectorAll(".market-map-scatter circle").length,
      heatmapWidth: Math.round(rect?.width || 0),
      heatmapHeight: Math.round(rect?.height || 0),
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
