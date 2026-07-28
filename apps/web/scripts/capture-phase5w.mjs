import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5w_runtime_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";
const expectedRuntime = process.env.GT_EXPECT_RUNTIME || "any";

await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.home = await capture("home-runtime", `${baseUrl}/?view=home&mode=live-if-available`, {
    requiredText: ["Runtime API", "Markets, risk and news"],
  });
  captures.asset = await capture("aapl-runtime", `${baseUrl}/?view=asset&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&mode=live-if-available&chartType=candlestick&compare=SPY`, {
    requiredText: ["Runtime API", "AAPL"],
    waitForChart: true,
  });
  captures.mapHttp = await fetchMarker("map-runtime-http", `${baseUrl}/?view=war-room-map&mode=cache`, ["Runtime API", "Global Terminal"]);
  captures.btcHttp = await fetchMarker("btcusdt-runtime-http", `${baseUrl}/?view=asset&symbol=BTCUSDT&assetClass=crypto&interval=1h&range=5d&mode=cache&compare=ETHUSDT`, ["Runtime API", "BTCUSDT"]);

  const report = { baseUrl, expectedRuntime, captures, captured_at: new Date().toISOString() };
  await writeFile(path.join(outputDirectory, "phase5w-runtime-report.json"), JSON.stringify(report, null, 2), "utf8");
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
  } = options;
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120_000 });
    await page.waitForSelector("[data-runtime-health-state]", { state: "attached", timeout: 60_000 });
    if (waitForChart) {
      await page.waitForFunction(() => document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") !== "loading", null, { timeout: 60_000 }).catch(() => {});
    }
    await page.waitForTimeout(350);
    const inspection = await evaluateWithNavigationRetry(page, () => {
      const chip = document.querySelector("[data-runtime-health-state]");
      const chart = document.querySelector("[data-chart-state]");
      const text = document.body.textContent || "";
      return {
        runtimeState: chip?.getAttribute("data-runtime-health-state") || null,
        runtimeReachable: chip?.getAttribute("data-runtime-health-reachable") || null,
        runtimeText: chip?.textContent?.replace(/\s+/g, " ").trim() || "",
        chartState: chart?.getAttribute("data-chart-state") || null,
        chartPoints: Number(chart?.getAttribute("data-chart-points") || 0),
        scrollWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        text,
      };
    });

    if (expectedRuntime === "online") {
      assert(inspection.runtimeReachable === "true", `${name}: expected runtime online, got ${inspection.runtimeReachable} (${inspection.runtimeState})`);
    }
    if (expectedRuntime === "offline") {
      assert(inspection.runtimeReachable === "false", `${name}: expected runtime offline, got ${inspection.runtimeReachable} (${inspection.runtimeState})`);
    }
    for (const marker of requiredText) {
      assert(inspection.text.includes(marker), `${name}: missing ${marker}`);
    }
    assert(inspection.runtimeText.includes("Runtime API"), `${name}: runtime chip text missing`);
    assert(inspection.scrollWidth <= inspection.viewportWidth, `${name}: horizontal overflow ${inspection.scrollWidth}/${inspection.viewportWidth}`);
    assertErrorsEmpty(errors, name);

    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage, timeout: 120_000 });
    const screenshotBytes = (await stat(screenshot)).size;
    assert(screenshotBytes > 12_000, `${name}: screenshot unexpectedly small`);
    delete inspection.text;
    return { ...inspection, screenshot, screenshotBytes, url: page.url() };
  } finally {
    await page.close();
  }
}

async function fetchMarker(name, url, markers) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45_000);
  try {
    const response = await fetch(url, { signal: controller.signal });
    const text = await response.text();
    assert(response.status === 200, `${name}: HTTP ${response.status}`);
    for (const marker of markers) {
      assert(text.includes(marker), `${name}: missing ${marker}`);
    }
    if (expectedRuntime === "online") {
      assert(text.includes("data-runtime-health-reachable=\"true\""), `${name}: runtime did not render online`);
    }
    if (expectedRuntime === "offline") {
      assert(text.includes("data-runtime-health-reachable=\"false\""), `${name}: runtime did not render offline`);
    }
    return {
      url,
      status: response.status,
      bytes: text.length,
      runtimeReachable: text.includes("data-runtime-health-reachable=\"true\""),
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function evaluateWithNavigationRetry(page, fn) {
  let lastError;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      return await page.evaluate(fn);
    } catch (error) {
      lastError = error;
      if (!String(error?.message || error).includes("Execution context was destroyed")) {
        throw error;
      }
      await page.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
      await page.waitForSelector("[data-runtime-health-state]", { state: "attached", timeout: 30_000 });
      await page.waitForTimeout(300);
    }
  }
  throw lastError;
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
