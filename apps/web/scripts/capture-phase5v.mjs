import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5v_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.aapl = await capture("aapl-equity-desktop", assetUrl("AAPL", "equity", "1d", "3mo", "cache", "candlestick", "SPY"), {
    symbol: "AAPL",
    expectChart: true,
    expectOptions: true,
    expectCompare: true,
    maxChartTop: 620,
  });
  captures.msft = await capture("msft-equity-desktop", assetUrl("MSFT", "equity", "1d", "3mo", "cache", "line", "SPY"), {
    symbol: "MSFT",
    expectChart: true,
    expectOptions: true,
    expectCompare: true,
    expectedChartType: "line",
    maxChartTop: 620,
  });
  captures.spy = await capture("spy-etf-desktop", assetUrl("SPY", "etf", "1d", "3mo", "cache", "candlestick", "QQQ"), {
    symbol: "SPY",
    expectChart: true,
    expectCompare: true,
    expectNoDerivatives: true,
    maxChartTop: 620,
  });
  captures.btc = await capture("btcusdt-crypto-desktop", assetUrl("BTCUSDT", "crypto", "1h", "5d", "cache", "candlestick", "ETHUSDT"), {
    symbol: "BTCUSDT",
    expectChart: true,
    expectDerivatives: true,
    expectCompare: true,
    maxChartTop: 620,
  });
  captures.eth = await capture("ethusdt-crypto-desktop", assetUrl("ETHUSDT", "crypto", "1h", "5d", "cache", "candlestick", "BTCUSDT"), {
    symbol: "ETHUSDT",
    expectChart: true,
    expectDerivatives: true,
    expectCompare: true,
    maxChartTop: 620,
  });
  captures.mobileAapl = await capture("aapl-equity-mobile", assetUrl("AAPL", "equity", "1d", "3mo", "cache", "candlestick", "SPY"), {
    symbol: "AAPL",
    expectChart: true,
    expectOptions: true,
    expectCompare: true,
    viewport: { width: 390, height: 844 },
    maxChartTop: 820,
    fullPage: true,
  });
  captures.mobileBtc = await capture("btcusdt-crypto-mobile", assetUrl("BTCUSDT", "crypto", "1h", "5d", "cache", "candlestick", "ETHUSDT"), {
    symbol: "BTCUSDT",
    expectChart: true,
    expectDerivatives: true,
    expectCompare: true,
    viewport: { width: 390, height: 844 },
    maxChartTop: 820,
    fullPage: true,
  });
  captures.optionsSurface = await capture("aapl-options-surface", assetUrl("AAPL", "equity", "1d", "3mo", "cache", "candlestick", "SPY", "options"), {
    symbol: "AAPL",
    expectChart: false,
    expectOptions: true,
    requiredText: ["OPRA", "Options Quant", "read-only"],
  });
  captures.unknown = await capture("unknown-symbol", assetUrl("NOTREAL", "equity", "1d", "3mo", "cache", "candlestick", ""), {
    symbol: "NOTREAL",
    expectChart: false,
    expectedStatus: "unknown-symbol",
  });

  const report = { baseUrl, captures, captured_at: new Date().toISOString() };
  await writeFile(path.join(outputDirectory, "phase5v-browser-report.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function capture(name, url, options) {
  const {
    symbol,
    expectedStatus,
    expectedChartType = "candlestick",
    expectChart,
    expectOptions = false,
    expectDerivatives = false,
    expectNoDerivatives = false,
    expectCompare = false,
    requiredText = [],
    viewport = { width: 1600, height: 1000 },
    maxChartTop = 900,
    fullPage = false,
  } = options;
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 120_000 });
    await page.waitForSelector("[data-symbol-workstation-state]", { timeout: 60_000 });
    if (expectChart) {
      await page.waitForFunction(() => document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") !== "loading", null, { timeout: 60_000 });
    }
    await page.waitForTimeout(400);
    const inspection = await page.evaluate(() => {
      const root = document.querySelector("[data-symbol-workstation-state]");
      const chart = document.querySelector("[data-chart-state]");
      const chartRect = chart?.getBoundingClientRect();
      const canvases = Array.from(document.querySelectorAll("canvas"));
      const text = root?.textContent || "";
      return {
        symbol: root?.getAttribute("data-symbol") || null,
        status: root?.getAttribute("data-symbol-workstation-state") || null,
        chartType: root?.getAttribute("data-chart-type") || null,
        historyRows: Number(root?.getAttribute("data-chart-rows") || 0),
        comparisonOverlap: Number(root?.getAttribute("data-comparison-overlap") || 0),
        newsCount: Number(root?.getAttribute("data-exact-news-count") || 0),
        chartState: chart?.getAttribute("data-chart-state") || null,
        chartPoints: Number(chart?.getAttribute("data-chart-points") || 0),
        chartCandles: Number(chart?.getAttribute("data-chart-candles") || 0),
        chartTop: Math.round(chartRect?.top || 0),
        chartWidth: Math.round(chartRect?.width || 0),
        deskStripCount: document.querySelectorAll("[data-phase5v-desk-strip]").length,
        sourceLedgerCount: document.querySelectorAll("[data-phase5v-source-ledger]").length,
        contextCardCount: document.querySelectorAll("[data-phase5v-context-card]").length,
        equityOptionsCount: document.querySelectorAll("[data-phase5v-equity-options]").length,
        cryptoDerivativesCount: document.querySelectorAll("[data-phase5v-crypto-derivatives]").length,
        scrollWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        canvasCount: canvases.length,
        text,
      };
    });

    assert(inspection.symbol === symbol || inspection.status === "unknown-symbol", `${name}: symbol mismatch ${inspection.symbol}`);
    if (expectedStatus) assert(inspection.status === expectedStatus, `${name}: expected ${expectedStatus}, got ${inspection.status}`);
    if (expectChart) {
      assert(inspection.chartState === "ready", `${name}: chart not ready (${inspection.chartState})`);
      assert(inspection.chartPoints > 0, `${name}: chart has no points`);
      assert(inspection.canvasCount > 0, `${name}: chart canvas missing`);
      assert(inspection.chartTop <= maxChartTop, `${name}: chart starts too low (${inspection.chartTop}px > ${maxChartTop}px)`);
      assert(inspection.chartWidth >= (viewport.width < 500 ? 340 : 760), `${name}: chart too narrow (${inspection.chartWidth}px)`);
    }
    if (expectChart && expectedChartType) assert(inspection.chartType === expectedChartType, `${name}: chart type lost`);
    if (expectCompare) assert(inspection.comparisonOverlap > 1, `${name}: comparison overlap missing`);
    if (expectChart) assert(inspection.deskStripCount > 0, `${name}: phase5v desk strip missing`);
    if (expectChart) assert(inspection.sourceLedgerCount > 0, `${name}: source ledger missing`);
    if (expectChart) assert(inspection.contextCardCount >= 5, `${name}: context card density too low`);
    if (expectOptions) assert(inspection.equityOptionsCount > 0, `${name}: options bridge missing`);
    if (expectDerivatives) assert(inspection.cryptoDerivativesCount > 0, `${name}: crypto derivatives card missing`);
    if (expectNoDerivatives) assert(inspection.cryptoDerivativesCount === 0, `${name}: crypto derivatives card leaked into non-crypto route`);
    requiredText.forEach((marker) => assert(inspection.text.includes(marker), `${name}: missing ${marker}`));
    assert(inspection.scrollWidth <= inspection.viewportWidth, `${name}: horizontal overflow ${inspection.scrollWidth}/${inspection.viewportWidth}`);
    assertErrorsEmpty(errors, name);

    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage });
    const screenshotBytes = (await stat(screenshot)).size;
    assert(screenshotBytes > 15_000, `${name}: screenshot unexpectedly small`);
    delete inspection.text;
    return { ...inspection, screenshot, screenshotBytes, url: page.url() };
  } finally {
    await page.close();
  }
}

function assetUrl(symbol, assetClass, interval, range, mode, chartType, compare, surface = "overview") {
  const params = new URLSearchParams({
    view: "asset",
    symbol,
    assetClass,
    interval,
    range,
    surface,
    mode,
    chartType,
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

function assertErrorsEmpty(errors, label) {
  assert(!errors.console.length, `${label}: console errors ${errors.console.join(" | ")}`);
  assert(!errors.page.length, `${label}: page errors ${errors.page.join(" | ")}`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
