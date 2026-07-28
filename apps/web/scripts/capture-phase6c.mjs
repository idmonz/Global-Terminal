import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3045";
const scenario = String(process.env.PHASE6C_SCENARIO || "online").toLowerCase();
const label = String(process.env.PHASE6C_LABEL || scenario).replace(/[^a-zA-Z0-9_-]/g, "_");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase6c_visual_${label}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  if (scenario === "online") {
    for (const symbol of ["AAPL", "TSLA", "JNJ", "TTE", "TMUS"]) {
      captures[symbol] = await captureAsset(`${symbol.toLowerCase()}-online-desktop`, {
        symbol,
        mode: "live-if-available",
        compare: "SPY",
        expectChart: true,
        expectMaterialized: symbol !== "AAPL",
      });
    }
    captures.tslaMobile = await captureAsset("tsla-online-mobile", {
      symbol: "TSLA",
      mode: "live-if-available",
      compare: "SPY",
      expectChart: true,
      expectMaterialized: true,
      viewport: { width: 390, height: 844 },
      fullPage: true,
      maxChartTop: 980,
    });
    captures.tslaFinancials = await captureAsset("tsla-online-financials", {
      symbol: "TSLA",
      mode: "live-if-available",
      surface: "financials",
      expectChart: false,
      expectMaterialized: true,
      expectSecFacts: true,
    });
    captures.originRoundTrip = await captureOriginRoundTrip();
  } else if (scenario === "cache") {
    captures.tslaCache = await captureAsset("tsla-cache-desktop", {
      symbol: "TSLA",
      mode: "cache",
      compare: "SPY",
      expectChart: true,
      expectMaterialized: true,
    });
    captures.jnjCacheMobile = await captureAsset("jnj-cache-mobile", {
      symbol: "JNJ",
      mode: "cache",
      compare: "SPY",
      expectChart: true,
      expectMaterialized: true,
      viewport: { width: 390, height: 844 },
      fullPage: true,
      maxChartTop: 980,
    });
  } else if (scenario === "failure") {
    captures.unsupported = await captureAsset("tsla-unsupported-capability", {
      symbol: "TSLA",
      mode: "live-if-available",
      interval: "15m",
      range: "1y",
      expectedStatus: "unsupported-interval",
      expectChart: false,
      expectMaterialized: true,
    });
    captures.unknown = await captureUnknown("NOTAREAL123");
  } else if (scenario === "offline") {
    captures.aaplOffline = await captureAsset("aapl-offline-fixture", {
      symbol: "AAPL",
      mode: "live-if-available",
      expectChart: true,
      expectRuntime: false,
    });
    captures.tslaOffline = await captureUnknown("TSLA", false);
    captures.tslaOfflineMobile = await captureUnknown("TSLA", false, { width: 390, height: 844 });
  } else {
    throw new Error(`Unsupported PHASE6C_SCENARIO: ${scenario}`);
  }

  const report = {
    baseUrl,
    scenario,
    captured_at: new Date().toISOString(),
    captures,
  };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureAsset(name, options) {
  const {
    symbol,
    mode,
    interval = "1d",
    range = "3mo",
    compare = "",
    surface = "overview",
    expectedStatus = null,
    expectChart,
    expectMaterialized = false,
    expectRuntime = true,
    expectSecFacts = false,
    viewport = { width: 1600, height: 1000 },
    fullPage = false,
    maxChartTop = 720,
  } = options;
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  const started = Date.now();
  try {
    await page.goto(assetUrl(symbol, mode, interval, range, compare, surface), {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector("[data-symbol-workstation-state]", { timeout: 180_000 });
    if (expectChart) {
      await page.waitForFunction(
        () => document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") !== "loading",
        null,
        { timeout: 120_000 },
      );
    }
    await page.waitForTimeout(500);
    const observed = await page.evaluate(() => {
      const root = document.querySelector("[data-symbol-workstation-state]");
      const chart = document.querySelector("[data-chart-state]");
      const chartRect = chart?.getBoundingClientRect();
      const runtime = document.querySelector("[data-runtime-health-state]");
      return {
        symbol: root?.getAttribute("data-symbol"),
        status: root?.getAttribute("data-symbol-workstation-state"),
        historyRows: Number(root?.getAttribute("data-chart-rows") || 0),
        chartState: chart?.getAttribute("data-chart-state") || null,
        chartPoints: Number(chart?.getAttribute("data-chart-points") || 0),
        chartCandles: Number(chart?.getAttribute("data-chart-candles") || 0),
        chartTop: Math.round(chartRect?.top || 0),
        chartWidth: Math.round(chartRect?.width || 0),
        canvasCount: document.querySelectorAll("canvas").length,
        identityOrigin: root?.getAttribute("data-identity-origin"),
        marketSector: root?.getAttribute("data-market-map-sector"),
        classificationConflict: root?.getAttribute("data-market-map-conflict"),
        providerCallBudget: Number(root?.getAttribute("data-provider-call-budget") || 0),
        broadRebuild: root?.getAttribute("data-broad-rebuild"),
        identityEvidence: document.querySelectorAll("[data-phase6c-identity-evidence]").length,
        sourceLedger: document.querySelectorAll("[data-phase5v-source-ledger]").length,
        secFactCount: Number(document.querySelector("[data-phase6a-sec-facts]")?.getAttribute("data-sec-fact-count") || 0),
        exactNewsCount: Number(root?.getAttribute("data-exact-news-count") || 0),
        marketDataStatus: root?.getAttribute("data-market-data-status"),
        runtimeReachable: runtime?.getAttribute("data-runtime-health-reachable"),
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        bodyText: document.body.innerText,
      };
    });
    observed.firstUsefulPaintMs = Date.now() - started;

    assert(observed.symbol === symbol, `${name}: exact identity mismatch ${observed.symbol}`);
    if (expectedStatus) {
      assert(observed.status === expectedStatus, `${name}: expected ${expectedStatus}, got ${observed.status}`);
    } else if (expectChart) {
      const accepted = expectRuntime ? ["ready", "cached", "stale"] : ["fixture"];
      assert(accepted.includes(observed.status), `${name}: unexpected data status ${observed.status}`);
    }
    assert(observed.runtimeReachable === String(expectRuntime), `${name}: runtime reachability mismatch`);
    assert(observed.broadRebuild === "false", `${name}: selected symbol path claims broad rebuild`);
    if (expectedStatus) {
      assert(observed.providerCallBudget === 0, `${name}: rejected request should have a zero provider budget`);
    } else {
      assert(observed.providerCallBudget > 0 && observed.providerCallBudget <= 12, `${name}: provider call budget is invalid`);
    }
    assert(observed.identityEvidence === 1, `${name}: identity evidence strip missing`);
    if (surface === "overview") assert(observed.sourceLedger > 0, `${name}: source ledger missing`);
    assert(!observed.horizontalOverflow, `${name}: page-level horizontal overflow`);
    assert(observed.bodyText.includes(symbol), `${name}: exact symbol is not visible`);
    assert(!observed.bodyText.includes("No verified workspace for AAPL"), `${name}: Apple fallback leaked`);
    if (expectMaterialized) {
      assert(observed.identityOrigin === "materialized-market-snapshot", `${name}: materialized identity origin missing`);
      assert(observed.marketSector && observed.marketSector !== "unavailable", `${name}: Market Map classification missing`);
    }
    if (expectChart) {
      assert(observed.chartState === "ready", `${name}: chart is ${observed.chartState}`);
      assert(observed.historyRows > 20, `${name}: insufficient OHLCV rows`);
      assert(observed.chartPoints > 20, `${name}: chart point count is ${observed.chartPoints}`);
      assert(observed.canvasCount > 0, `${name}: chart canvas missing`);
      assert(observed.chartTop <= maxChartTop, `${name}: chart starts at ${observed.chartTop}px`);
      assert(observed.chartWidth >= (viewport.width < 500 ? 330 : 760), `${name}: chart width ${observed.chartWidth}px`);
      assert(observed.marketDataStatus && observed.marketDataStatus !== "unavailable", `${name}: source clock unavailable`);
    } else {
      if (expectedStatus) {
        assert(observed.historyRows === 0, `${name}: unsupported capability unexpectedly has history`);
      }
    }
    if (expectSecFacts) assert(observed.secFactCount > 0, `${name}: SEC fact rows missing`);
    assertErrorsEmpty(errors, name);

    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage });
    const screenshotBytes = (await stat(screenshot)).size;
    assert(screenshotBytes > 15_000, `${name}: screenshot unexpectedly small`);
    let secFactsScreenshot = null;
    if (expectSecFacts) {
      secFactsScreenshot = path.join(outputDirectory, `${name}-sec-facts.png`);
      await page.locator("[data-phase6a-sec-facts]").screenshot({ path: secFactsScreenshot });
      assert((await stat(secFactsScreenshot)).size > 8_000, `${name}: SEC facts screenshot unexpectedly small`);
    }
    delete observed.bodyText;
    return { ...observed, screenshot, screenshotBytes, secFactsScreenshot, url: page.url() };
  } finally {
    await page.close();
  }
}

async function captureOriginRoundTrip() {
  const name = "tsla-market-map-round-trip";
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(
      `${baseUrl}/?view=market-map&mode=live-if-available&query=TSLA&selected=TSLA&size=equal&color=relative_volume&sector=Consumer%20Discretionary`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 180_000 });
    await page.getByRole("link", { name: "Open workstation", exact: true }).click();
    await page.waitForSelector('[data-symbol="TSLA"]', { timeout: 180_000 });
    await page.getByRole("link", { name: "Return to saved screen state", exact: true }).click();
    await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 180_000 });
    const url = new URL(page.url());
    const observed = {
      query: url.searchParams.get("query"),
      selected: url.searchParams.get("selected"),
      size: url.searchParams.get("size"),
      color: url.searchParams.get("color"),
      sector: url.searchParams.get("sector"),
      horizontalOverflow: await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1),
    };
    assert(observed.query === "TSLA", `${name}: query state lost`);
    assert(observed.selected === "TSLA", `${name}: selected state lost`);
    assert(observed.size === "equal", `${name}: size state lost`);
    assert(observed.color === "relative_volume", `${name}: color state lost`);
    assert(observed.sector === "Consumer Discretionary", `${name}: sector state lost`);
    assert(!observed.horizontalOverflow, `${name}: page-level overflow`);
    assertErrorsEmpty(errors, name);
    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot });
    return { ...observed, screenshot, screenshotBytes: (await stat(screenshot)).size, url: page.url() };
  } finally {
    await page.close();
  }
}

async function captureUnknown(symbol, expectRuntime = true, viewport = { width: 1600, height: 1000 }) {
  const name = `${symbol.toLowerCase()}-${expectRuntime ? "unknown" : "offline-unknown"}-${viewport.width < 500 ? "mobile" : "desktop"}`;
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(assetUrl(symbol, "live-if-available", "1d", "3mo", ""), {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-symbol-workstation-state="unknown-symbol"]', { timeout: 180_000 });
    const observed = await page.evaluate(() => ({
      status: document.querySelector("[data-symbol-workstation-state]")?.getAttribute("data-symbol-workstation-state"),
      runtimeReachable: document.querySelector("[data-runtime-health-state]")?.getAttribute("data-runtime-health-reachable"),
      bodyText: document.body.innerText,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    }));
    assert(observed.status === "unknown-symbol", `${name}: unknown state missing`);
    assert(observed.runtimeReachable === String(expectRuntime), `${name}: runtime reachability mismatch`);
    assert(!observed.bodyText.includes("Apple Inc."), `${name}: Apple identity leaked`);
    assert(!observed.horizontalOverflow, `${name}: page-level overflow`);
    assertErrorsEmpty(errors, name);
    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage: viewport.width < 500 });
    delete observed.bodyText;
    return { ...observed, screenshot, screenshotBytes: (await stat(screenshot)).size, url: page.url() };
  } finally {
    await page.close();
  }
}

function assetUrl(symbol, mode, interval, range, compare, surface = "overview") {
  const params = new URLSearchParams({
    view: "asset",
    symbol,
    assetClass: "equity",
    interval,
    range,
    surface,
    mode,
    chartType: "candlestick",
    panels: "trend,momentum,risk,comparison,financials,news,asset,sources",
  });
  if (compare) params.set("compare", compare);
  return `${baseUrl}/?${params.toString()}`;
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
  assert(!errors.console.length, `${label}: console errors ${errors.console.join(" | ")}`);
  assert(!errors.page.length, `${label}: page errors ${errors.page.join(" | ")}`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
