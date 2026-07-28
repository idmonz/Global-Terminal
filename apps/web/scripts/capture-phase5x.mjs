import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5x_provider_breadth_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";
const expectedRuntime = process.env.GT_EXPECT_RUNTIME || "any";

await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  if (expectedRuntime === "offline") {
    captures.home = await capture("offline-home", `${baseUrl}/?view=home&mode=live-if-available`, {
      requiredText: ["Runtime API", "Markets, risk and news"],
    });
    captures.aaplFallback = await capture("offline-aapl-fallback", `${baseUrl}/?view=asset&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&mode=live-if-available&surface=overview&compare=SPY`, {
      requiredText: ["AAPL"],
      waitForChart: true,
    });
    captures.unknown = await capture("offline-unknown-symbol", `${baseUrl}/?view=asset&symbol=NOTAREAL123&assetClass=equity&mode=live-if-available`, {
      requiredText: ["unknown-symbol", "No verified workspace"],
    });
  } else {
    captures.home = await capture("home-online", `${baseUrl}/?view=home&mode=live-if-available`, {
      requiredText: ["Runtime API", "Markets, risk and news"],
    });
    captures.aaplFinancials = await capture("aapl-financials-provider-breadth", `${baseUrl}/?view=asset&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&mode=live-if-available&surface=financials&compare=SPY`, {
      requiredText: ["AAPL", "Source-bounded fundamentals"],
      waitForSelector: '[data-phase5x-equity-provider-breadth="true"]',
      inspectProviderBreadth: true,
    });
    captures.aaplNews = await capture("aapl-news-provider-breadth", `${baseUrl}/?view=asset&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&mode=live-if-available&surface=news&compare=SPY`, {
      requiredText: ["AAPL"],
      inspectNews: true,
    });
    captures.btc = await capture("btcusdt-overview", `${baseUrl}/?view=asset&symbol=BTCUSDT&assetClass=crypto&interval=1h&range=5d&mode=live-if-available&compare=ETHUSDT`, {
      requiredText: ["BTCUSDT", "Funding"],
      waitForChart: true,
    });
    captures.unknown = await capture("unknown-symbol", `${baseUrl}/?view=asset&symbol=NOTAREAL123&assetClass=equity&mode=live-if-available`, {
      requiredText: ["unknown-symbol", "No verified workspace"],
    });
    captures.mobileFinancials = await capture("aapl-financials-mobile", `${baseUrl}/?view=asset&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&mode=live-if-available&surface=financials&compare=SPY`, {
      viewport: { width: 390, height: 844 },
      fullPage: true,
      requiredText: ["AAPL", "Free provider breadth"],
      waitForSelector: '[data-phase5x-equity-provider-breadth="true"]',
      inspectProviderBreadth: true,
    });
  }

  const report = { baseUrl, expectedRuntime, captures, captured_at: new Date().toISOString() };
  await writeFile(path.join(outputDirectory, "phase5x-provider-breadth-report.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function capture(name, url, options = {}) {
  const {
    requiredText = [],
    viewport = { width: 1600, height: 1000 },
    fullPage = false,
    waitForChart = false,
    waitForSelector = null,
    inspectProviderBreadth = false,
    inspectNews = false,
  } = options;
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120_000 });
    await page.waitForSelector("[data-runtime-health-state]", { state: "attached", timeout: 60_000 });
    if (waitForSelector) {
      await page.waitForSelector(waitForSelector, { timeout: 90_000 });
    }
    if (waitForChart) {
      await page.waitForFunction(() => document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") !== "loading", null, { timeout: 60_000 }).catch(() => {});
    }
    await page.waitForTimeout(500);
    const inspection = await page.evaluate(({ inspectProviderBreadth, inspectNews }) => {
      const chip = document.querySelector("[data-runtime-health-state]");
      const chart = document.querySelector("[data-chart-state]");
      const provider = document.querySelector('[data-phase5x-equity-provider-breadth="true"]');
      const text = document.body.textContent || "";
      return {
        runtimeState: chip?.getAttribute("data-runtime-health-state") || null,
        runtimeReachable: chip?.getAttribute("data-runtime-health-reachable") || null,
        chartState: chart?.getAttribute("data-chart-state") || null,
        chartPoints: Number(chart?.getAttribute("data-chart-points") || 0),
        providerBreadthVisible: Boolean(provider),
        providerBreadthText: inspectProviderBreadth ? provider?.textContent?.replace(/\s+/g, " ").trim().slice(0, 600) || "" : "",
        newsRows: inspectNews ? document.querySelectorAll(".symbol-news-grid article").length : null,
        scrollWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        text,
      };
    }, { inspectProviderBreadth, inspectNews });
    if (expectedRuntime === "online") {
      assert(inspection.runtimeReachable === "true", `${name}: expected runtime online, got ${inspection.runtimeReachable} (${inspection.runtimeState})`);
    }
    if (expectedRuntime === "offline") {
      assert(inspection.runtimeReachable === "false", `${name}: expected runtime offline, got ${inspection.runtimeReachable} (${inspection.runtimeState})`);
    }
    for (const marker of requiredText) {
      assert(inspection.text.includes(marker), `${name}: missing ${marker}`);
    }
    if (inspectProviderBreadth) {
      assert(inspection.providerBreadthVisible, `${name}: provider breadth panel missing`);
      assert(/Alpha Vantage|Finnhub/.test(inspection.providerBreadthText), `${name}: provider text missing Alpha Vantage/Finnhub`);
    }
    if (inspectNews) {
      assert(Number(inspection.newsRows || 0) > 0, `${name}: expected source-backed company/news rows`);
    }
    assert(inspection.scrollWidth <= inspection.viewportWidth + 1, `${name}: horizontal overflow ${inspection.scrollWidth}/${inspection.viewportWidth}`);
    assertErrorsEmpty(errors, name);
    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage, timeout: 120_000 });
    const screenshotBytes = (await stat(screenshot)).size;
    assert(screenshotBytes > 15_000, `${name}: screenshot unexpectedly small`);
    delete inspection.text;
    return { ...inspection, screenshot, screenshotBytes, url: page.url() };
  } finally {
    await page.close();
  }
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
