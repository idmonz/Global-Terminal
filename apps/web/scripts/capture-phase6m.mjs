import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3066";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6m_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const fixture = JSON.parse(await readFile(path.join(repoRoot, "static", "api-fixtures", "attention-desk.json"), "utf8"));

await mkdir(outputDirectory, { recursive: true });
const browser = await launchBrowser();
const report = {
  evidence_version: "phase6m.visual.v1",
  product_phase: "Phase 6M",
  base_url: baseUrl,
  captured_at: new Date().toISOString(),
  captures: {},
};

try {
  report.captures.desktop = await captureDailyReviewDesktop();
  report.captures.mobile = await captureDailyReviewMobile();
  report.captures.states = await captureMaterialStates();
  report.captures.review = await captureLocalReviewLifecycle();
  report.captures.drilldown = await captureDrilldownReturns();
  report.captures.account = await captureAccountIsolationConflictAndOffline();
  report.captures.regressions = await captureRegressions();
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureDailyReviewDesktop() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  try {
    await openAttention(page);
    const state = await inspect(page);
    assert(state.visibleCount >= 3, `daily queue is not useful (${state.visibleCount})`);
    assert(state.providerCalls === 0, `attention claims ${state.providerCalls} provider calls`);
    assert(state.productNavWidth >= 160, `ProductNav is crushed at ${state.productNavWidth}px`);
    assert(!state.horizontalOverflow, "desktop Attention Desk overflows horizontally");
    assert(state.duplicateIds.length === 0, `duplicate ids: ${state.duplicateIds.join(", ")}`);
    assert(state.unlabeledControls === 0, `${state.unlabeledControls} controls lack accessible labels`);
    assert(telemetry.accountRequests.length === 0, "default local review made a hidden account request");
    assert(telemetry.providerRequests.length === 0, `provider request escaped: ${telemetry.providerRequests.join(" | ")}`);
    const first = await screenshot(page, "attention-daily-review-desktop", false);
    await page.getByLabel("Attention change kind").selectOption("source-degradation");
    await waitForVisibleCount(page, 1);
    const degraded = await screenshot(page, "attention-source-degraded", false);
    return {
      ...state,
      hiddenRequestCount: telemetry.accountRequests.length,
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
      screenshots: { first, degraded },
    };
  } finally {
    await context.close();
  }
}

async function captureDailyReviewMobile() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const telemetry = observe(page);
  try {
    await openAttention(page);
    const state = await inspect(page);
    const criticalTop = await page.locator(".attention-queue-row").first().evaluate((node) => ({
      top: Math.round(node.getBoundingClientRect().top),
      severity: node.getAttribute("data-attention-severity"),
    }));
    assert(!state.horizontalOverflow, "390px Attention Desk overflows horizontally");
    assert(state.rootWidth <= 390, `mobile root width is ${state.rootWidth}`);
    assert(criticalTop.top < 844, `first material row starts below the first viewport at ${criticalTop.top}`);
    assert(telemetry.accountRequests.length === 0, "mobile local review made a hidden account request");
    return {
      ...state,
      criticalTop,
      hiddenRequestCount: telemetry.accountRequests.length,
      errors: telemetry.errors,
      screenshot: await screenshot(page, "attention-daily-review-mobile", false),
      tallScreenshot: await screenshot(page, "attention-daily-review-mobile-tall", true),
    };
  } finally {
    await context.close();
  }
}

async function captureMaterialStates() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    await openAttention(page, "&attentionSeverity=critical");
    await waitForVisibleCount(page, 0);
    assert(await page.getByText("No material change matches this review state.", { exact: true }).isVisible(), "honest no-material state missing");
    const noMaterial = await screenshot(page, "attention-no-material-change", false);

    const firstFingerprint = fixture.data.all_items.find((row) => row.material)?.fingerprint;
    assert(firstFingerprint, "fixture has no material fingerprint for expiry proof");
    const expiryContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await expiryContext.addInitScript(({ key, fingerprint }) => {
      localStorage.setItem(key, JSON.stringify({
        states: {
          [fingerprint]: {
            review_state: "snoozed",
            prior_state: "new",
            snoozed_until: "2020-01-01T00:00:00.000Z",
            version: 1,
          },
        },
        policy: {
          minimum_severity: "info",
          included_change_kinds: ["market-change", "new-evidence", "source-degradation", "stale-evidence", "resolved"],
          source_health_handling: "include",
          version: 0,
        },
        checkpoint: { reviewed_through_at: null, version: 0 },
      }));
    }, { key: "global-terminal.attention-desk.v1", fingerprint: firstFingerprint });
    const expiryPage = await expiryContext.newPage();
    try {
      await openAttention(expiryPage);
      await expiryPage.getByText("Snooze expired", { exact: true }).waitFor({ state: "visible" });
      const expired = await screenshot(expiryPage, "attention-snooze-expired-recovery", false);
      return { noMaterial, expired };
    } finally {
      await expiryContext.close();
    }
  } finally {
    await context.close();
  }
}

async function captureLocalReviewLifecycle() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    await openAttention(page);
    const first = page.locator(".attention-queue-row").first();
    await first.getByRole("button", { name: "Review", exact: true }).click();
    await first.getAttribute("data-attention-review-state").then((value) => assert(value === "reviewed", `review state is ${value}`));
    const reviewed = await screenshot(page, "attention-reviewed-local", false);

    const second = page.locator(".attention-queue-row").nth(1);
    await second.getByRole("button", { name: "Snooze 4h", exact: true }).click();
    await page.getByRole("button", { name: "Snoozed", exact: true }).click();
    await page.locator('.attention-queue-row[data-attention-review-state="snoozed"]').first().waitFor({ state: "visible" });
    const snoozed = await screenshot(page, "attention-snoozed-local", false);
    await page.locator('.attention-queue-row[data-attention-review-state="snoozed"]').first().getByRole("button", { name: "Undo snooze", exact: true }).click();
    await page.getByRole("button", { name: "Needs Review", exact: true }).click();
    await page.getByRole("button", { name: "Mark review checkpoint", exact: true }).click();
    await page.getByText("Local review checkpoint advanced.", { exact: false }).waitFor({ state: "visible" });
    const checkpoint = await screenshot(page, "attention-checkpoint-local", false);
    return { reviewed, snoozed, checkpoint, providerCallCount: 0 };
  } finally {
    await context.close();
  }
}

async function captureDrilldownReturns() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    const results = {};
    await openAttention(page);
    for (const destination of ["News", "Brief", "Map"]) {
      const link = await selectAttentionDestination(page, destination);
      await link.click();
      await page.getByRole("link", { name: "Return to Attention Desk", exact: true }).waitFor({ state: "visible", timeout: 120_000 });
      results[destination.toLowerCase()] = await screenshot(page, `attention-drilldown-${destination.toLowerCase()}`, false);
      await page.getByRole("link", { name: "Return to Attention Desk", exact: true }).click();
      await page.locator('[data-phase6m-attention-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
      assert(new URL(page.url()).searchParams.get("view") === "attention-desk", `${destination} return lost origin`);
    }

    const aapl = page.locator(".attention-queue-row").filter({ hasText: "AAPL" }).first();
    await aapl.locator(".attention-row-select").click();
    const analyst = page.locator(".attention-drilldown-grid").getByRole("link", { name: "Analyst", exact: true });
    await analyst.waitFor({ state: "visible" });
    await analyst.click();
    await page.getByRole("link", { name: "Return to Attention Desk", exact: true }).waitFor({ state: "visible", timeout: 120_000 });
    results.analyst = await screenshot(page, "attention-drilldown-analyst", false);
    await page.getByRole("link", { name: "Return to Attention Desk", exact: true }).click();
    await page.locator('[data-phase6m-attention-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
    return { routes: Object.keys(results), screenshots: results };
  } finally {
    await context.close();
  }
}

async function selectAttentionDestination(page, destination) {
  const rows = page.locator(".attention-queue-row");
  const count = await rows.count();
  for (let index = 0; index < count; index += 1) {
    await rows.nth(index).locator(".attention-row-select").click();
    const link = page.locator(".attention-drilldown-grid").getByRole("link", { name: destination, exact: true });
    if (await link.isVisible()) return link;
  }
  throw new Error(`No Attention row exposes the ${destination} drilldown`);
}

async function captureAccountIsolationConflictAndOffline() {
  const accountA = await withDedicatedPage(async (page) => {
    await openAttention(page);
    if (!(await localSignIn(page, "analyst-a"))) return { available: false, reason: "local-auth-disabled" };
    await page.getByRole("button", { name: "Use account review", exact: true }).click();
    await page.locator('[data-attention-review-scope="account"]').waitFor({ state: "visible" });
    const row = page.locator(".attention-queue-row").first();
    const title = (await row.locator("h4").textContent()) || "";
    await row.getByRole("button", { name: "Review", exact: true }).click();
    await page.getByText("Account state saved", { exact: false }).waitFor({ state: "visible" });
    return { available: true, title, screenshot: await screenshot(page, "attention-account-a-reviewed", false) };
  });
  if (!accountA.available) return accountA;

  const accountB = await withDedicatedPage(async (page) => {
    await openAttention(page);
    assert(await localSignIn(page, "analyst-b"), "Account B sign-in unavailable");
    await page.getByRole("button", { name: "Use account review", exact: true }).click();
    await page.locator('[data-attention-review-scope="account"]').waitFor({ state: "visible" });
    const same = page.locator(".attention-queue-row").filter({ hasText: accountA.title }).first();
    assert(await same.getAttribute("data-attention-review-state") === "new", "Account B observed Account A review state");
    const isolated = await screenshot(page, "attention-account-b-isolated", false);
    await page.route("**/api/account/attention-desk/items/**", (route) => route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ payload_type: "attention_review_state", data: { current_version: 9 } }) }));
    await same.getByRole("button", { name: "Review", exact: true }).click();
    await page.getByText("Review version changed", { exact: false }).waitFor({ state: "visible" });
    return { isolated, conflict: await screenshot(page, "attention-version-conflict", false) };
  });

  const offline = await withDedicatedPage(async (page) => {
    await page.route("**/api/account/attention-desk**", (route) => route.abort("failed"));
    await openAttention(page);
    await page.getByRole("button", { name: "Use account review", exact: true }).click();
    await page.locator('[data-attention-account-state="offline"]').waitFor({ state: "visible" });
    assert(Number(await page.locator('[data-phase6m-attention-desk="true"]').getAttribute("data-attention-visible-count")) > 0, "account outage removed local attention rows");
    return screenshot(page, "attention-account-offline-local-retained", false);
  });

  return {
    available: true,
    accountA: accountA.screenshot,
    accountB: accountB.isolated,
    conflict: accountB.conflict,
    offline,
    isolated: true,
  };
}

async function launchBrowser() {
  return chromium.launch({ executablePath: chromePath, headless: true });
}

async function withDedicatedPage(callback) {
  const dedicatedBrowser = await launchBrowser();
  const context = await dedicatedBrowser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    return await callback(page);
  } finally {
    await dedicatedBrowser.close();
  }
}

async function captureRegressions() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    const routes = [
      ["analyst", `${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=AAPL`, '[data-phase6h-analyst-workspace="true"]'],
      ["operations", `${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=AAPL`, '[data-phase6i-research-operations="true"]'],
      ["watchlist", `${baseUrl}/?view=watchlist-desk&mode=fixture&list=primary&selected=AAPL`, '[data-phase6d-watchlist-desk="true"]'],
      ["daily-brief", `${baseUrl}/?view=daily-brief&mode=fixture`, ".daily-brief-workstation"],
    ];
    const output = {};
    for (const [name, url, selector] of routes) {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 180_000 });
      await page.locator(selector).waitFor({ state: "visible", timeout: 120_000 });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
      assert(!overflow, `${name} regression overflows horizontally`);
      output[name] = { visible: true, overflow, screenshot: await screenshot(page, `attention-regression-${name}`, false) };
    }
    return output;
  } finally {
    await context.close();
  }
}

async function openAttention(page, suffix = "") {
  await page.goto(`${baseUrl}/?view=attention-desk&mode=fixture${suffix}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.locator('[data-phase6m-attention-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
  await page.locator(".attention-queue-row").first().waitFor({ state: "visible", timeout: 120_000 }).catch(() => {});
}

async function localSignIn(page, alias) {
  return page.evaluate(async (selectedAlias) => {
    const response = await fetch("/api/account/local-session", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alias: selectedAlias, return_to: "/?view=attention-desk" }),
    });
    return response.status === 201;
  }, alias);
}

function observe(page) {
  const accountRequests = [];
  const providerRequests = [];
  const errors = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/account/")) accountRequests.push(url);
    if (/alphavantage|finnhub|coingecko|binance|gdelt|usgs|opensky/i.test(url)) providerRequests.push(url);
  });
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => { if (message.type() === "error" && !message.text().includes("favicon")) errors.push(`console:${message.text()}`); });
  return { accountRequests, providerRequests, errors };
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.querySelector('[data-phase6m-attention-desk="true"]');
    const nav = document.querySelector(".attention-desk-workspace-grid > .product-nav");
    const ids = Array.from(document.querySelectorAll("[id]")).map((node) => node.id);
    const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
    const controls = Array.from(document.querySelectorAll("button,select,input,a[href]"));
    const unlabeledControls = controls.filter((node) => {
      const associatedLabels = "labels" in node && node.labels
        ? Array.from(node.labels).map((item) => item.textContent?.trim()).filter(Boolean).join(" ")
        : "";
      const label = node.getAttribute("aria-label") || node.getAttribute("title") || node.textContent?.trim() || associatedLabels;
      return !label;
    }).length;
    return {
      visibleCount: Number(root?.getAttribute("data-attention-visible-count") || 0),
      providerCalls: Number(root?.getAttribute("data-attention-provider-calls") || -1),
      productNavWidth: Math.round(nav?.getBoundingClientRect().width || 0),
      productNavScrollWidth: nav?.scrollWidth || 0,
      productNavClientWidth: nav?.clientWidth || 0,
      rootWidth: Math.round(root?.getBoundingClientRect().width || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      duplicateIds: [...new Set(duplicateIds)],
      unlabeledControls,
      firstViewportHasDigest: Boolean(document.querySelector(".attention-digest-band")),
      firstViewportHasQueue: Boolean(document.querySelector(".attention-queue-row")),
      sourceTruthVisible: Boolean(document.querySelector(".attention-source-detail")),
    };
  });
}

async function waitForVisibleCount(page, expected) {
  await page.waitForFunction((count) => Number(document.querySelector('[data-phase6m-attention-desk="true"]')?.getAttribute("data-attention-visible-count")) === count, expected);
}

async function screenshot(page, name, fullPage) {
  const file = path.join(outputDirectory, `${name}.png`);
  await page.bringToFront();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.screenshot({ path: file, fullPage, animations: "disabled", caret: "hide", omitBackground: false });
  const bytes = (await stat(file)).size;
  assert(bytes > 12_000, `${name} screenshot is unexpectedly small (${bytes})`);
  return { file, bytes };
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
