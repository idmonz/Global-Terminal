import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3051";
const scenario = String(process.env.PHASE6E_SCENARIO || "online").toLowerCase();
const runtimeMode = String(process.env.PHASE6E_RUNTIME_MODE || "cache");
const label = String(process.env.PHASE6E_LABEL || scenario).replace(/[^a-zA-Z0-9_-]/g, "_");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase6e_visual_${label}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  if (scenario === "online") {
    captures.assetDesktop = await captureAsset("AAPL", { width: 1600, height: 1000 }, false);
    captures.assetMobile = await captureAsset("TSLA", { width: 390, height: 844 }, true);
    captures.watchlist = await captureAdvancedWatchlist();
    captures.unknown = await captureUnknown();
  } else if (scenario === "offline") {
    captures.assetDesktop = await captureOffline("AAPL", { width: 1600, height: 1000 }, false);
    captures.assetMobile = await captureOffline("TSLA", { width: 390, height: 844 }, true);
  } else {
    throw new Error(`Unsupported PHASE6E_SCENARIO: ${scenario}`);
  }
  const report = { baseUrl, scenario, captured_at: new Date().toISOString(), captures };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureAsset(symbol, viewport, fullPage) {
  const name = `asset-${symbol.toLowerCase()}-${viewport.width < 600 ? "mobile" : "desktop"}`;
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  const responses = [];
  page.on("response", async (response) => {
    const url = response.url();
    if (url.includes("/api/runtime/") || url.startsWith(`${baseUrl}/?`)) {
      responses.push({
        url,
        status: response.status(),
        bytes: Number(response.headers()["content-length"] || 0),
      });
    }
  });
  try {
    const started = Date.now();
    await page.goto(
      `${baseUrl}/?view=asset&symbol=${symbol}&assetClass=equity&interval=1d&range=3mo&surface=overview&mode=${encodeURIComponent(runtimeMode)}`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-phase6e-progressive-workstation="true"]', { timeout: 120_000 });
    await page.waitForFunction(
      () => Number(document.querySelector("[data-phase6e-progressive-workstation]")?.getAttribute("data-panel-bytes") || 0) > 0
        && document.querySelectorAll(".progressive-chart-panel canvas").length > 0,
      null,
      { timeout: 120_000 },
    );
    const usefulMs = Date.now() - started;
    let observed = await observeAsset(page);
    assert(observed.symbol === symbol, `${name}: exact symbol mismatch`);
    assert(observed.summaryBytes < 50_000, `${name}: summary payload is ${observed.summaryBytes} bytes`);
    assert(observed.panelBytes < 80_000, `${name}: chart-core payload is ${observed.panelBytes} bytes`);
    assert(observed.chartRows > 0, `${name}: no chart rows`);
    assert(observed.canvasCount > 0, `${name}: chart canvas missing`);
    assert(!observed.horizontalOverflow, `${name}: page horizontal overflow`);
    assert(usefulMs < 1_500, `${name}: warm useful chart took ${usefulMs} ms`);

    await page.getByRole("button", { name: "Technicals", exact: true }).click();
    await page.waitForFunction(
      () => document.querySelector("[data-phase6e-progressive-workstation]")?.getAttribute("data-delivery-panel") === "technicals"
        && document.querySelectorAll(".progressive-analysis-grid canvas").length > 0,
      null,
      { timeout: 120_000 },
    );
    await page.getByRole("button", { name: "Financials", exact: true }).click();
    await waitForPanel(page, "financials");
    await page.getByRole("button", { name: "News", exact: true }).click();
    await waitForPanel(page, "news");
    await page.getByRole("button", { name: "Sources", exact: true }).click();
    await waitForPanel(page, "sources");
    await page.getByRole("button", { name: "Chart", exact: true }).click();
    await waitForPanel(page, "chart-core");
    observed = await observeAsset(page);
    const backgroundPrefetches = responses.filter((response) => response.url.includes("_rsc="));
    assert(observed.panelBytes < 80_000, `${name}: cached chart-core grew unexpectedly`);
    assert(backgroundPrefetches.length === 0, `${name}: ${backgroundPrefetches.length} unrelated RSC routes were prefetched`);
    assertErrorsEmpty(errors, name);
    return {
      ...observed,
      usefulMs,
      backgroundPrefetches: backgroundPrefetches.length,
      responses,
      screenshot: await screenshot(page, name, fullPage),
      url: page.url(),
    };
  } finally {
    await page.close();
  }
}

async function captureAdvancedWatchlist() {
  const name = "watchlist-advanced-desktop";
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  let panelRequests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/symbol-workstation/")) panelRequests += 1;
  });
  try {
    await page.goto(`${baseUrl}/?view=watchlist-desk&mode=fixture&list=fixture-daily&selected=AAPL`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-phase6d-watchlist-desk="true"]', { timeout: 120_000 });
    await page.waitForTimeout(500);
    panelRequests = 0;
    await page.getByRole("button", { name: "Performance", exact: true }).click();
    await page.getByLabel("Advanced watchlist controls").getByLabel("Sort").selectOption("metric-desc");
    await page.getByLabel("Advanced watchlist controls").getByLabel("Group").selectOption("sector");
    await page.getByRole("button", { name: "Risk", exact: true }).click();
    await page.getByRole("button", { name: "Technicals", exact: true }).first().click();
    await page.waitForTimeout(250);
    const observed = await page.evaluate(() => {
      const root = document.querySelector("[data-phase6d-watchlist-desk]");
      return {
        mode: root?.getAttribute("data-watchlist-view-mode"),
        sort: root?.getAttribute("data-watchlist-sort"),
        group: root?.getAttribute("data-watchlist-group"),
        fanout: root?.getAttribute("data-provider-fanout"),
        groups: document.querySelectorAll(".watchlist-group-heading").length,
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      };
    });
    assert(observed.mode === "technicals", `${name}: technical mode did not activate`);
    assert(observed.sort === "metric-desc", `${name}: sort state missing`);
    assert(observed.group === "sector" && observed.groups > 0, `${name}: grouping missing`);
    assert(observed.fanout === "false", `${name}: fan-out declaration missing`);
    assert(panelRequests === 0, `${name}: metric mode changes made ${panelRequests} provider-panel requests`);
    assert(!observed.horizontalOverflow, `${name}: horizontal overflow`);
    assertErrorsEmpty(errors, name);
    return { ...observed, panelRequests, screenshot: await screenshot(page, name, false) };
  } finally {
    await page.close();
  }
}

async function captureUnknown() {
  const name = "asset-unknown";
  const page = await browser.newPage({ viewport: { width: 1200, height: 820 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(`${baseUrl}/?view=asset&symbol=NOTAREAL123&assetClass=equity&mode=cache`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-symbol-workstation-state="unknown-symbol"]', { timeout: 120_000 });
    const body = await page.locator("body").innerText();
    assert(body.includes("No verified workspace for NOTAREAL123"), `${name}: unknown state missing`);
    assert(!body.includes("Apple Inc."), `${name}: AAPL fallback leaked`);
    assertErrorsEmpty(errors, name);
    return { screenshot: await screenshot(page, name, false), url: page.url() };
  } finally {
    await page.close();
  }
}

async function captureOffline(symbol, viewport, fullPage) {
  const name = `asset-${symbol.toLowerCase()}-offline-${viewport.width < 600 ? "mobile" : "desktop"}`;
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.route(/\/api\/runtime\//, (route) => route.abort("internetdisconnected"));
    await page.goto(
      `${baseUrl}/?view=asset&symbol=${symbol}&assetClass=equity&interval=1d&range=3mo&surface=overview&mode=fixture`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-phase6e-progressive-workstation="true"]', { timeout: 120_000 });
    await page.waitForTimeout(700);
    const observed = await observeAsset(page);
    const body = await page.locator("body").innerText();
    assert(observed.symbol === symbol, `${name}: fixture identity mismatch`);
    assert(observed.panelBytes === 0, `${name}: offline panel falsely loaded`);
    assert(body.includes("unavailable") || body.includes("offline"), `${name}: honest offline state missing`);
    assert(!observed.horizontalOverflow, `${name}: horizontal overflow`);
    errors.console = errors.console.filter((entry) => entry.includes("ERR_FAILED") || entry.includes("ERR_INTERNET_DISCONNECTED") ? false : true);
    assertErrorsEmpty(errors, name);
    return { ...observed, screenshot: await screenshot(page, name, fullPage), url: page.url() };
  } finally {
    await page.close();
  }
}

async function waitForPanel(page, panel) {
  await page.waitForFunction(
    (expected) => document.querySelector("[data-phase6e-progressive-workstation]")?.getAttribute("data-delivery-panel") === expected
      && Number(document.querySelector("[data-phase6e-progressive-workstation]")?.getAttribute("data-panel-bytes") || 0) > 0,
    panel,
    { timeout: 120_000 },
  );
}

async function observeAsset(page) {
  return page.evaluate(() => {
    const root = document.querySelector("[data-phase6e-progressive-workstation]");
    const chart = document.querySelector(".progressive-chart-panel");
    const paints = performance.getEntriesByType("paint").map((entry) => ({ name: entry.name, startTime: Math.round(entry.startTime) }));
    return {
      symbol: root?.getAttribute("data-symbol"),
      delivery: root?.getAttribute("data-delivery-panel"),
      summaryBytes: Number(root?.getAttribute("data-summary-bytes") || 0),
      panelBytes: Number(root?.getAttribute("data-panel-bytes") || 0),
      runtimeBoundary: root?.getAttribute("data-runtime-boundary"),
      chartRows: Number(chart?.getAttribute("data-chart-rows") || 0),
      canvasCount: document.querySelectorAll("canvas").length,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      paints,
    };
  });
}

async function screenshot(page, name, fullPage) {
  const filename = path.join(outputDirectory, `${name}.png`);
  await page.screenshot({ path: filename, fullPage });
  const bytes = (await stat(filename)).size;
  assert(bytes > 15_000, `${name}: screenshot unexpectedly small`);
  return { path: filename, bytes };
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
