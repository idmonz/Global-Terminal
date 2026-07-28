import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5n_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.aapl = await capture(browser, {
    name: "aapl-live-candlestick-desktop",
    url: assetUrl("AAPL", "equity", "1d", "3mo", "live-if-available", "candlestick", "SPY"),
    symbol: "AAPL",
    expectCandles: true,
    expectComparison: true,
    expectNews: true,
  });
  captures.aaplFull = await capture(browser, {
    name: "aapl-live-full-page",
    url: assetUrl("AAPL", "equity", "1d", "3mo", "live-if-available", "candlestick", "SPY"),
    symbol: "AAPL",
    expectCandles: true,
    expectComparison: true,
    expectNews: true,
    fullPage: true,
  });
  captures.msft = await capture(browser, {
    name: "msft-live-line-desktop",
    url: assetUrl("MSFT", "equity", "1d", "3mo", "live-if-available", "line", "SPY"),
    symbol: "MSFT",
    expectedChartType: "line",
    expectNews: true,
  });
  captures.spy = await capture(browser, {
    name: "spy-etf-financial-desktop",
    url: assetUrl("SPY", "etf", "1d", "3mo", "live-if-available", "candlestick", "QQQ"),
    symbol: "SPY",
    expectCandles: true,
    expectComparison: true,
    expectNews: true,
    requiredText: ["fund-profile"],
  });
  captures.btc = await capture(browser, {
    name: "btcusdt-derivatives-desktop",
    url: assetUrl("BTCUSDT", "crypto", "1h", "5d", "live-if-available", "candlestick", "ETHUSDT"),
    symbol: "BTCUSDT",
    expectCandles: true,
    expectComparison: true,
    expectNews: true,
    requiredText: ["Funding", "Open interest", "Basis"],
  });
  captures.fixtureEmptyNews = await capture(browser, {
    name: "aapl-fixture-empty-news-desktop",
    url: assetUrl("AAPL", "equity", "1d", "3mo", "fixture", "candlestick", ""),
    symbol: "AAPL",
    expectCandles: true,
    expectNews: false,
    requiredText: ["Live/cache exact-symbol news was not requested"],
  });
  captures.tablet = await capture(browser, {
    name: "aapl-live-tablet",
    url: assetUrl("AAPL", "equity", "1d", "3mo", "live-if-available", "candlestick", "SPY"),
    symbol: "AAPL",
    expectCandles: true,
    expectComparison: true,
    viewport: { width: 768, height: 1024 },
    minProductWidth: 700,
  });
  captures.mobile = await capture(browser, {
    name: "ethusdt-live-mobile",
    url: assetUrl("ETHUSDT", "crypto", "1h", "5d", "live-if-available", "candlestick", "BTCUSDT"),
    symbol: "ETHUSDT",
    expectCandles: true,
    expectComparison: true,
    viewport: { width: 390, height: 844 },
    minProductWidth: 350,
  });
  captures.fallback = await capture(browser, {
    name: "aapl-chart-fallback-desktop",
    url: `${assetUrl("AAPL", "equity", "1d", "3mo", "fixture", "candlestick", "")}&chartMode=fallback`,
    symbol: "AAPL",
    expectedChartState: "fallback",
    expectCandles: false,
  });
  captures.unknown = await capture(browser, {
    name: "unknown-symbol-desktop",
    url: assetUrl("NOTREAL", "equity", "1d", "3mo", "live-if-available", "candlestick", ""),
    symbol: "NOTREAL",
    expectedStatus: "unknown-symbol",
    expectChart: false,
  });

  const focus = await focusCheck(browser);
  const report = { baseUrl, captures, focus, browserConsoleErrorCount: 0, browserPageErrorCount: 0 };
  await writeFile(path.join(outputDirectory, "phase5n-browser-report.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function capture(browserInstance, options) {
  const {
    name, url, symbol, expectedStatus, expectedChartState = "ready", expectedChartType = "candlestick",
    expectChart = true, expectCandles = false, expectComparison = false, expectNews = false,
    requiredText = [], fullPage = false, viewport = { width: 1600, height: 1000 }, minProductWidth = 0,
  } = options;
  const page = await browserInstance.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 120_000 });
    await page.waitForSelector("[data-symbol-workstation-state]", { timeout: 60_000 });
    const root = page.locator("[data-symbol-workstation-state]").first();
    if (expectChart) await page.waitForFunction(() => document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") !== "loading", null, { timeout: 60_000 });
    const inspection = await root.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      const chart = element.querySelector("[data-chart-state]");
      const chartRect = chart?.getBoundingClientRect();
      const priceCell = element.querySelector(".symbol-chart-panel .finance-chart-container table tr:first-child td:nth-child(2)");
      const canvases = Array.from(element.querySelectorAll("canvas"));
      const canvasPixels = canvases.map((canvas) => {
        try {
          const ctx = canvas.getContext("2d", { willReadFrequently: true });
          if (!ctx || !canvas.width || !canvas.height) return 0;
          const image = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
          let nonTransparent = 0;
          for (let index = 3; index < image.length; index += 64) if (image[index] > 0) nonTransparent += 1;
          return nonTransparent;
        } catch { return -1; }
      });
      return {
        symbol: element.getAttribute("data-symbol"),
        status: element.getAttribute("data-symbol-workstation-state"),
        chartType: element.getAttribute("data-chart-type"),
        marketStatus: element.getAttribute("data-market-data-status"),
        overlap: Number(element.getAttribute("data-comparison-overlap") || 0),
        newsCount: Number(element.getAttribute("data-exact-news-count") || 0),
        historyRows: Number(element.getAttribute("data-chart-rows") || 0),
        chartState: chart?.getAttribute("data-chart-state") || null,
        chartPoints: Number(chart?.getAttribute("data-chart-points") || 0),
        candleCount: Number(chart?.getAttribute("data-chart-candles") || 0),
        volumeCount: Number(chart?.getAttribute("data-chart-volume") || 0),
        chartWidth: Math.round(chartRect?.width || 0),
        pricePlotWidth: Math.round(priceCell?.getBoundingClientRect().width || 0),
        productWidth: Math.round(rect.width),
        viewportWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        canvasCount: canvases.length,
        nonTransparentPixelSamples: canvasPixels.reduce((sum, value) => sum + Math.max(0, value), 0),
        text: element.textContent || "",
      };
    });

    assert(inspection.symbol === symbol || inspection.status === "unknown-symbol", `${name}: symbol mismatch ${inspection.symbol}`);
    if (expectedStatus) assert(inspection.status === expectedStatus, `${name}: expected ${expectedStatus}, got ${inspection.status}`);
    if (expectChart) {
      assert(inspection.chartState === expectedChartState, `${name}: chart state ${inspection.chartState}`);
      if (expectedChartState === "ready") {
        assert(inspection.chartPoints > 0, `${name}: no chart points`);
        assert(inspection.canvasCount > 0 && inspection.nonTransparentPixelSamples > 0, `${name}: blank canvas`);
        if (viewport.width >= 1200) assert(inspection.chartWidth >= 760, `${name}: desktop chart remains too narrow (${inspection.chartWidth}px)`);
        const minimumPlotRatio = viewport.width < 500 ? 0.70 : 0.78;
        assert(inspection.pricePlotWidth >= inspection.chartWidth * minimumPlotRatio, `${name}: price plot is compressed inside the chart (${inspection.pricePlotWidth}/${inspection.chartWidth})`);
      }
    }
    if (expectCandles) assert(inspection.candleCount > 0 && inspection.volumeCount > 0, `${name}: candles/volume unavailable`);
    assert(inspection.chartType === expectedChartType || inspection.status === "unknown-symbol", `${name}: chart type state lost`);
    if (expectComparison) assert(inspection.overlap > 1, `${name}: comparison overlap missing`);
    if (expectNews) assert(inspection.newsCount > 0, `${name}: exact news path did not succeed`);
    requiredText.forEach((marker) => assert(inspection.text.includes(marker), `${name}: missing ${marker}`));
    assert(inspection.scrollWidth <= inspection.viewportWidth, `${name}: document overflow ${inspection.scrollWidth}/${inspection.viewportWidth}`);
    if (minProductWidth) assert(inspection.productWidth >= minProductWidth, `${name}: product width ${inspection.productWidth}px is below ${minProductWidth}px`);
    assert(new URL(page.url()).searchParams.get("chartType") === expectedChartType, `${name}: URL lost chartType`);
    assert(new URL(page.url()).searchParams.has("panels"), `${name}: URL lost panels`);
    if (expectComparison) assert(new URL(page.url()).searchParams.get("compare"), `${name}: URL lost compare`);

    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage });
    const bytes = (await stat(screenshot)).size;
    assert(bytes > 15_000, `${name}: screenshot unexpectedly small (${bytes})`);
    assertErrorsEmpty(errors, name);
    delete inspection.text;
    return { ...inspection, screenshot, screenshotBytes: bytes, url: page.url() };
  } finally { await page.close(); }
}

async function focusCheck(browserInstance) {
  const page = await browserInstance.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = listenForErrors(page);
  try {
    await page.goto(assetUrl("AAPL", "equity", "1d", "3mo", "fixture", "candlestick", "SPY"), { waitUntil: "networkidle", timeout: 120_000 });
    const control = page.getByRole("link", { name: "Line", exact: true });
    const outline = await control.evaluate((element) => { element.focus(); return getComputedStyle(element).outlineStyle; });
    assert(outline !== "none", "chart control focus indicator missing");
    assertErrorsEmpty(errors, "focus-check");
    return { outline };
  } finally { await page.close(); }
}

function assetUrl(symbol, assetClass, interval, range, mode, chartType, compare) {
  const params = new URLSearchParams({
    view: "asset", symbol, assetClass, interval, range, surface: "overview", mode, chartType,
    panels: "trend,momentum,risk,comparison,financials,news,asset,sources",
  });
  if (compare) params.set("compare", compare);
  return `${baseUrl}/?${params.toString()}`;
}

function listenForErrors(page) {
  const errors = { console: [], page: [] };
  page.on("console", (message) => { if (message.type() === "error") errors.console.push(message.text()); });
  page.on("pageerror", (error) => errors.page.push(error.stack || error.message));
  return errors;
}
function assertErrorsEmpty(errors, label) { assert(!errors.console.length, `${label}: console errors ${errors.console.join(" | ")}`); assert(!errors.page.length, `${label}: page errors ${errors.page.join(" | ")}`); }
function assert(condition, message) { if (!condition) throw new Error(message); }
