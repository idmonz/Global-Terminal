import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3064";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6l_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const report = {
  evidence_version: "phase6l.visual.v1",
  product_phase: "Phase 6L",
  base_url: baseUrl,
  captured_at: new Date().toISOString(),
  captures: {},
};

try {
  report.captures.desktop = await captureDesktopJourney();
  report.captures.mobile = await captureMobileTruth();
  report.captures.isolation = await captureTenantIsolation();
  report.captures.offline = await captureAccountOutage();
  report.captures.regressions = await captureRegressions();
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureDesktopJourney() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const accountRequests = [];
  const errors = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/account/")) accountRequests.push(request.url());
  });
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console:${message.text()}`);
  });
  try {
    await openWatchlist(page);
    assert(accountRequests.length === 0, `account API was not lazy: ${accountRequests.join(" | ")}`);
    const navigation = await page.locator(".watchlist-desk-workspace-grid > .product-nav").evaluate((node) => ({
      width: Math.round(node.getBoundingClientRect().width),
      scrollWidth: node.scrollWidth,
      clientWidth: node.clientWidth,
    }));
    assert(navigation.width >= 160, `research navigation remains crushed at ${navigation.width}px`);
    assert(navigation.scrollWidth <= navigation.clientWidth + 1, "research navigation text overflows its rail");
    const closed = await screenshot(page, "phase6l-watchlist-nav-fixed-desktop", false);

    await page.getByRole("button", { name: /Account research/ }).click();
    await page.getByRole("button", { name: "Use Analyst A" }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="ready"]').waitFor({ state: "visible", timeout: 30_000 });
    await page.locator('[data-phase6l-sync-state="hosted-unavailable"]').waitFor({ state: "visible" });
    if ((await page.locator(".tenant-account-watchlists article").count()) === 0) {
      const candidates = await page.locator(".tenant-candidate-list label").count();
      assert(candidates === 2, `expected two visual QA import candidates, got ${candidates}`);
      await page.getByLabel("I consent to copy the selected public research fields into this account workspace.", { exact: true }).check();
      await page.getByRole("button", { name: "Confirm import", exact: true }).click();
      await page.locator(".tenant-account-watchlists article").first().waitFor({ state: "visible", timeout: 30_000 });
      await page.getByRole("button", { name: "In-app rule", exact: true }).first().click();
      await page.getByRole("button", { name: "Check saved changes", exact: true }).first().click();
      await page.locator(".tenant-inbox article").first().waitFor({ state: "visible", timeout: 30_000 });
    }
    await page.getByRole("button", { name: "Review sync plan" }).click();
    await page.getByText("Explicit sync consent", { exact: true }).waitFor({ state: "visible" });
    const resourceCount = Number(await page.locator(".tenant-sync-plan > div > strong").first().textContent().then((value) => value?.match(/\d+/)?.[0] || "0"));
    assert(resourceCount >= 4, `sync preview is not a useful account snapshot (${resourceCount} records)`);
    const attentionCount = await page.locator(".tenant-inbox article").count();
    assert(attentionCount >= 1, "attention queue did not expose saved material changes");
    await page.evaluate(() => window.scrollTo(0, 0));
    const reviewed = await screenshot(page, "phase6l-sync-reviewed-hosted-unavailable-desktop", false);

    await page.getByLabel(/Explicit sync consent/).check();
    await page.getByRole("button", { name: "Queue offline plan" }).click();
    await page.locator(".tenant-sync-queue article").first().waitFor({ state: "visible", timeout: 30_000 });
    await page.evaluate(() => window.scrollTo(0, 0));
    const pending = await screenshot(page, "phase6l-sync-pending-local-desktop", false);
    const state = await inspect(page);
    assert(!state.horizontalOverflow, "desktop Phase 6L journey overflows horizontally");
    assert(state.hostedUnavailable, "hosted-unavailable truth is not visible");
    assert(state.pendingCount >= 1, "offline queue did not expose a pending row");
    assert(errors.filter((row) => !row.includes("favicon")).length === 0, `browser errors: ${errors.join(" | ")}`);
    return { navigation, lazyAccountCalls: 0, resourceCount, attentionCount, ...state, screenshots: { closed, reviewed, pending } };
  } finally {
    await context.close();
  }
}

async function captureMobileTruth() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  try {
    await openWatchlist(page);
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.getByRole("button", { name: "Use Analyst A" }).click();
    await page.locator('[data-phase6l-sync-state="hosted-unavailable"]').waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Review sync plan" }).click();
    const state = await inspect(page);
    assert(!state.horizontalOverflow, "mobile Phase 6L journey overflows horizontally");
    assert(state.deskWidth <= 390, `mobile account desk width is ${state.deskWidth}`);
    await page.evaluate(() => window.scrollTo(0, 0));
    const syncScreenshot = await screenshot(page, "phase6l-sync-reviewed-mobile", false);
    await page.locator(".tenant-inbox").scrollIntoViewIfNeeded();
    const attentionScreenshot = await screenshot(page, "phase6l-attention-queue-mobile", false);
    return { ...state, screenshots: { sync: syncScreenshot, attention: attentionScreenshot } };
  } finally {
    await context.close();
  }
}

async function captureTenantIsolation() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    await openWatchlist(page);
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.getByRole("button", { name: "Use Analyst B" }).click();
    await page.locator('[data-phase6l-sync-state="hosted-unavailable"]').waitFor({ state: "visible" });
    const sync = await page.evaluate(() => fetch("/api/account/research-desk/sync", { credentials: "same-origin", cache: "no-store" }).then((response) => response.json()));
    assert(sync.data.pending_count === 0, "Account B can enumerate Account A sync queue");
    return { pendingCount: 0, screenshot: await screenshot(page, "phase6l-account-b-sync-isolated", false) };
  } finally {
    await context.close();
  }
}

async function captureAccountOutage() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.route("**/api/account/**", (route) => route.abort("failed"));
  try {
    await openWatchlist(page);
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="offline"]').waitFor({ state: "visible" });
    assert((await page.locator(".watchlist-symbol-row").count()) > 0, "account outage removed local watchlist research");
    const accountScreenshot = await elementScreenshot(page.locator('[data-phase6k-tenant-research="true"]'), "phase6l-account-api-offline-state");
    const localScreenshot = await elementScreenshot(page.locator(".watchlist-desk-layout"), "phase6l-account-api-offline-local-retained");
    return { localWorkflowRetained: true, screenshots: { account: accountScreenshot, local: localScreenshot } };
  } finally {
    await context.close();
  }
}

async function captureRegressions() {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  try {
    const views = [
      ["analyst-workspace", '[data-phase6h-analyst-workspace="true"]'],
      ["market-map", '.market-map-screener[data-market-map-state="ready"]'],
      ["daily-brief", '.daily-brief-workstation'],
    ];
    const result = {};
    for (const [view, selector] of views) {
      await page.goto(`${baseUrl}/?view=${view}&mode=fixture&symbol=AAPL`, { waitUntil: "domcontentloaded", timeout: 180_000 });
      await page.locator(selector).waitFor({ state: "visible", timeout: 120_000 });
      result[view] = { visible: true, horizontalOverflow: await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) };
      assert(!result[view].horizontalOverflow, `${view} regression overflow`);
    }
    return result;
  } finally {
    await context.close();
  }
}

async function openWatchlist(page) {
  await page.goto(`${baseUrl}/?view=watchlist-desk&mode=fixture&list=primary&selected=AAPL`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.locator('[data-phase6d-watchlist-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
  await Promise.race([
    page.locator('.watchlist-chart-panel [data-chart-state="ready"]').waitFor({ state: "visible", timeout: 30_000 }),
    page.getByText("Chart cache unavailable", { exact: false }).waitFor({ state: "visible", timeout: 30_000 }),
  ]).catch(() => {});
}

async function inspect(page) {
  return page.evaluate(() => {
    const desk = document.querySelector('[data-phase6k-tenant-research="true"]');
    return {
      deskWidth: Math.round(desk?.getBoundingClientRect().width || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      hostedUnavailable: desk?.textContent?.includes("Hosted unavailable") || false,
      pendingCount: desk?.querySelectorAll(".tenant-sync-queue article").length || 0,
      providerCallTruth: desk?.textContent?.includes("Market provider calls 0") || false,
    };
  });
}

async function screenshot(page, name, fullPage) {
  const file = path.join(outputDirectory, `${name}.png`);
  await page.screenshot({ path: file, fullPage });
  const bytes = (await stat(file)).size;
  assert(bytes > 15_000, `${name} screenshot is unexpectedly small (${bytes})`);
  return { file, bytes };
}

async function elementScreenshot(locator, name) {
  const file = path.join(outputDirectory, `${name}.png`);
  await locator.screenshot({ path: file });
  const bytes = (await stat(file)).size;
  assert(bytes > 8_000, `${name} element screenshot is unexpectedly small (${bytes})`);
  return { file, bytes };
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
