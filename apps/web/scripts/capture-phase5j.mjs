import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5j_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";
const baselineOnly = process.env.GT_PHASE5J_BASELINE_ONLY === "1";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const consoleErrors = [];

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  if (baselineOnly) {
    await page.goto(baseUrl + "/?view=options-quant&symbol=AAPL&mode=fixture", {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await page.waitForSelector('[data-workspace="OptionsQuantWorkspace"]', { timeout: 60_000 });
  const baselineDesktop = path.join(outputDirectory, "baseline-options-desktop.png");
  await page.screenshot({ path: baselineDesktop, fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  const baselineMobile = path.join(outputDirectory, "baseline-options-mobile.png");
  await page.screenshot({ path: baselineMobile, fullPage: false });

  const sizes = {
    desktop: (await stat(baselineDesktop)).size,
    mobile: (await stat(baselineMobile)).size,
  };
    console.log(JSON.stringify({ baselineOnly, screenshotBytes: sizes, browserConsoleErrorCount: consoleErrors.length }, null, 2));
  }

  if (!baselineOnly) {
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.goto(baseUrl + "/?view=options-quant&symbol=AAPL&mode=live-if-available&surface=chain&optionType=all&moneyness=all", {
      waitUntil: "domcontentloaded",
      timeout: 120_000,
    });
    await page.waitForSelector('[data-options-state="ready"]', { timeout: 120_000 });
    await page.waitForFunction(() => Number(document.querySelector("[data-options-rows]")?.getAttribute("data-options-rows") || 0) >= 40, null, { timeout: 120_000 });
    const liveChain = await inspect(page);
    assert(liveChain.totalRows >= 40, "live/cache chain did not expose at least 40 contracts");
    assert(liveChain.visibleStrikes >= 15, "selected expiry did not expose a useful strike table");
    assert(liveChain.tableWidth >= 760, "chain table is too narrow for a terminal surface");
    const liveDesktop = path.join(outputDirectory, "options-live-chain-desktop.png");
    await page.screenshot({ path: liveDesktop, fullPage: false });

    const expirySelect = page.locator(".options-controls label").filter({ hasText: "Expiry" }).locator("select");
    if (await expirySelect.locator("option").count() > 1) {
      await expirySelect.selectOption({ index: 1 });
      await page.waitForURL((url) => Boolean(url.searchParams.get("expiry")));
    }
    await page.getByRole("button", { name: "put", exact: true }).click();
    await page.waitForURL((url) => url.searchParams.get("optionType") === "put");
    await page.locator(".options-controls label").filter({ hasText: "Moneyness" }).locator("select").selectOption("atm");
    await page.waitForURL((url) => url.searchParams.get("moneyness") === "atm");
    const firstPriceButton = page.locator(".options-chain-table tbody td button").first();
    if (await firstPriceButton.count()) {
      await firstPriceButton.click();
      await page.waitForURL((url) => Boolean(url.searchParams.get("selected")));
    }
    const firstCompare = page.locator(".options-compare-control input").first();
    await firstCompare.click();
    await page.waitForURL((url) => Boolean(url.searchParams.get("compare")));
    await page.getByRole("button", { name: "IV structure", exact: true }).click();
    await page.waitForURL((url) => url.searchParams.get("surface") === "iv");
    await page.waitForSelector(".options-iv-chart", { timeout: 60_000 });
    const ivPoints = await page.locator(".options-iv-chart circle").count();
    assert(ivPoints >= 3, "IV chart did not render enough source points");
    const interactionUrl = page.url();
    const ivDesktop = path.join(outputDirectory, "options-live-iv-desktop.png");
    await page.screenshot({ path: ivDesktop, fullPage: false });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(baseUrl + "/?view=options-quant&symbol=AAPL&mode=live-if-available&surface=chain&optionType=all&moneyness=all", {
      waitUntil: "domcontentloaded",
      timeout: 120_000,
    });
    await page.waitForSelector('[data-options-state="ready"]', { timeout: 120_000 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(600);
    const mobile = await inspect(page);
    const liveMobile = path.join(outputDirectory, "options-live-chain-mobile.png");
    await page.screenshot({ path: liveMobile, fullPage: false });
    assert(mobile.viewportWidth === 390, "mobile viewport was not applied");
    assert(mobile.productWidth >= 340 && mobile.productWidth <= 390, "mobile product width overflowed: " + mobile.productWidth + "px in " + mobile.viewportWidth + "px viewport");

    await page.setViewportSize({ width: 1200, height: 820 });
    await page.goto(baseUrl + "/?view=options-quant&symbol=AAPL&mode=fixture&surface=scenario&optionType=all&moneyness=all", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await page.waitForSelector(".options-scenario-matrix", { timeout: 60_000 });
    const fixture = await inspect(page);
    assert(fixture.totalRows >= 30, "fixture did not retain a useful option chain");
    assert(fixture.scenarioRows >= 10, "fixture scenario matrix is incomplete");
    const fixtureFallback = path.join(outputDirectory, "options-fixture-scenario.png");
    await page.screenshot({ path: fixtureFallback, fullPage: false });

    const finalSizes = Object.fromEntries(await Promise.all([
      ["liveDesktop", liveDesktop],
      ["ivDesktop", ivDesktop],
      ["liveMobile", liveMobile],
      ["fixtureFallback", fixtureFallback],
    ].map(async ([key, file]) => [key, (await stat(file)).size])));
    assert(consoleErrors.length === 0, "browser console errors: " + consoleErrors.join(" | "));
    console.log(JSON.stringify({ liveChain, mobile, fixture, ivPoints, interactionUrl, screenshotBytes: finalSizes, browserConsoleErrorCount: consoleErrors.length }, null, 2));
  }
} finally {
  await browser.close();
}

async function inspect(page) {
  return page.locator(".options-product").evaluate((root) => {
    const table = root.querySelector(".options-chain-table");
    const rect = root.getBoundingClientRect();
    return {
      totalRows: Number(root.getAttribute("data-options-rows") || 0),
      visibleStrikes: root.querySelectorAll(".options-chain-table tbody tr").length,
      scenarioRows: root.querySelectorAll(".options-scenario-matrix tbody tr").length,
      ivPoints: root.querySelectorAll(".options-iv-chart circle").length,
      tableWidth: Math.round(table?.getBoundingClientRect().width || 0),
      productWidth: Math.round(rect.width),
      viewportWidth: window.innerWidth,
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
