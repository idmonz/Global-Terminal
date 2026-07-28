import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5m_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.aaplFixture = await captureAsset(browser, {
    name: "aapl-fixture-desktop",
    url: assetUrl("AAPL", "equity", "1d", "3mo", "fixture"),
    symbol: "AAPL",
    expectedStatus: "fixture",
  });

  captures.msftLive = await captureAsset(browser, {
    name: "msft-runtime-desktop",
    url: assetUrl("MSFT", "equity", "1d", "3mo", "live-if-available"),
    symbol: "MSFT",
    forbiddenWorkspaceText: ["Apple Inc.", "Bitcoin"],
  });

  captures.msftCache = await captureAsset(browser, {
    name: "msft-cache-desktop",
    url: assetUrl("MSFT", "equity", "1d", "3mo", "cache"),
    symbol: "MSFT",
    expectedStatus: "cached",
  });

  captures.spy = await captureAsset(browser, {
    name: "spy-etf-desktop",
    url: assetUrl("SPY", "etf", "1d", "3mo", "live-if-available"),
    symbol: "SPY",
    forbiddenWorkspaceText: ["Microsoft", "Apple Inc."],
  });

  captures.btc = await captureAsset(browser, {
    name: "btcusdt-crypto-desktop",
    url: assetUrl("BTCUSDT", "crypto", "1h", "5d", "live-if-available"),
    symbol: "BTCUSDT",
    forbiddenWorkspaceText: ["Ethereum", "Microsoft"],
  });

  captures.eth = await captureAsset(browser, {
    name: "ethusdt-crypto-desktop",
    url: assetUrl("ETHUSDT", "crypto", "1h", "5d", "live-if-available"),
    symbol: "ETHUSDT",
    forbiddenWorkspaceText: ["Bitcoin", "Apple Inc."],
  });

  captures.cacheMiss = await captureAsset(browser, {
    name: "suiusdt-cache-miss-desktop",
    url: assetUrl("SUIUSDT", "crypto", "1h", "5d", "cache"),
    symbol: "SUIUSDT",
    expectedStatus: "cache-miss",
    expectChart: false,
  });

  captures.unknown = await captureAsset(browser, {
    name: "unknown-symbol-desktop",
    url: assetUrl("NOTREAL", "equity", "1d", "3mo", "live-if-available"),
    symbol: "NOTREAL",
    expectedStatus: "unknown-symbol",
    expectChart: false,
  });

  captures.chartFallback = await captureAsset(browser, {
    name: "aapl-chart-fallback-desktop",
    url: `${assetUrl("AAPL", "equity", "1d", "3mo", "fixture")}&chartMode=fallback`,
    symbol: "AAPL",
    expectedStatus: "fixture",
    expectedChartState: "fallback",
  });

  captures.tablet = await captureAsset(browser, {
    name: "msft-runtime-tablet",
    url: assetUrl("MSFT", "equity", "1d", "3mo", "live-if-available"),
    symbol: "MSFT",
    maxWidth: 768,
    viewport: { width: 768, height: 1024 },
  });

  captures.mobile = await captureAsset(browser, {
    name: "ethusdt-runtime-mobile",
    url: assetUrl("ETHUSDT", "crypto", "1h", "5d", "live-if-available"),
    symbol: "ETHUSDT",
    minWidth: 340,
    maxWidth: 390,
    viewport: { width: 390, height: 844 },
  });

  const searchPage = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const searchErrors = listenForErrors(searchPage);
  let searchResults;
  let searchFocusOutline;
  let finalUrl;
  try {
    await searchPage.goto(assetUrl("AAPL", "equity", "1d", "3mo", "fixture"), {
      waitUntil: "networkidle",
      timeout: 120_000,
    });
    const search = searchPage.getByLabel("Search markets");
    await search.fill("micro");
    await searchPage.waitForSelector("#global-symbol-results a");
    searchResults = await searchPage.locator("#global-symbol-results a").allTextContents();
    assert(searchResults.some((value) => value.includes("MSFT")), "search did not rank Microsoft for 'micro'");
    await searchPage.locator("#global-symbol-results a").filter({ hasText: "MSFT" }).first().click();
    await searchPage.waitForURL((url) => url.searchParams.get("symbol") === "MSFT");
    assert(searchPage.url().includes("interval=1d") && searchPage.url().includes("range=3mo"), "search navigation lost interval/range state");
    await searchPage.waitForSelector('[data-symbol="MSFT"]');
    await searchPage.waitForSelector('[data-chart-state="ready"]');
    searchFocusOutline = await search.evaluate((element) => {
      element.focus();
      return getComputedStyle(element).outlineStyle;
    });
    assert(searchFocusOutline !== "none", "symbol search keyboard focus indicator is missing");
    assertErrorsEmpty(searchErrors, "symbol search navigation");
    finalUrl = searchPage.url();
  } finally {
    await searchPage.close();
  }

  const report = {
    baseUrl,
    captures,
    searchResults,
    searchFocusOutline,
    finalUrl,
    browserConsoleErrorCount: 0,
    browserPageErrorCount: 0,
  };
  await writeFile(path.join(outputDirectory, "phase5m-browser-report.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureAsset(browserInstance, {
  name,
  url,
  symbol,
  expectedStatus,
  expectChart = true,
  expectedChartState = "ready",
  forbiddenWorkspaceText = [],
  minWidth = 0,
  maxWidth = null,
  viewport = { width: 1600, height: 1000 },
}) {
  const page = await browserInstance.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 120_000 });
    await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 60_000 });
    await page.waitForSelector("[data-symbol-workstation-state]", { timeout: 60_000 });

    const workstation = page.locator("[data-symbol-workstation-state]").first();
    const inspection = await workstation.evaluate((root) => {
      const rect = root.getBoundingClientRect();
      const chart = root.querySelector("[data-chart-state]");
      return {
        symbol: root.getAttribute("data-symbol"),
        status: root.getAttribute("data-symbol-workstation-state"),
        historyRows: Number(root.getAttribute("data-chart-rows") || 0),
        chartState: chart?.getAttribute("data-chart-state") || null,
        chartPoints: Number(chart?.getAttribute("data-chart-points") || 0),
        workspaceText: root.textContent || "",
        productWidth: Math.round(rect.width),
        viewportWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
      };
    });

    assert(inspection.symbol === symbol || inspection.status === "unknown-symbol", `${name}: expected ${symbol}, received ${inspection.symbol}`);
    if (expectedStatus) assert(inspection.status === expectedStatus, `${name}: expected status ${expectedStatus}, received ${inspection.status}`);
    if (expectChart) {
      await page.waitForFunction(
        () => document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") !== "loading",
        null,
        { timeout: 60_000 },
      );
      const chartState = await page.locator("[data-chart-state]").first().getAttribute("data-chart-state");
      const chartPoints = Number(await page.locator("[data-chart-state]").first().getAttribute("data-chart-points"));
      assert(chartState === expectedChartState, `${name}: expected chart ${expectedChartState}, received ${chartState}`);
      if (expectedChartState === "ready") assert(chartPoints > 0, `${name}: ready chart has no points`);
      inspection.chartState = chartState;
      inspection.chartPoints = chartPoints;
    } else {
      assert(inspection.historyRows === 0 || inspection.status === "unknown-symbol", `${name}: unavailable state unexpectedly has history rows`);
    }
    for (const forbidden of forbiddenWorkspaceText) {
      assert(!inspection.workspaceText.includes(forbidden), `${name}: cross-symbol content leaked: ${forbidden}`);
    }
    assert(inspection.scrollWidth <= inspection.viewportWidth, `${name}: page overflows viewport ${inspection.scrollWidth}/${inspection.viewportWidth}`);
    if (minWidth) assert(inspection.productWidth >= minWidth, `${name}: product width is too narrow: ${inspection.productWidth}`);
    if (maxWidth) assert(inspection.productWidth <= maxWidth, `${name}: product width exceeds viewport: ${inspection.productWidth}/${maxWidth}`);
    assert(new URL(page.url()).searchParams.get("symbol") === symbol, `${name}: URL lost symbol state`);

    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage: false });
    const screenshotBytes = (await stat(screenshot)).size;
    assert(screenshotBytes > 12_000, `${name}: screenshot is unexpectedly small: ${screenshotBytes}`);
    assertErrorsEmpty(errors, name);
    delete inspection.workspaceText;
    return { ...inspection, screenshot, screenshotBytes, url: page.url() };
  } finally {
    await page.close();
  }
}

function assetUrl(symbol, assetClass, interval, range, mode) {
  const params = new URLSearchParams({
    view: "asset",
    symbol,
    assetClass,
    interval,
    range,
    surface: "overview",
    mode,
  });
  return `${baseUrl}/?${params.toString()}`;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function listenForErrors(page) {
  const errors = { console: [], page: [] };
  page.on("console", (message) => {
    if (message.type() === "error") errors.console.push(message.text());
  });
  page.on("pageerror", (error) => errors.page.push(error.stack || error.message));
  return errors;
}

function assertErrorsEmpty(errors, label) {
  if (errors.console.length || errors.page.length) {
    console.error(JSON.stringify({ label, errors }, null, 2));
  }
  assert(errors.console.length === 0, `${label}: browser console errors: ${errors.console.join(" | ")}`);
  assert(errors.page.length === 0, `${label}: browser page errors: ${errors.page.join(" | ")}`);
}
