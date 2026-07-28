import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3051";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6f_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.desktop = await captureWatchlist({ width: 1600, height: 1000 }, "desktop");
  captures.mobile = await captureWatchlist({ width: 390, height: 844 }, "mobile");
  captures.journey = await captureExactJourney();
  captures.failure = await captureCatalystFailure();
  captures.offline = await captureOfflineSnapshot();
  const report = { baseUrl, captured_at: new Date().toISOString(), captures };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureOfflineSnapshot() {
  const label = "api-offline-saved-snapshot";
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.route(/127\.0\.0\.1:\d+\/api\//, async (route) => {
      await route.abort("internetdisconnected");
    });
    await page.route(/\/api\/runtime\//, async (route) => {
      await route.abort("internetdisconnected");
    });
    await page.goto(
      `${baseUrl}/?view=watchlist-desk&mode=fixture&list=fixture-daily&selected=TSLA&watchMode=catalysts&sort=manual&group=none&panel=catalysts`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-watchlist-catalyst-count]', { timeout: 120_000 });
    await page.waitForSelector(".watchlist-message", { timeout: 120_000 });
    const state = await observe(page);
    const body = await page.locator("body").innerText();
    assert(state.symbol === "TSLA", `${label}: exact identity changed`);
    assert(state.catalystCount > 0, `${label}: saved snapshot disappeared offline`);
    assert(body.includes("saved Research Snapshot remains visible"), `${label}: offline fallback message missing`);
    assert(!state.horizontalOverflow, `${label}: horizontal overflow`);
    errors.console = errors.console.filter((entry) => (
      entry.includes("ERR_FAILED")
      || entry.includes("ERR_INTERNET_DISCONNECTED")
      || entry.includes("Failed to load resource")
    ) ? false : true);
    assertErrorsEmpty(errors, label);
    return {
      ...state,
      screenshot: await screenshot(page, label, true),
      url: page.url(),
    };
  } finally {
    await page.close();
  }
}

async function captureWatchlist(viewport, label) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  let panelRequests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/symbol-workstation/")) panelRequests += 1;
  });
  try {
    await page.goto(
      `${baseUrl}/?view=watchlist-desk&mode=fixture&list=fixture-daily&selected=AAPL&watchMode=price&sort=manual&group=none&panel=chart`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-phase6d-watchlist-desk="true"]', { timeout: 120_000 });
    await page.waitForTimeout(600);
    const advanced = page.getByLabel("Advanced watchlist controls");
    panelRequests = 0;
    for (const mode of ["Performance", "Financials", "Risk", "Technicals", "Catalysts"]) {
      await advanced.getByRole("button", { name: mode, exact: true }).click();
    }
    await advanced.getByLabel("Sort").selectOption("metric-asc");
    await advanced.getByLabel("Group").selectOption("sector");
    await page.waitForTimeout(150);
    assert(panelRequests === 0, `${label}: list modes made ${panelRequests} exact-panel requests`);

    await page.getByLabel("Selected symbol panels").getByRole("button", { name: "Catalysts", exact: true }).click();
    await page.locator('[data-watchlist-symbol="TSLA"] .watchlist-symbol-select').click();
    await page.waitForFunction(
      () => document.querySelector("[data-phase6d-watchlist-desk]")?.getAttribute("data-selected-symbol") === "TSLA",
      null,
      { timeout: 30_000 },
    );
    await page.waitForFunction(
      () => Number(document.querySelector("[data-watchlist-catalyst-count]")?.getAttribute("data-watchlist-catalyst-count") || 0) > 0,
      null,
      { timeout: 30_000 },
    );
    const state = await observe(page);
    assert(state.symbol === "TSLA", `${label}: exact TSLA selection missing`);
    assert(state.mode === "catalysts", `${label}: catalyst mode was not preserved`);
    assert(state.catalystCount > 0, `${label}: saved catalysts are blank`);
    assert(state.fanout === "false", `${label}: row fan-out contract missing`);
    assert(!state.horizontalOverflow, `${label}: horizontal overflow`);
    assert(page.url().includes("watchMode=catalysts"), `${label}: watch mode URL state missing`);
    assert(page.url().includes("sort=metric-asc"), `${label}: sort URL state missing`);
    assert(page.url().includes("group=sector"), `${label}: group URL state missing`);
    const accessibility = await assertAccessibleBasics(page, label);
    assertErrorsEmpty(errors, label);
    return {
      ...state,
      accessibility,
      panelRequests,
      url: page.url(),
      screenshot: await screenshot(page, `watchlist-catalysts-${label}`, label === "mobile"),
    };
  } finally {
    await page.close();
  }
}

async function captureExactJourney() {
  const label = "watchlist-tsla-catalyst-return";
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(
      `${baseUrl}/?view=watchlist-desk&mode=fixture&list=fixture-daily&selected=TSLA&watchMode=catalysts&sort=metric-desc&group=sector&panel=catalysts`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-watchlist-catalyst-count]', { timeout: 120_000 });
    await page.getByRole("link", { name: "Full workstation", exact: true }).click();
    await page.waitForSelector('[data-phase6e-progressive-workstation="true"]', { timeout: 120_000 });
    await page.waitForFunction(
      () => document.querySelector("[data-phase6e-progressive-workstation]")?.getAttribute("data-delivery-panel") === "catalysts",
      null,
      { timeout: 120_000 },
    );
    await page.waitForFunction(
      () => Number(document.querySelector("[data-phase6e-progressive-workstation]")?.getAttribute("data-panel-bytes") || 0) > 0,
      null,
      { timeout: 120_000 },
    );
    const asset = await page.evaluate(() => {
      const root = document.querySelector("[data-phase6e-progressive-workstation]");
      return {
        symbol: root?.getAttribute("data-symbol"),
        panel: root?.getAttribute("data-delivery-panel"),
        catalystCount: Number(document.querySelector("[data-progressive-catalyst-count]")?.getAttribute("data-progressive-catalyst-count") || 0),
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      };
    });
    assert(asset.symbol === "TSLA", `${label}: asset identity mismatch`);
    assert(asset.panel === "catalysts", `${label}: catalyst surface was not opened`);
    assert(asset.catalystCount > 0, `${label}: exact saved catalyst panel is blank`);
    assert(!asset.horizontalOverflow, `${label}: asset horizontal overflow`);
    assert(page.url().includes("origin=watchlist-desk"), `${label}: sanitized origin missing`);
    const assetAccessibility = await assertAccessibleBasics(page, `${label}-asset`);
    const assetScreenshot = await screenshot(page, "asset-tsla-catalysts", false);

    await page.getByRole("link", { name: "Return to Watchlist", exact: true }).click();
    await page.waitForSelector('[data-phase6d-watchlist-desk="true"]', { timeout: 120_000 });
    const returned = await observe(page);
    assert(returned.symbol === "TSLA", `${label}: selected symbol was not restored`);
    assert(returned.mode === "catalysts", `${label}: watch mode was not restored`);
    assert(returned.sort === "metric-desc", `${label}: sort was not restored`);
    assert(returned.group === "sector", `${label}: group was not restored`);
    assert(returned.panel === "catalysts", `${label}: panel was not restored`);
    const returnedAccessibility = await assertAccessibleBasics(page, `${label}-returned`);
    assertErrorsEmpty(errors, label);
    return {
      asset,
      returned,
      assetAccessibility,
      returnedAccessibility,
      assetScreenshot,
      returnedScreenshot: await screenshot(page, "watchlist-tsla-returned", false),
      url: page.url(),
    };
  } finally {
    await page.close();
  }
}

async function captureCatalystFailure() {
  const label = "provider-failure-lkg";
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.route(/\/api\/symbol-workstation\/TSLA\/panels\/catalysts/, async (route) => {
      await route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({ source_status: "rate-limited", data_gap: "429 test gate" }),
      });
    });
    await page.goto(
      `${baseUrl}/?view=watchlist-desk&mode=fixture&list=fixture-daily&selected=TSLA&watchMode=catalysts&sort=manual&group=none&panel=catalysts`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector('[data-watchlist-catalyst-count]', { timeout: 120_000 });
    await page.locator('[data-watchlist-symbol="AAPL"] .watchlist-symbol-select').click();
    await page.locator('[data-watchlist-symbol="TSLA"] .watchlist-symbol-select').click();
    await page.waitForSelector(".watchlist-message", { timeout: 120_000 });
    const state = await observe(page);
    const body = await page.locator("body").innerText();
    assert(state.symbol === "TSLA", `${label}: exact identity changed`);
    assert(state.catalystCount > 0, `${label}: saved snapshot disappeared after provider failure`);
    assert(body.includes("saved Research Snapshot remains visible"), `${label}: explicit saved-snapshot fallback message missing`);
    assert(!state.horizontalOverflow, `${label}: horizontal overflow`);
    errors.console = errors.console.filter((entry) => !entry.includes("429"));
    assertErrorsEmpty(errors, label);
    return {
      ...state,
      screenshot: await screenshot(page, label, false),
      url: page.url(),
    };
  } finally {
    await page.close();
  }
}

async function observe(page) {
  return page.evaluate(() => {
    const root = document.querySelector("[data-phase6d-watchlist-desk]");
    const catalyst = document.querySelector("[data-watchlist-catalyst-count]");
    return {
      symbol: root?.getAttribute("data-selected-symbol"),
      mode: root?.getAttribute("data-watchlist-view-mode"),
      sort: root?.getAttribute("data-watchlist-sort"),
      group: root?.getAttribute("data-watchlist-group"),
      panel: root?.getAttribute("data-panel-delivery"),
      fanout: root?.getAttribute("data-provider-fanout"),
      materialization: root?.getAttribute("data-materialization-status"),
      catalystCount: Number(catalyst?.getAttribute("data-watchlist-catalyst-count") || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
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

async function assertAccessibleBasics(page, label) {
  const audit = await page.evaluate(() => {
    const duplicateIds = [...document.querySelectorAll("[id]")]
      .map((element) => element.id)
      .filter((id, index, ids) => id && ids.indexOf(id) !== index);
    const interactive = [...document.querySelectorAll("button, a[href], input, select, textarea")];
    const unlabeled = interactive
      .filter((element) => {
        if (element instanceof HTMLInputElement && element.type === "hidden") return false;
        const ariaLabel = element.getAttribute("aria-label")?.trim();
        const labelledBy = element.getAttribute("aria-labelledby")?.trim();
        const title = element.getAttribute("title")?.trim();
        const text = element.textContent?.trim();
        const value = element instanceof HTMLInputElement ? element.value.trim() : "";
        const label = element.id
          ? document.querySelector(`label[for="${CSS.escape(element.id)}"]`)?.textContent?.trim()
          : "";
        const wrappingLabel = element.closest("label")?.textContent?.trim();
        return !(ariaLabel || labelledBy || title || text || value || label || wrappingLabel);
      })
      .map((element) => element.outerHTML.slice(0, 180));
    return {
      duplicateIds: [...new Set(duplicateIds)],
      interactiveCount: interactive.length,
      unlabeled,
    };
  });
  assert(!audit.duplicateIds.length, `${label}: duplicate IDs ${audit.duplicateIds.join(", ")}`);
  assert(!audit.unlabeled.length, `${label}: unlabeled controls ${audit.unlabeled.join(" | ")}`);

  const focusTarget = page.getByRole("button", { name: "Catalysts", exact: true }).first();
  await page.keyboard.press("Tab");
  await focusTarget.focus();
  const focusStyle = await focusTarget.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      boxShadow: style.boxShadow,
    };
  });
  const hasVisibleFocus = (
    (focusStyle.outlineStyle !== "none" && focusStyle.outlineWidth !== "0px")
    || (focusStyle.boxShadow && focusStyle.boxShadow !== "none")
  );
  assert(hasVisibleFocus, `${label}: Catalysts keyboard focus indicator is missing`);
  return {
    interactiveCount: audit.interactiveCount,
    duplicateIdCount: audit.duplicateIds.length,
    unlabeledControlCount: audit.unlabeled.length,
    focusStyle,
  };
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
