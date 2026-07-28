import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3047";
const scenario = String(process.env.PHASE6D_SCENARIO || "online").toLowerCase();
const label = String(process.env.PHASE6D_LABEL || scenario).replace(/[^a-zA-Z0-9_-]/g, "_");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase6d_visual_${label}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  if (scenario === "online") {
    captures.desktop = await captureOnlineDesktop();
    captures.mobile = await captureMobile();
    captures.failure = await captureUnknownSymbol();
  } else if (scenario === "offline") {
    captures.desktop = await captureOfflineDesktop();
    captures.mobile = await captureOfflineMobile();
  } else {
    throw new Error(`Unsupported PHASE6D_SCENARIO: ${scenario}`);
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

async function captureOnlineDesktop() {
  const name = "watchlist-desk-online-desktop";
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(`${baseUrl}/?view=watchlist-desk&mode=local&list=primary&selected=TSLA`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-phase6d-watchlist-desk="true"]', { timeout: 120_000 });
    await waitForChart(page);
    let observed = await observe(page);
    assert(observed.itemCount === 5, `${name}: expected five watchlist symbols, got ${observed.itemCount}`);
    assert(observed.selected === "TSLA", `${name}: initial exact symbol mismatch`);
    assert(observed.chartState === "ready", `${name}: initial chart is not ready`);
    assert(observed.canvasCount > 0, `${name}: chart canvas missing`);
    assert(observed.materializationStatus === "completed", `${name}: materialization ledger is not completed`);
    assert(!observed.privateTextVisible, `${name}: private note leaked into rendered text`);
    assert(!observed.privateTextInUrl, `${name}: private note leaked into URL`);
    assert(!observed.horizontalOverflow, `${name}: page-level horizontal overflow`);

    await page.locator('[data-watchlist-symbol="JNJ"] .watchlist-symbol-select').click();
    await page.waitForFunction(
      () => document.querySelector("[data-phase6d-watchlist-desk]")?.getAttribute("data-selected-symbol") === "JNJ",
    );
    await waitForChart(page);
    observed = await observe(page);
    assert(observed.selected === "JNJ", `${name}: click did not switch exact symbol`);
    assert(new URL(page.url()).searchParams.get("selected") === "JNJ", `${name}: selected URL state was not preserved`);
    assert(new URL(page.url()).searchParams.get("view") === "watchlist-desk", `${name}: symbol switch caused a full-workstation route`);

    await page.getByRole("button", { name: "Financials", exact: true }).click();
    await page.waitForSelector("[data-watchlist-financial-state]", { timeout: 120_000 });
    const financialState = await page.locator("[data-watchlist-financial-state]").getAttribute("data-watchlist-financial-state");
    assert(Boolean(financialState), `${name}: financial delivery state missing`);

    await page.getByRole("button", { name: "News", exact: true }).click();
    await page.waitForSelector("[data-watchlist-news-count]", { timeout: 120_000 });
    const newsCount = Number(await page.locator("[data-watchlist-news-count]").getAttribute("data-watchlist-news-count") || 0);

    await page.getByRole("button", { name: "Sources", exact: true }).click();
    await page.waitForSelector("[data-watchlist-source-count]", { timeout: 120_000 });
    const sourceCount = Number(await page.locator("[data-watchlist-source-count]").getAttribute("data-watchlist-source-count") || 0);
    assert(sourceCount > 0, `${name}: exact provenance ledger is empty`);

    await page.getByRole("button", { name: "Chart", exact: true }).click();
    await waitForChart(page);
    await page.waitForTimeout(300);
    assertErrorsEmpty(errors, name);
    const screenshotResult = await captureScreenshot(page, name, false);
    return {
      ...observed,
      financialState,
      newsCount,
      sourceCount,
      screenshot: screenshotResult,
      url: page.url(),
    };
  } finally {
    await page.close();
  }
}

async function captureMobile() {
  const name = "watchlist-desk-online-mobile";
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(`${baseUrl}/?view=watchlist-desk&mode=local&list=primary&selected=AAPL`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-phase6d-watchlist-desk="true"]', { timeout: 120_000 });
    await waitForChart(page);
    const observed = await observe(page);
    assert(observed.itemCount === 5, `${name}: expected five symbols`);
    assert(observed.selected === "AAPL", `${name}: mobile exact symbol mismatch`);
    assert(!observed.horizontalOverflow, `${name}: mobile page-level overflow`);
    assert(observed.canvasToOpsGap >= 24, `${name}: chart overlaps the operations rail (${observed.canvasToOpsGap}px)`);
    assert(!observed.privateTextVisible, `${name}: private text leaked`);
    assertErrorsEmpty(errors, name);
    const screenshotResult = await captureScreenshot(page, name, true);
    return { ...observed, screenshot: screenshotResult, url: page.url() };
  } finally {
    await page.close();
  }
}

async function captureUnknownSymbol() {
  const name = "watchlist-desk-unknown-symbol";
  const page = await browser.newPage({ viewport: { width: 1200, height: 850 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  const secret = "PHASE6D_PRIVATE_BROWSER_SENTINEL";
  try {
    await page.goto(`${baseUrl}/?view=watchlist-desk&mode=local&list=primary&selected=AAPL`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector(".watchlist-add-form");
    await page.locator('input[name="symbol"]').fill("NOTAREAL123");
    await page.locator('input[name="private_reason"]').fill(secret);
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await page.waitForSelector(".watchlist-message", { timeout: 120_000 });
    const observed = await observe(page, secret);
    assert(observed.itemCount === 5, `${name}: unknown symbol mutated the list`);
    assert(!observed.privateTextVisible, `${name}: submitted private note leaked into DOM`);
    assert(!observed.privateTextInUrl, `${name}: submitted private note leaked into URL`);
    assert(!observed.bodyText.includes("Apple Inc. added"), `${name}: unknown symbol fell back to Apple`);
    errors.console = errors.console.filter((entry) => !entry.includes("422 (Unprocessable Content)"));
    assertErrorsEmpty(errors, name);
    const screenshotResult = await captureScreenshot(page, name, false);
    delete observed.bodyText;
    return { ...observed, screenshot: screenshotResult, url: page.url() };
  } finally {
    await page.close();
  }
}

async function captureOfflineDesktop() {
  return captureOffline("watchlist-desk-offline-desktop", { width: 1600, height: 1000 }, false);
}

async function captureOfflineMobile() {
  return captureOffline("watchlist-desk-offline-mobile", { width: 390, height: 844 }, true);
}

async function captureOffline(name, viewport, fullPage) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.route(/\/api\/symbol-workstation\//, (route) => route.abort("internetdisconnected"));
    await page.goto(`${baseUrl}/?view=watchlist-desk&mode=fixture&selected=TSLA`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-phase6d-watchlist-desk="true"]', { timeout: 120_000 });
    await page.waitForTimeout(800);
    const observed = await observe(page);
    assert(observed.itemCount === 5, `${name}: deterministic fixture list is incomplete`);
    assert(observed.selected === "TSLA", `${name}: deterministic selection mismatch`);
    assert(observed.chartState === "unavailable", `${name}: offline fixture falsely claims a chart`);
    assert(observed.bodyText.includes("Runtime API is offline") || observed.bodyText.includes("initial exact-symbol panel is unavailable"), `${name}: honest offline state missing`);
    assert(!observed.horizontalOverflow, `${name}: page-level overflow`);
    assert(!observed.privateTextVisible, `${name}: private text leaked`);
    errors.console = errors.console.filter((entry) => !entry.includes("ERR_INTERNET_DISCONNECTED"));
    assertErrorsEmpty(errors, name);
    const screenshotResult = await captureScreenshot(page, name, fullPage);
    delete observed.bodyText;
    return { ...observed, screenshot: screenshotResult, url: page.url() };
  } finally {
    await page.close();
  }
}

async function waitForChart(page) {
  await page.waitForFunction(
    () => document.querySelector("[data-watchlist-chart-state]")?.getAttribute("data-watchlist-chart-state") === "ready"
      && document.querySelectorAll("canvas").length > 0,
    null,
    { timeout: 120_000 },
  );
}

async function observe(page, privateSentinel = "phase6d-local-private-qa") {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      return await page.evaluate((sentinel) => {
        const root = document.querySelector("[data-phase6d-watchlist-desk]");
        const chart = document.querySelector("[data-watchlist-chart-state]");
        const chartContent = document.querySelector(".watchlist-chart-panel .finance-chart-shell");
        const chartContainer = document.querySelector(".watchlist-chart-panel .finance-chart-container");
        const ops = document.querySelector(".watchlist-ops-rail");
        const chartRect = chartContent?.getBoundingClientRect();
        const containerRect = chartContainer?.getBoundingClientRect();
        const canvasBottom = Math.max(
          0,
          ...Array.from(document.querySelectorAll(".watchlist-chart-panel canvas"))
            .map((node) => node.getBoundingClientRect().bottom),
        );
        const opsRect = ops?.getBoundingClientRect();
        const bodyText = document.body.innerText;
        return {
          itemCount: Number(root?.getAttribute("data-watchlist-item-count") || 0),
          selected: root?.getAttribute("data-selected-symbol"),
          chartState: chart?.getAttribute("data-watchlist-chart-state") || "unavailable",
          panel: root?.getAttribute("data-panel-delivery"),
          panelBytes: Number(root?.getAttribute("data-panel-bytes") || 0),
          materializationStatus: root?.getAttribute("data-materialization-status"),
          canvasCount: document.querySelectorAll("canvas").length,
          chartToOpsGap: chartRect && opsRect ? Math.round(opsRect.top - chartRect.bottom) : 0,
          canvasToOpsGap: opsRect ? Math.round(opsRect.top - canvasBottom) : 0,
          chartShellHeight: Math.round(chartRect?.height || 0),
          chartContainerHeight: Math.round(containerRect?.height || 0),
          horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
          privateTextVisible: bodyText.includes(sentinel),
          privateTextInUrl: window.location.href.includes(sentinel) || window.location.href.includes("private_reason"),
          bodyText,
        };
      }, privateSentinel);
    } catch (error) {
      if (!String(error).includes("Execution context was destroyed") || attempt === 3) throw error;
      await page.waitForTimeout(300);
      await page.waitForSelector('[data-phase6d-watchlist-desk="true"]', { timeout: 120_000 });
    }
  }
  throw new Error("Unable to observe the watchlist desk.");
}

async function captureScreenshot(page, name, fullPage) {
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
