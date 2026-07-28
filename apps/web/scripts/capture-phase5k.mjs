import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5k_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const consoleErrors = [];
const files = {};

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  const liveUrl = baseUrl + "/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY&mode=live-if-available";
  await page.goto(liveUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForSelector('[data-portfolio-state="ready"]', { timeout: 120_000 });
  await page.waitForFunction(() => Number(document.querySelector("[data-performance-points]")?.getAttribute("data-performance-points") || 0) >= 200, null, { timeout: 120_000 });
  const desktop = await inspect(page);
  assert(desktop.holdings >= 7, "desktop holdings are incomplete");
  assert(desktop.performancePoints >= 200, "desktop performance history is incomplete");
  assert(desktop.performancePolylineLength > 100, "portfolio chart is blank");
  assert(desktop.drawdownPolylineLength > 100, "drawdown chart is blank");
  assert(desktop.tableRows >= 7, "holdings table is blank");
  files.desktopOverview = path.join(outputDirectory, "portfolio-live-overview-desktop.png");
  await page.screenshot({ path: files.desktopOverview, fullPage: false });

  await page.getByRole("button", { name: "Correlation", exact: true }).click();
  await page.waitForURL((url) => url.searchParams.get("surface") === "correlation");
  await page.waitForSelector(".portfolio-correlation-cell", { timeout: 30_000 });
  const correlation = await inspect(page);
  assert(correlation.correlationCells >= 36, "correlation matrix is incomplete");
  files.desktopCorrelation = path.join(outputDirectory, "portfolio-live-correlation-desktop.png");
  await page.screenshot({ path: files.desktopCorrelation, fullPage: false });

  await page.getByRole("button", { name: "Stress", exact: true }).click();
  await page.waitForURL((url) => url.searchParams.get("surface") === "stress");
  await page.waitForSelector(".portfolio-stress-panel tbody tr", { timeout: 30_000 });
  const stress = await inspect(page);
  assert(stress.stressRows >= 8, "stress table is incomplete");
  files.desktopStress = path.join(outputDirectory, "portfolio-live-stress-desktop.png");
  await page.screenshot({ path: files.desktopStress, fullPage: false });

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto(liveUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForSelector('[data-portfolio-state="ready"]', { timeout: 120_000 });
  const tablet = await inspect(page);
  assert(tablet.productWidth <= 768 && tablet.productWidth >= 560, "tablet product width is invalid");
  files.tabletOverview = path.join(outputDirectory, "portfolio-live-overview-tablet.png");
  await page.screenshot({ path: files.tabletOverview, fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(liveUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForSelector('[data-portfolio-state="ready"]', { timeout: 120_000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  const mobile = await inspect(page);
  files.mobileOverview = path.join(outputDirectory, "portfolio-live-overview-mobile.png");
  await page.screenshot({ path: files.mobileOverview, fullPage: false });
  assert(mobile.viewportWidth === 390, "mobile viewport was not applied");
  assert(
    mobile.productWidth >= 300 && mobile.productWidth <= 390 && mobile.scrollWidth <= 390,
    "mobile product overflows viewport: " + JSON.stringify(mobile),
  );
  assert(mobile.performancePolylineLength > 100, "mobile performance chart is blank");

  await page.setViewportSize({ width: 1200, height: 850 });
  const fixtureUrl = baseUrl + "/?view=portfolio-risk&portfolio=demo-core&surface=factors&period=1y&benchmark=SPY&mode=fixture";
  await page.goto(fixtureUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForSelector(".portfolio-factor-row", { timeout: 60_000 });
  const fixture = await inspect(page);
  assert(fixture.factorRows >= 4, "fixture factor view is incomplete");
  assert(!page.url().includes("quantity=") && !page.url().includes("cost_basis="), "private fields leaked into URL");
  files.fixtureFactors = path.join(outputDirectory, "portfolio-fixture-factors.png");
  await page.screenshot({ path: files.fixtureFactors, fullPage: false });

  const focusButton = page.getByRole("button", { name: "Risk", exact: true });
  await focusButton.focus();
  const focusOutline = await focusButton.evaluate((element) => getComputedStyle(element).outlineStyle);
  assert(focusOutline !== "none", "keyboard focus indicator is missing");
  assert(consoleErrors.length === 0, "browser console errors: " + consoleErrors.join(" | "));

  const screenshotBytes = Object.fromEntries(
    await Promise.all(Object.entries(files).map(async ([key, file]) => [key, (await stat(file)).size])),
  );
  console.log(JSON.stringify({
    desktop,
    correlation,
    stress,
    tablet,
    mobile,
    fixture,
    focusOutline,
    finalUrl: page.url(),
    screenshotBytes,
    browserConsoleErrorCount: consoleErrors.length,
  }, null, 2));
} finally {
  await browser.close();
}

async function inspect(page) {
  return page.locator(".portfolio-product").evaluate((root) => {
    const rect = root.getBoundingClientRect();
    const performanceLine = root.querySelector(".portfolio-line");
    const drawdownLine = root.querySelector(".drawdown-line");
    return {
      holdings: Number(root.getAttribute("data-holdings-count") || 0),
      performancePoints: Number(root.getAttribute("data-performance-points") || 0),
      correlationAttributeCells: Number(root.getAttribute("data-correlation-cells") || 0),
      correlationCells: root.querySelectorAll(".portfolio-correlation-cell").length,
      tableRows: root.querySelectorAll(".portfolio-holdings-panel tbody tr").length,
      stressRows: root.querySelectorAll(".portfolio-stress-panel tbody tr").length,
      factorRows: root.querySelectorAll(".portfolio-factor-row").length,
      performancePolylineLength: performanceLine?.getAttribute("points")?.length || 0,
      drawdownPolylineLength: drawdownLine?.getAttribute("points")?.length || 0,
      productWidth: Math.round(rect.width),
      viewportWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
