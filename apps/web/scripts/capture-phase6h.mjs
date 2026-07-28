import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3053";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6h_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.desktop = await captureDesktop();
  captures.live = await captureLiveData();
  captures.mobile = await captureMobileLazy();
  captures.layout = await captureLayoutRestore();
  captures.synchronization = await captureSynchronization();
  captures.journey = await captureChangeJourney();
  captures.unknown = await captureUnknown();
  captures.lkg = await captureLastKnownGood();
  captures.slow = await captureSlowPanel();
  const report = { baseUrl, captured_at: new Date().toISOString(), captures };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureDesktop() {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  const requests = trackPanelRequests(page);
  const rsc = [];
  page.on("request", (request) => {
    if (request.url().includes("_rsc=")) rsc.push(request.url());
  });
  try {
    const response = await page.goto(workspaceUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    const htmlBytes = Buffer.byteLength(await response.text());
    await page.waitForSelector('[data-phase6h-analyst-workspace="true"]', { timeout: 120_000 });
    await page.waitForSelector('[data-panel="chart-core"] canvas', { timeout: 120_000 });
    await page.waitForFunction(() => document.querySelectorAll(".analyst-desktop-grid .analyst-panel").length === 4);
    await page.waitForTimeout(800);
    const state = await observe(page);
    const unique = new Set(requests);
    assert(state.symbol === "AAPL", "desktop: exact symbol changed");
    assert(state.chartRows > 20, "desktop: useful chart rows missing");
    assert(state.desktopPanels === 4, "desktop: expected four simultaneous evidence panels");
    assert(requests.length <= 3, `desktop: expected at most three secondary requests, got ${requests.length}`);
    assert(unique.size === requests.length, "desktop: concurrent panel requests were not deduplicated");
    assert(rsc.length === 0, `desktop: unexpected RSC prefetches ${rsc.length}`);
    assert(htmlBytes < 100_000, `desktop: initial HTML ${htmlBytes} exceeds 100 KB`);
    assert(!state.horizontalOverflow, "desktop: horizontal overflow");
    const accessibility = await assertAccessible(page, "desktop");
    assertErrorsEmpty(errors, "desktop");
    return {
      ...state,
      htmlBytes,
      panelRequests: requests,
      rscRequests: rsc.length,
      accessibility,
      screenshot: await screenshot(page, "analyst-workspace-desktop", false),
    };
  } finally {
    await page.close();
  }
}

async function captureLiveData() {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  const requests = trackPanelRequests(page);
  try {
    const url = `${baseUrl}/?view=analyst-workspace&mode=live-if-available&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&layout=research&panel=chart-core`;
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector('[data-phase6h-analyst-workspace="true"]', { timeout: 120_000 });
    await page.waitForFunction(() => document.querySelector('[data-panel="chart-core"]')?.getAttribute("data-panel-status") === "ready");
    await page.waitForFunction(() => {
      const panel = document.querySelector('[data-panel="chart-core"]');
      return (panel?.textContent || "").includes("yfinance");
    });
    await page.waitForFunction(() => [...document.querySelectorAll(".analyst-desktop-grid .analyst-panel")].every((panel) => ["ready", "last-known-good"].includes(panel.getAttribute("data-panel-status"))));
    await page.waitForTimeout(500);
    const state = await observe(page);
    const chartText = await page.locator('[data-panel="chart-core"]').innerText();
    assert(chartText.includes("live/fresh") || chartText.includes("cached"), "live: honest source state missing");
    assert(state.chartRows > 20, "live: verified chart rows missing");
    assert(requests.some((url) => url.includes("/AAPL/panels/chart-core")), "live: saved primary was not revalidated");
    assert(!state.horizontalOverflow, "live: horizontal overflow");
    assertErrorsEmpty(errors, "live");
    return {
      ...state,
      panelRequests: requests,
      chartSource: chartText.split("\n").slice(0, 12),
      screenshot: await screenshot(page, "analyst-workspace-live-aapl", false),
    };
  } finally {
    await page.close();
  }
}

async function captureMobileLazy() {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  const requests = trackPanelRequests(page);
  try {
    await page.goto(workspaceUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector('[data-phase6h-analyst-workspace="true"]', { timeout: 120_000 });
    await page.waitForSelector('[data-panel="chart-core"] canvas', { timeout: 120_000 });
    await page.waitForTimeout(350);
    const before = [...requests];
    assert(before.length === 0, `mobile: hidden panels eagerly fetched ${before.join(", ")}`);
    await page.getByRole("button", { name: /Financials panel/ }).click();
    await page.waitForSelector('[data-panel="financials"]', { timeout: 120_000 });
    await page.waitForFunction(() => {
      const panel = document.querySelector('[data-panel="financials"]');
      return panel?.getAttribute("data-panel-status") === "ready";
    });
    const state = await observe(page);
    assert(requests.length === 1 && requests[0].includes("/financials"), `mobile: expected one selected panel request, got ${requests.join(", ")}`);
    assert(state.desktopPanels === 0, "mobile: desktop pane grid remained visible");
    assert(!state.horizontalOverflow, "mobile: horizontal overflow");
    const accessibility = await assertAccessible(page, "mobile");
    assertErrorsEmpty(errors, "mobile");
    return {
      ...state,
      requestsBeforeAction: before,
      requestsAfterAction: requests,
      accessibility,
      screenshot: await screenshot(page, "analyst-workspace-mobile", true),
    };
  } finally {
    await page.close();
  }
}

async function captureLayoutRestore() {
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();
  const errors = listenForErrors(page);
  try {
    await page.goto(workspaceUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector("#analyst-split");
    await page.locator("#analyst-split").fill("64");
    await page.getByRole("button", { name: "Save layout locally" }).click();
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-phase6h-analyst-workspace="true"]');
    await page.waitForTimeout(100);
    const restored = await page.locator("#analyst-split").inputValue();
    assert(restored === "64", `layout: expected split 64, got ${restored}`);
    assertErrorsEmpty(errors, "layout");
    return {
      restoredSplit: restored,
      screenshot: await screenshot(page, "analyst-layout-restored", false),
    };
  } finally {
    await context.close();
  }
}

async function captureSynchronization() {
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  const requests = trackPanelRequests(page);
  try {
    await page.goto(workspaceUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector('[data-panel="chart-core"] canvas', { timeout: 120_000 });
    await page.waitForTimeout(500);
    const beforeSwitch = requests.length;
    await page.locator("#analyst-symbol-input").fill("TSLA");
    await page.getByRole("button", { name: "Open exact symbol workspace" }).click();
    await page.waitForFunction(() => document.querySelector("[data-phase6h-analyst-workspace]")?.getAttribute("data-symbol") === "TSLA");
    await page.waitForFunction(() => [...document.querySelectorAll(".analyst-desktop-grid .analyst-panel")].every((panel) => panel.getAttribute("data-panel-status") === "ready"));
    const switchRequests = requests.slice(beforeSwitch);
    assert(switchRequests.length >= 1, "synchronization: symbol switch made no exact panel request");
    assert(switchRequests.every((url) => url.includes("/TSLA/")), `synchronization: cross-symbol request ${switchRequests.join(", ")}`);

    const beforeInterval = requests.length;
    await page.getByLabel("Workspace interval").selectOption("1h");
    await page.waitForFunction(() => new URL(window.location.href).searchParams.get("interval") === "1h");
    await page.waitForTimeout(500);
    const intervalRequests = requests.slice(beforeInterval);
    assert(intervalRequests.length === 1, `synchronization: interval change requested ${intervalRequests.length} panels`);
    assert(intervalRequests[0].includes("/TSLA/panels/chart-core"), "synchronization: interval did not update exact TSLA chart");
    assertErrorsEmpty(errors, "synchronization");
    return {
      switchRequests,
      intervalRequests,
      screenshot: await screenshot(page, "analyst-symbol-timeframe-synchronized", false),
    };
  } finally {
    await page.close();
  }
}

async function captureChangeJourney() {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(changesUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector(".change-evidence-panel", { timeout: 120_000 });
    await page.getByLabel("Type").selectOption("event");
    await page.locator(".change-inbox-row").first().click();
    const selected = await page.locator("[data-phase6d-watchlist-desk]").getAttribute("data-watchlist-selected-change");
    await page.getByRole("link", { name: /Open exact catalysts analysis/ }).click();
    await page.waitForSelector('[data-phase6h-analyst-workspace="true"]', { timeout: 120_000 });
    const workspaceState = await page.evaluate(() => {
      const root = document.querySelector("[data-phase6h-analyst-workspace]");
      return {
        symbol: root?.getAttribute("data-symbol"),
        panel: root?.getAttribute("data-focused-panel"),
        text: document.querySelector(".analyst-workspace-rail")?.textContent || "",
      };
    });
    assert(workspaceState.symbol === "AAPL", "journey: exact symbol changed");
    assert(workspaceState.panel === "catalysts", "journey: event did not map to catalysts");
    assert(workspaceState.text.includes("scheduled-earnings"), "journey: saved change evidence missing");
    const workspaceScreenshot = await screenshot(page, "change-to-analyst-workspace", false);
    await page.getByRole("link", { name: "Return to Change Inbox", exact: true }).first().click();
    await page.waitForSelector('[data-watchlist-view-mode="changes"]', { timeout: 120_000 });
    const returned = await page.evaluate(() => {
      const root = document.querySelector("[data-phase6d-watchlist-desk]");
      return {
        type: root?.getAttribute("data-watchlist-change-type"),
        change: root?.getAttribute("data-watchlist-selected-change"),
      };
    });
    assert(returned.type === "event", "journey: change filter not restored");
    assert(returned.change === selected, "journey: selected change not restored");
    assertErrorsEmpty(errors, "journey");
    return {
      workspaceState,
      returned,
      workspaceScreenshot,
      returnedScreenshot: await screenshot(page, "analyst-returned-change-inbox", false),
    };
  } finally {
    await page.close();
  }
}

async function captureUnknown() {
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(`${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=NOTAREAL123&assetClass=equity`, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector(".unknown-symbol-state", { timeout: 120_000 });
    const body = await page.locator("body").innerText();
    assert(!body.includes("Apple"), "unknown: AAPL fallback leaked");
    assert(body.includes("NOTAREAL123"), "unknown: requested symbol missing");
    assertErrorsEmpty(errors, "unknown");
    return { screenshot: await screenshot(page, "analyst-unknown-symbol", false) };
  } finally {
    await page.close();
  }
}

async function captureLastKnownGood() {
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(
      `${baseUrl}/?view=analyst-workspace&mode=cache&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&layout=research&panel=chart-core`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-panel="chart-core"] canvas', { timeout: 120_000 });
    const jobId = "research_refresh_0123456789ab";
    const completed = {
      contract_version: "phase_2b.v1",
      payload_type: "research_refresh_job",
      generated_at: new Date().toISOString(),
      data: {
        job_id: jobId,
        symbol: "AAPL",
        status: "completed",
        progress: { current: 1, total: 1, percent: 100 },
        actual_calls: 1,
      },
      summary: { status: "completed" },
      source_status: [],
      unavailable: [],
      errors: [],
      caveats: [],
    };
    await page.route(
      /\/api\/runtime\/api\/analyst-workspace\/AAPL\/refresh/,
      (route) =>
        route.fulfill({
          status: 202,
          contentType: "application/json",
          body: JSON.stringify(completed),
        }),
    );
    await page.route(
      new RegExp(`/api/runtime/api/research-operations/jobs/${jobId}`),
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(completed),
        }),
    );
    await page
      .getByRole("button", { name: "Queue bounded refresh for chart-core" })
      .click();
    await page.waitForFunction(() =>
      document
        .querySelector(".analyst-operation-status")
        ?.textContent?.includes("completed"),
    );
    const state = await observe(page);
    assert(state.chartRows > 20, "bounded refresh: saved chart disappeared");
    assertErrorsEmpty(errors, "bounded-refresh-retention");
    return {
      ...state,
      screenshot: await screenshot(
        page,
        "analyst-panel-retained-after-bounded-refresh",
        false,
      ),
    };
  } finally {
    await page.close();
  }
}

async function captureSlowPanel() {
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  await page.route(/\/api\/runtime\/api\/symbol-workstation\/AAPL\/panels\/financials/, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    await route.continue();
  });
  try {
    await page.goto(workspaceUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector('[data-panel="chart-core"] canvas', { timeout: 120_000 });
    const before = await page.locator('[data-panel="chart-core"]').boundingBox();
    await page.waitForFunction(() => document.querySelector('[data-panel="financials"]')?.getAttribute("data-panel-status") === "ready");
    const after = await page.locator('[data-panel="chart-core"]').boundingBox();
    assert(before && after, "slow: chart bounds unavailable");
    assert(Math.abs(before.width - after.width) < 2 && Math.abs(before.height - after.height) < 2, "slow: chart pane shifted while secondary loaded");
    assertErrorsEmpty(errors, "slow");
    return {
      before,
      after,
      screenshot: await screenshot(page, "analyst-slow-secondary-stable", false),
    };
  } finally {
    await page.close();
  }
}

function workspaceUrl() {
  return `${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&layout=research&panel=chart-core`;
}

function changesUrl() {
  return `${baseUrl}/?view=watchlist-desk&mode=fixture&list=fixture-daily&selected=AAPL&watchMode=changes&sort=manual&group=none&panel=chart`;
}

function trackPanelRequests(page) {
  const requests = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/runtime/api/symbol-workstation/") && request.url().includes("/panels/")) {
      requests.push(request.url());
    }
  });
  return requests;
}

async function observe(page) {
  return page.evaluate(() => {
    const root = document.querySelector("[data-phase6h-analyst-workspace]");
    return {
      symbol: root?.getAttribute("data-symbol"),
      focusedPanel: root?.getAttribute("data-focused-panel"),
      layout: root?.getAttribute("data-layout"),
      desktopPanels: document.querySelectorAll(".analyst-desktop-grid .analyst-panel").length,
      chartRows: Number(document.querySelector('[data-panel="chart-core"] .progressive-chart-panel')?.getAttribute("data-chart-rows") || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
}

async function assertAccessible(page, label) {
  const audit = await page.evaluate(() => {
    const ids = [...document.querySelectorAll("[id]")].map((element) => element.id).filter(Boolean);
    const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
    const controls = [...document.querySelectorAll("button, a[href], input, select")];
    const unlabeled = controls.filter((element) => {
      const explicit = element.id ? document.querySelector(`label[for="${CSS.escape(element.id)}"]`)?.textContent?.trim() : "";
      return !(element.getAttribute("aria-label")?.trim() || element.getAttribute("title")?.trim() || element.textContent?.trim() || explicit || element.closest("label")?.textContent?.trim());
    }).map((element) => element.outerHTML.slice(0, 160));
    return { duplicateIds: [...new Set(duplicateIds)], unlabeled, controlCount: controls.length };
  });
  assert(!audit.duplicateIds.length, `${label}: duplicate IDs ${audit.duplicateIds.join(", ")}`);
  assert(!audit.unlabeled.length, `${label}: unlabeled controls ${audit.unlabeled.join(" | ")}`);
  const target = page.getByRole("button", { name: /Chart panel/ });
  await target.focus();
  const focus = await target.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outline: style.outlineStyle, width: style.outlineWidth, shadow: style.boxShadow };
  });
  assert((focus.outline !== "none" && focus.width !== "0px") || focus.shadow !== "none", `${label}: focus indicator missing`);
  return audit;
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
  page.on("pageerror", (error) => errors.page.push(error.message));
  return errors;
}

function assertErrorsEmpty(errors, label) {
  assert(!errors.console.length, `${label}: console errors ${errors.console.join(" | ")}`);
  assert(!errors.page.length, `${label}: page errors ${errors.page.join(" | ")}`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
