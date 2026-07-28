import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3052";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6g_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.desktop = await captureInbox({ width: 1600, height: 1000 }, "desktop");
  captures.mobile = await captureInbox({ width: 390, height: 844 }, "mobile");
  captures.emptyFilter = await captureEmptyFilter();
  captures.journey = await captureDrilldownReturn();
  captures.offline = await captureOfflineEvidence();
  const report = { baseUrl, captured_at: new Date().toISOString(), captures };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureInbox(viewport, label) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  let providerRequests = 0;
  page.on("request", (request) => {
    const url = request.url().toLowerCase();
    if (url.includes("alphavantage") || url.includes("finnhub") || url.includes("yfinance")) providerRequests += 1;
  });
  try {
    await page.goto(changesUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector('[data-watchlist-change-count="6"]', { timeout: 120_000 });
    await page.waitForSelector(".change-evidence-panel", { timeout: 120_000 });
    const controls = page.getByLabel("Change inbox filters");
    await controls.getByLabel("Type").selectOption("event");
    await controls.getByLabel("Severity").selectOption("material");
    await page.locator(".change-inbox-row").first().click();
    await page.waitForTimeout(150);
    const state = await observe(page);
    assert(state.mode === "changes", `${label}: change mode missing`);
    assert(state.changeCount === 6, `${label}: expected six deterministic changes`);
    assert(state.changeType === "event", `${label}: event filter missing`);
    assert(state.changeSeverity === "material", `${label}: severity filter missing`);
    assert(state.selectedChange?.startsWith("change_"), `${label}: selected change missing`);
    assert(state.fanout === "false", `${label}: provider fan-out contract missing`);
    assert(providerRequests === 0, `${label}: change scan made ${providerRequests} provider requests`);
    assert(!state.horizontalOverflow, `${label}: horizontal overflow`);
    assert(page.url().includes("changeType=event"), `${label}: type filter URL state missing`);
    assert(page.url().includes("changeSeverity=material"), `${label}: severity filter URL state missing`);
    assert(page.url().includes("change=change_"), `${label}: selected change URL state missing`);
    const accessibility = await assertAccessibleBasics(page, label);
    assertErrorsEmpty(errors, label);
    return {
      ...state,
      providerRequests,
      accessibility,
      url: page.url(),
      screenshot: await screenshot(page, `change-inbox-${label}`, label === "mobile"),
    };
  } finally {
    await page.close();
  }
}

async function captureEmptyFilter() {
  const label = "no-matching-change";
  const page = await browser.newPage({ viewport: { width: 1280, height: 850 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(`${changesUrl()}&changeType=fundamental`, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector(".change-inbox-empty", { timeout: 120_000 });
    const body = await page.locator("body").innerText();
    const state = await observe(page);
    assert(body.includes("No changes match these filters"), `${label}: honest empty state missing`);
    assert(state.changeCount === 6, `${label}: comparison was discarded by filter`);
    assert(!state.horizontalOverflow, `${label}: horizontal overflow`);
    assertErrorsEmpty(errors, label);
    return { ...state, screenshot: await screenshot(page, label, false), url: page.url() };
  } finally {
    await page.close();
  }
}

async function captureDrilldownReturn() {
  const label = "change-drilldown-return";
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.goto(`${changesUrl()}&changeType=event&changeSeverity=material`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector(".change-evidence-panel", { timeout: 120_000 });
    await page.locator(".change-inbox-row").first().click();
    const selected = await page.locator("[data-phase6d-watchlist-desk]").getAttribute("data-watchlist-selected-change");
    await page.getByRole("link", { name: /Open exact catalysts analysis/ }).click();
    await page.waitForSelector('[data-phase6h-analyst-workspace="true"]', { timeout: 120_000 });
    await page.waitForFunction(() => document.querySelector('[data-panel="catalysts"]')?.getAttribute("data-panel-status") === "ready");
    const assetState = await page.evaluate(() => {
      const root = document.querySelector("[data-phase6h-analyst-workspace]");
      return {
        symbol: root?.getAttribute("data-symbol"),
        panel: root?.getAttribute("data-focused-panel"),
        changeEvidence: document.querySelector(".analyst-workspace-rail")?.textContent || "",
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      };
    });
    assert(assetState.symbol === "AAPL", `${label}: exact symbol changed`);
    assert(assetState.panel === "catalysts", `${label}: event did not open catalysts`);
    assert(assetState.changeEvidence.includes("scheduled-earnings"), `${label}: saved change evidence missing`);
    assert(!assetState.horizontalOverflow, `${label}: asset overflow`);
    const assetScreenshot = await screenshot(page, "change-event-exact-catalysts", false);
    await page.getByRole("link", { name: "Return to Change Inbox", exact: true }).first().click();
    await page.waitForSelector('[data-watchlist-view-mode="changes"]', { timeout: 120_000 });
    const returned = await observe(page);
    assert(returned.changeType === "event", `${label}: type filter not restored`);
    assert(returned.changeSeverity === "material", `${label}: severity not restored`);
    assert(returned.selectedChange === selected, `${label}: selected change not restored`);
    assert(!returned.horizontalOverflow, `${label}: return overflow`);
    assertErrorsEmpty(errors, label);
    return {
      assetState,
      returned,
      assetScreenshot,
      returnedScreenshot: await screenshot(page, "change-inbox-returned", false),
      url: page.url(),
    };
  } finally {
    await page.close();
  }
}

async function captureOfflineEvidence() {
  const label = "offline-saved-change-evidence";
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const errors = listenForErrors(page);
  try {
    await page.route(/\/api\//, async (route) => route.abort("internetdisconnected"));
    await page.goto(changesUrl(), { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector(".change-evidence-panel", { timeout: 120_000 });
    const body = await page.locator("body").innerText();
    const state = await observe(page);
    assert(state.changeCount === 6, `${label}: saved comparison disappeared`);
    assert(body.includes("Previous") && body.includes("Current"), `${label}: evidence comparison missing`);
    assert(body.includes("Preview only"), `${label}: delivery boundary missing`);
    assert(!state.horizontalOverflow, `${label}: horizontal overflow`);
    errors.console = errors.console.filter((entry) => (
      entry.includes("ERR_FAILED")
      || entry.includes("ERR_INTERNET_DISCONNECTED")
      || entry.includes("Failed to load resource")
    ) ? false : true);
    assertErrorsEmpty(errors, label);
    return { ...state, screenshot: await screenshot(page, label, true), url: page.url() };
  } finally {
    await page.close();
  }
}

function changesUrl() {
  return `${baseUrl}/?view=watchlist-desk&mode=fixture&list=fixture-daily&selected=AAPL&watchMode=changes&sort=manual&group=none&panel=chart`;
}

async function observe(page) {
  return page.evaluate(() => {
    const root = document.querySelector("[data-phase6d-watchlist-desk]");
    return {
      mode: root?.getAttribute("data-watchlist-view-mode"),
      changeCount: Number(root?.getAttribute("data-watchlist-change-count") || 0),
      selectedChange: root?.getAttribute("data-watchlist-selected-change"),
      changeType: root?.getAttribute("data-watchlist-change-type"),
      changeSeverity: root?.getAttribute("data-watchlist-change-severity"),
      changeStatus: root?.getAttribute("data-watchlist-change-status"),
      fanout: root?.getAttribute("data-provider-fanout"),
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
    const unlabeled = interactive.filter((element) => {
      if (element instanceof HTMLInputElement && element.type === "hidden") return false;
      const label = element.id
        ? document.querySelector(`label[for="${CSS.escape(element.id)}"]`)?.textContent?.trim()
        : "";
      return !(
        element.getAttribute("aria-label")?.trim()
        || element.getAttribute("aria-labelledby")?.trim()
        || element.getAttribute("title")?.trim()
        || element.textContent?.trim()
        || (element instanceof HTMLInputElement ? element.value.trim() : "")
        || label
        || element.closest("label")?.textContent?.trim()
      );
    }).map((element) => element.outerHTML.slice(0, 180));
    return { duplicateIds: [...new Set(duplicateIds)], interactiveCount: interactive.length, unlabeled };
  });
  assert(!audit.duplicateIds.length, `${label}: duplicate IDs ${audit.duplicateIds.join(", ")}`);
  assert(!audit.unlabeled.length, `${label}: unlabeled controls ${audit.unlabeled.join(" | ")}`);
  const focusTarget = page.getByRole("button", { name: "Changes", exact: true });
  await focusTarget.focus();
  const focusStyle = await focusTarget.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth, boxShadow: style.boxShadow };
  });
  assert(
    (focusStyle.outlineStyle !== "none" && focusStyle.outlineWidth !== "0px")
      || (focusStyle.boxShadow && focusStyle.boxShadow !== "none"),
    `${label}: keyboard focus indicator missing`,
  );
  return audit;
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
