import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3067";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6n_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const fixture = JSON.parse(await readFile(path.join(repoRoot, "static", "api-fixtures", "attention-desk.json"), "utf8"));

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const report = {
  evidence_version: "phase6n.visual.v1",
  product_phase: "Phase 6N",
  base_url: baseUrl,
  captured_at: new Date().toISOString(),
  captures: {},
};

try {
  report.captures.journey = await captureExplicitRunJourney();
  report.captures.mobile = await captureMobileCriticalFirst();
  report.captures.states = await captureOperationalStates();
  report.captures.offline = await captureRuntimeOffline();
  report.captures.drilldown = await captureDrilldownReturn();
  report.captures.account = await captureAccountIsolationConflictAndOffline();
  report.captures.regressions = await captureRegressions();
  report.passed = true;
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureExplicitRunJourney() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  const controller = await installAccountRuntime(page, completedRun({ runId: "obsrun_previous" }));
  try {
    await openAttention(page);
    assert(telemetry.accountRequests.length === 0, "default local review made a hidden account request");
    await loadAccountReviewView(page);
    await page.getByRole("button", { name: "Refresh saved Watchlist", exact: true }).click();
    await page.locator('[data-observation-run-status="running"]').waitFor({ state: "visible" });
    const progress = await screenshot(page, "observation-run-progress-desktop", false);
    await page.locator('[data-observation-run-status="completed"]').waitFor({ state: "visible", timeout: 15_000 });
    const state = await inspect(page);
    assert(state.observationVisible, "observation run strip is not visible");
    assert(state.providerCalls === 0, `Attention claims ${state.providerCalls} triage provider calls`);
    assert(state.productNavWidth >= 160, `ProductNav is crushed at ${state.productNavWidth}px`);
    assert(!state.horizontalOverflow, "desktop observation journey overflows horizontally");
    assert(state.duplicateIds.length === 0, `duplicate ids: ${state.duplicateIds.join(", ")}`);
    assert(state.unlabeledControls === 0, `${state.unlabeledControls} controls lack labels`);
    assert(state.liveRegionCount >= 1, "observation journey has no aria-live status region");
    assert(state.observationHeight > 120, `observation strip height is unstable (${state.observationHeight}px)`);
    const focusEvidence = await inspectFocusVisible(page);
    assert(focusEvidence.visible, `Refresh saved Watchlist lacks a visible keyboard focus state: ${JSON.stringify(focusEvidence)}`);
    assertCleanTelemetry(telemetry, "explicit run journey");
    return {
      ...state,
      focusVisible: focusEvidence.visible,
      focusEvidence,
      progress,
      completed: await screenshot(page, "observation-run-completed-desktop", false),
      accountRequestCount: telemetry.accountRequests.length,
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
      runApiPosts: controller.postCount,
      runPolls: controller.pollCount,
    };
  } finally {
    await context.close();
  }
}

async function captureMobileCriticalFirst() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installAccountRuntime(page, completedRun({ materialChanges: 4 }));
  try {
    await openAttention(page);
    await loadAccountReviewView(page);
    const state = await inspect(page);
    const firstRow = await page.locator(".attention-queue-row").first().evaluate((node) => ({
      top: Math.round(node.getBoundingClientRect().top),
      severity: node.getAttribute("data-attention-severity"),
    }));
    assert(!state.horizontalOverflow, "390px observation layout overflows horizontally");
    assert(state.rootWidth <= 390, `mobile root width is ${state.rootWidth}`);
    assert(firstRow.top < 844, `first material change starts below the first viewport at ${firstRow.top}`);
    assert(state.liveRegionCount >= 1, "mobile observation journey has no aria-live status region");
    assertCleanTelemetry(telemetry, "mobile critical-first journey");
    return {
      ...state,
      firstRow,
      providerRequestCount: telemetry.providerRequests.length,
      screenshot: await screenshot(page, "observation-run-mobile-critical-first", false),
      tallScreenshot: await screenshot(page, "observation-run-mobile-critical-first-tall", true),
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureOperationalStates() {
  const cases = [
    ["observation-run-no-due-work", completedRun({ reason: "no-due-work", sessionState: "outside-regular-session", materialChanges: 0 }), "completed"],
    ["observation-run-quota-blocked", partialRun({ reason: "daily-quota-exhausted", calls: 0, lkg: 2 }), "partial"],
    ["observation-run-partial-lkg", partialRun({ reason: "provider-partial", calls: 3, lkg: 3 }), "partial"],
    ["observation-run-cancelled", cancelledRun(), "cancelled"],
    ["observation-run-provider-offline", partialRun({ reason: "provider-offline", calls: 1, lkg: 5 }), "partial"],
    ["observation-run-no-list", baseRun("not-run", { reason: "no-saved-watchlist", calls: 0, completed: 0 }), "not-run"],
  ];
  const output = {};
  for (const [name, run, expected] of cases) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const telemetry = observe(page);
    await installAccountRuntime(page, run, { refreshEnabled: false, refreshReason: run.reason, noList: name === "observation-run-no-list" });
    try {
      await openAttention(page);
      await loadAccountReviewView(page);
      await page.locator(`[data-observation-run-status="${expected}"]`).waitFor({ state: "visible" });
      const state = await inspect(page);
      assert(!state.horizontalOverflow, `${name} overflows horizontally`);
      assert(state.liveRegionCount >= 1, `${name} has no aria-live status region`);
      assertCleanTelemetry(telemetry, name);
      output[name] = { ...state, providerRequestCount: 0, screenshot: await screenshot(page, name, false), errors: telemetry.errors };
    } finally {
      await context.close();
    }
  }
  return output;
}

async function captureRuntimeOffline() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await page.route("**/api/account/**", (route) => route.fulfill(serviceUnavailableResponse()));
  try {
    await openAttention(page);
    await page.getByRole("button", { name: "Use account review", exact: true }).click();
    await page.locator('[data-attention-account-state="offline"]').waitFor({ state: "visible" });
    const state = await inspect(page);
    assert(state.visibleCount > 0, "runtime outage removed retained Attention evidence");
    const outageTelemetry = assertControlledOfflineTelemetry(telemetry, "runtime offline");
    return {
      ...state,
      providerRequestCount: 0,
      screenshot: await screenshot(page, "observation-run-runtime-offline", false),
      errors: outageTelemetry.unexpected,
      expectedErrors: outageTelemetry.expected,
    };
  } finally {
    await context.close();
  }
}

async function captureDrilldownReturn() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installAccountRuntime(page, completedRun({ materialChanges: 4 }));
  try {
    await openAttention(page);
    await loadAccountReviewView(page);
    const screenshots = {};
    for (const destination of ["News", "Brief", "Map", "Analyst"]) {
      const link = await selectAttentionDestination(page, destination);
      await link.click();
      await page.getByRole("link", { name: "Return to Attention Desk", exact: true }).waitFor({ state: "visible", timeout: 120_000 });
      screenshots[destination.toLowerCase()] = await screenshot(page, `observation-run-drilldown-${destination.toLowerCase()}`, false);
      await page.getByRole("link", { name: "Return to Attention Desk", exact: true }).click();
      await page.locator('[data-phase6m-attention-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
      assert(new URL(page.url()).searchParams.get("view") === "attention-desk", `${destination} return lost Attention origin`);
      if (destination !== "Analyst") await loadAccountReviewView(page);
    }
    assertCleanTelemetry(telemetry, "Attention drilldown return journey");
    return {
      routes: ["News", "Brief", "Map", "Analyst"],
      returned: true,
      screenshots,
      providerRequestCount: 0,
      cancelledRequestCount: telemetry.cancelledRequests.length,
      errors: telemetry.errors,
    };
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
    const telemetry = observe(page);
    await openAttention(page);
    if (!(await localSignIn(page, "analyst-a"))) return { available: false, reason: "local-auth-disabled", errors: telemetry.errors };
    await loadAccountReviewView(page);
    const row = page.locator('.attention-queue-row[data-attention-review-state="new"]').first();
    await row.waitFor({ state: "visible" });
    const title = ((await row.locator("h4").textContent()) || "").trim();
    assert(Boolean(title), "Account A review row has no title");
    await row.getByRole("button", { name: "Review", exact: true }).click();
    await page.getByText("Account state saved", { exact: false }).waitFor({ state: "visible" });
    assertCleanTelemetry(telemetry, "Account A review");
    return { available: true, title, screenshot: await screenshot(page, "attention-account-a-reviewed", false), errors: telemetry.errors };
  });
  if (!accountA.available) return accountA;

  const accountB = await withDedicatedPage(async (page) => {
    const telemetry = observe(page);
    await openAttention(page);
    assert(await localSignIn(page, "analyst-b"), "Account B sign-in unavailable");
    await loadAccountReviewView(page);
    const same = page.locator(".attention-queue-row").filter({ hasText: accountA.title }).first();
    await same.waitFor({ state: "visible" });
    assert(await same.getAttribute("data-attention-review-state") === "new", "Account B observed Account A review state");
    const isolated = await screenshot(page, "attention-account-b-isolated", false);
    await page.route("**/api/account/attention-desk/items/**", (route) => route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ payload_type: "attention_review_state", data: { current_version: 9 } }),
    }));
    await same.getByRole("button", { name: "Review", exact: true }).click();
    await page.getByText("Review version changed", { exact: false }).waitFor({ state: "visible" });
    const conflictTelemetry = assertControlledConflictTelemetry(telemetry, "Account B isolation and conflict");
    return {
      isolated,
      conflict: await screenshot(page, "attention-version-conflict", false),
      errors: conflictTelemetry.unexpected,
      expectedErrors: conflictTelemetry.expected,
    };
  });

  const offline = await withDedicatedPage(async (page) => {
    const telemetry = observe(page);
    await page.route("**/api/account/attention-desk**", (route) => route.fulfill(serviceUnavailableResponse()));
    await openAttention(page);
    await page.getByRole("button", { name: "Use account review", exact: true }).click();
    await page.locator('[data-attention-account-state="offline"]').waitFor({ state: "visible" });
    const state = await inspect(page);
    assert(state.visibleCount > 0, "account outage removed retained Attention evidence");
    const outageTelemetry = assertControlledOfflineTelemetry(telemetry, "Account runtime offline fallback");
    return {
      screenshot: await screenshot(page, "attention-account-offline-local-retained", false),
      errors: outageTelemetry.unexpected,
      expectedErrors: outageTelemetry.expected,
    };
  });

  return {
    available: true,
    isolated: true,
    accountA: accountA.screenshot,
    accountB: accountB.isolated,
    conflict: accountB.conflict,
    offline: offline.screenshot,
    providerRequestCount: 0,
    errors: [...accountA.errors, ...accountB.errors, ...offline.errors],
    expectedErrors: [...accountB.expectedErrors, ...offline.expectedErrors],
  };
}

async function withDedicatedPage(callback) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    return await callback(page);
  } finally {
    await context.close();
  }
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

async function captureRegressions() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  const routes = [
    ["phase6h-analyst", `${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=AAPL`, '[data-phase6h-analyst-workspace="true"]'],
    ["phase6i-operations", `${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=AAPL`, '[data-phase6i-research-operations="true"]'],
    ["phase6l-watchlist", `${baseUrl}/?view=watchlist-desk&mode=fixture&list=primary&selected=AAPL`, '[data-phase6d-watchlist-desk="true"]'],
    ["phase6m-attention", `${baseUrl}/?view=attention-desk&mode=fixture`, '[data-phase6m-attention-desk="true"]'],
  ];
  const output = {};
  try {
    for (const [name, url, selector] of routes) {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 180_000 });
      await page.locator(selector).waitFor({ state: "visible", timeout: 120_000 });
      const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
      assert(!horizontalOverflow, `${name} regression overflows horizontally`);
      output[name] = { horizontalOverflow, screenshot: await screenshot(page, name, false) };
    }
    assertCleanTelemetry(telemetry, "Phase 6H-6M regression surfaces");
    output.providerRequestCount = 0;
    output.errors = telemetry.errors;
    return output;
  } finally {
    await context.close();
  }
}

async function installAccountRuntime(page, initialRun, options = {}) {
  let currentRun = initialRun;
  let postCount = 0;
  let pollCount = 0;
  await page.route("**/api/account/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    if (pathname.endsWith("/attention-desk") && request.method() === "GET") {
      await route.fulfill(jsonResponse(accountEnvelope(currentRun, options)));
      return;
    }
    if (pathname.endsWith("/observation-runs") && request.method() === "POST") {
      postCount += 1;
      currentRun = runningRun();
      await route.fulfill(jsonResponse({ payload_type: "observation_run", data: currentRun }));
      return;
    }
    if (/\/observation-runs\/[^/]+$/.test(pathname) && request.method() === "GET") {
      pollCount += 1;
      if (pollCount >= 3) currentRun = completedRun({ runId: "obsrun_visual_completed", materialChanges: 4 });
      await route.fulfill(jsonResponse({ payload_type: "observation_run", data: currentRun }));
      return;
    }
    if (/\/observation-runs\/[^/]+\/cancel$/.test(pathname) && request.method() === "POST") {
      currentRun = cancelledRun();
      await route.fulfill(jsonResponse({ payload_type: "observation_run", data: currentRun }));
      return;
    }
    await route.fallback();
  });
  return {
    get postCount() { return postCount; },
    get pollCount() { return pollCount; },
  };
}

function accountEnvelope(run, options = {}) {
  const active = ["queued", "running"].includes(run.status);
  const data = structuredClone(fixture.data);
  data.observation_run = {
    observation_run_version: "observation_run.v1",
    mode: "account-local",
    latest_run: active ? completedRun({ runId: "obsrun_previous", materialChanges: 2 }) : run,
    active_run: active ? run : null,
    available_watchlist: options.noList ? null : { resource_id: "wl_visual_daily", name: "Daily Radar", item_count: 5 },
    changes: [],
    material_change_count: run.materialChanges ?? 0,
    source_health: run.provider_states || [],
    refresh_action: {
      enabled: options.refreshEnabled ?? !active,
      reason: options.refreshReason || (active ? "active-run" : "ready"),
      maximum_symbols: 5,
      maximum_provider_calls: 16,
    },
    provider_call_count: 0,
    generated_at: "2026-07-13T14:31:00+00:00",
    caveat: "Controlled account visual evidence; Attention made zero market-provider calls.",
    not_financial_advice: true,
  };
  data.summary = { ...(data.summary || {}), provider_call_count: 0 };
  return { ...fixture, data };
}

function baseRun(status, options = {}) {
  const calls = options.calls ?? 4;
  const lkg = options.lkg ?? 0;
  return {
    observation_run_version: "observation_run.v1",
    mode: "account-local",
    run_id: options.runId || `obsrun_visual_${status}`,
    watchlist_resource_id: "wl_visual_daily",
    watchlist_name: "Daily Radar",
    status,
    requested_count: 5,
    completed_count: options.completed ?? (status === "completed" ? 5 : status === "running" ? 2 : lkg),
    failed_count: status === "partial" ? Math.max(1, 5 - lkg) : status === "failed" ? 5 : 0,
    skipped_count: 0,
    lkg_reused_count: lkg,
    provider_call_budget: 16,
    provider_call_count: calls,
    provider_budget: { maximum_calls: 16, actual_calls: calls, cache_hits: options.cacheHits ?? 1, stale_hits: lkg },
    session: { policy: "market-aware", calendar_status: options.sessionState || "proxy-unverified", market_open_claimed: false },
    provider_states: [{ provider: "yfinance", operation: "history", configured: true, contacted: calls > 0, source_status: options.reason || "cached" }],
    skipped_capabilities: options.reason ? [{ provider: "all", capability: "refresh", reason: options.reason }] : [],
    missing_capabilities: status === "partial" ? [{ symbol: "NVDA", provider: "yfinance", source_status: options.reason || "unavailable", reason: options.reason || "controlled-partial" }] : [],
    cancellation_requested: status === "cancelled",
    attempted_at: "2026-07-13T14:30:00+00:00",
    retrieved_at: status === "running" ? null : "2026-07-13T14:30:04+00:00",
    completed_at: ["queued", "running"].includes(status) ? null : "2026-07-13T14:30:05+00:00",
    materialChanges: options.materialChanges ?? 0,
    reason: options.reason || "ready",
    not_financial_advice: true,
  };
}

function runningRun() { return baseRun("running", { runId: "obsrun_visual_active", calls: 1, completed: 1 }); }
function completedRun(options = {}) { return baseRun("completed", { materialChanges: 4, ...options }); }
function partialRun(options = {}) { return baseRun("partial", options); }
function cancelledRun() { return baseRun("cancelled", { calls: 1, completed: 0, reason: "user-cancelled" }); }

async function openAttention(page) {
  await page.goto(`${baseUrl}/?view=attention-desk&mode=cache`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.locator('[data-phase6m-attention-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
  await page.locator(".attention-queue-row").first().waitFor({ state: "visible", timeout: 120_000 });
  await assertProductStyles(page);
}

async function loadAccountReviewView(page) {
  await page.getByRole("button", { name: "Use account review", exact: true }).click();
  await page.locator('[data-attention-review-scope="account"]').waitFor({ state: "visible" });
}

function observe(page) {
  const accountRequests = [];
  const providerRequests = [];
  const errors = [];
  const httpFailures = [];
  const requestFailures = [];
  const cancelledRequests = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/account/")) accountRequests.push(url);
    if (/alphavantage|finnhub|query1\.finance|coingecko|binance|gdelt|usgs|opensky/i.test(url)) providerRequests.push(url);
  });
  page.on("response", (response) => {
    if (response.status() < 400) return;
    httpFailures.push({
      status: response.status(),
      url: response.url(),
      resourceType: response.request().resourceType(),
    });
  });
  page.on("requestfailed", (request) => {
    const failure = {
      url: request.url(),
      resourceType: request.resourceType(),
      errorText: request.failure()?.errorText || "unknown-request-failure",
    };
    if (isExpectedNavigationCancellation(failure)) {
      cancelledRequests.push(failure);
      return;
    }
    requestFailures.push(failure);
  });
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => {
    if (message.type() !== "error" || message.text().includes("favicon")) return;
    // Chromium emits a URL-less console line for HTTP failures. The response
    // listener above records the actionable status, URL, and resource type.
    if (message.text().startsWith("Failed to load resource:")) return;
    errors.push(`console:${message.text()}`);
  });
  return { accountRequests, providerRequests, errors, httpFailures, requestFailures, cancelledRequests };
}

function isExpectedNavigationCancellation(failure) {
  if (failure.errorText !== "net::ERR_ABORTED") return false;
  const url = new URL(failure.url);
  const appOrigin = new URL(baseUrl).origin;
  const nextRscPrefetch = failure.resourceType === "fetch"
    && url.origin === appOrigin
    && url.searchParams.has("_rsc");
  const mapTileDuringRouteExit = failure.resourceType === "image"
    && url.protocol === "https:"
    && url.hostname === "tile.openstreetmap.org";
  return nextRscPrefetch || mapTileDuringRouteExit;
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.querySelector('[data-phase6m-attention-desk="true"]');
    const observation = document.querySelector('[data-phase6n-observation-run="true"]');
    const nav = document.querySelector(".attention-desk-workspace-grid > .product-nav");
    const ids = Array.from(document.querySelectorAll("[id]")).map((node) => node.id);
    const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
    const controls = Array.from(document.querySelectorAll("button,select,input,a[href]"));
    const unlabeledControls = controls.filter((node) => {
      const labels = "labels" in node && node.labels ? Array.from(node.labels).map((item) => item.textContent?.trim()).filter(Boolean).join(" ") : "";
      return !(node.getAttribute("aria-label") || node.getAttribute("title") || node.textContent?.trim() || labels);
    }).length;
    return {
      visibleCount: Number(root?.getAttribute("data-attention-visible-count") || 0),
      providerCalls: Number(root?.getAttribute("data-attention-provider-calls") || -1),
      observationVisible: Boolean(observation),
      observationStatus: observation?.getAttribute("data-observation-run-status"),
      observationHeight: Math.round(observation?.getBoundingClientRect().height || 0),
      productNavWidth: Math.round(nav?.getBoundingClientRect().width || 0),
      rootWidth: Math.round(root?.getBoundingClientRect().width || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      duplicateIds: [...new Set(duplicateIds)],
      unlabeledControls,
      liveRegionCount: document.querySelectorAll('[aria-live="polite"], [aria-live="assertive"]').length,
    };
  });
}

async function inspectFocusVisible(page) {
  const control = page.getByRole("button", { name: "Refresh saved Watchlist", exact: true });
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  });
  const maxTabStops = Math.min(250, await page.locator('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])').count() + 2);
  let last = { visible: false, reached: false, outlineStyle: "unknown", outlineWidth: "0px", tabs: 0 };
  for (let tabs = 1; tabs <= maxTabStops; tabs += 1) {
    await page.keyboard.press("Tab");
    last = await control.evaluate((node, tabCount) => {
      const style = getComputedStyle(node);
      const reached = document.activeElement === node;
      return {
        visible: reached && style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) >= 2,
        reached,
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        tabs: tabCount,
      };
    }, tabs);
    if (last.reached) return last;
  }
  return last;
}

async function assertProductStyles(page) {
  const evidence = await page.evaluate(() => {
    const root = document.querySelector(".attention-desk");
    const grid = document.querySelector(".attention-desk-workspace-grid");
    const rootStyle = root ? getComputedStyle(root) : null;
    const gridStyle = grid ? getComputedStyle(grid) : null;
    return {
      rootBackground: rootStyle?.backgroundColor || "missing",
      rootColor: rootStyle?.color || "missing",
      gridDisplay: gridStyle?.display || "missing",
      linkedStyleSheets: Array.from(document.styleSheets).filter((sheet) => Boolean(sheet.href)).length,
    };
  });
  assert(
    evidence.rootBackground === "rgb(8, 17, 23)" && evidence.gridDisplay === "grid" && evidence.linkedStyleSheets > 0,
    `Global Terminal styles are not loaded: ${JSON.stringify(evidence)}`,
  );
}

async function screenshot(page, name, fullPage) {
  const file = path.join(outputDirectory, `${name}.png`);
  await page.bringToFront();
  await page.evaluate(async () => {
    window.scrollTo(0, 0);
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  const options = { fullPage, animations: "disabled", caret: "hide", omitBackground: false };
  await page.screenshot(options);
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.screenshot({ ...options, path: file });
  const bytes = (await stat(file)).size;
  assert(bytes > 12_000, `${name} screenshot is unexpectedly small (${bytes})`);
  return { file, bytes };
}

function jsonResponse(body) {
  return { status: 200, contentType: "application/json", body: JSON.stringify(body) };
}

function serviceUnavailableResponse() {
  return {
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "controlled-visual-runtime-offline" }),
  };
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertCleanTelemetry(telemetry, label) {
  assert(telemetry.providerRequests.length === 0, `${label} made ${telemetry.providerRequests.length} direct provider requests`);
  assert(telemetry.errors.length === 0, `${label} emitted browser errors: ${telemetry.errors.join(" | ")}`);
  assert(telemetry.requestFailures.length === 0, `${label} emitted request failures: ${formatTelemetry(telemetry.requestFailures)}`);
  assert(telemetry.httpFailures.length === 0, `${label} emitted HTTP failures: ${formatTelemetry(telemetry.httpFailures)}`);
}

function assertControlledOfflineTelemetry(telemetry, label) {
  return assertControlledHttpFailureTelemetry(telemetry, label, 503);
}

function assertControlledConflictTelemetry(telemetry, label) {
  return assertControlledHttpFailureTelemetry(telemetry, label, 409);
}

function assertControlledHttpFailureTelemetry(telemetry, label, status) {
  assert(telemetry.providerRequests.length === 0, `${label} made ${telemetry.providerRequests.length} direct provider requests`);
  assert(telemetry.errors.length === 0, `${label} emitted browser errors: ${telemetry.errors.join(" | ")}`);
  assert(telemetry.requestFailures.length === 0, `${label} emitted request failures: ${formatTelemetry(telemetry.requestFailures)}`);
  const expected = telemetry.httpFailures.filter((failure) => failure.status === status);
  const unexpected = telemetry.httpFailures.filter((failure) => failure.status !== status);
  assert(expected.length >= 1, `${label} did not record the controlled HTTP ${status} failure`);
  assert(unexpected.length === 0, `${label} emitted unexpected HTTP failures: ${formatTelemetry(unexpected)}`);
  return { expected, unexpected };
}

function formatTelemetry(entries) {
  return entries.map((entry) => JSON.stringify(entry)).join(" | ");
}
