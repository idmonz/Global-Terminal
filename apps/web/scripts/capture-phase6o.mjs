import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3267";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6o_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const fixture = JSON.parse(await readFile(path.join(repoRoot, "static", "api-fixtures", "watchlist-alert-manager.json"), "utf8"));

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const report = {
  evidence_version: "phase6o.visual.v1",
  product_phase: "Phase 6O",
  base_url: baseUrl,
  captured_at: new Date().toISOString(),
  captures: {},
};

try {
  report.captures.initialHtml = await measureInitialHtml();
  report.captures.journey = await captureCreateEvaluateHistoryJourney();
  report.captures.mobile = await captureMobileHistory();
  report.captures.states = await captureFailureAndLifecycleStates();
  report.captures.conflict = await captureOptimisticConflict();
  report.captures.account = await captureAccountIsolation();
  report.captures.drilldown = await captureDrilldownReturn();
  report.passed = true;
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function measureInitialHtml() {
  const response = await fetch(`${baseUrl}/?view=alert-manager&mode=fixture`);
  const html = await response.text();
  const bytes = Buffer.byteLength(html, "utf8");
  assert(response.ok, `Alert Manager initial HTML returned ${response.status}`);
  assert(html.includes("Watchlist Alert Manager"), "Alert Manager marker is absent from initial HTML");
  assert(bytes < 100_000, `Alert Manager initial HTML is ${bytes} bytes`);
  return { status: response.status, bytes, limit_bytes: 100_000, passed: true };
}

async function captureCreateEvaluateHistoryJourney() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  const controller = await installManagerRuntime(page, emptyManagerData());
  try {
    await openManager(page, "rules");
    const create = await screenshot(page, "alert-manager-create-empty-desktop", true);
    await page.getByRole("button", { name: "Create rule", exact: true }).click();
    await page.locator(".alert-rule-table tbody tr").first().waitFor({ state: "visible" });
    await page.getByText(/rule created/i).waitFor({ state: "visible" });
    const activeState = await inspect(page);
    const active = await screenshot(page, "alert-manager-active-rule-desktop", false);

    await page.getByRole("button", { name: "Run due checks", exact: true }).click();
    await page.locator(".alert-trigger-list article").first().waitFor({ state: "visible" });
    await page.getByText(/Due rules evaluated/i).waitFor({ state: "visible" });
    const history = await screenshot(page, "alert-manager-trigger-history-desktop", true);
    const state = await inspect(page);
    const focusEvidence = await inspectFocusVisible(page, "Create rule");

    assert(controller.createCount === 1, `expected one rule create, received ${controller.createCount}`);
    assert(controller.evaluationCount === 1, `expected one evaluation, received ${controller.evaluationCount}`);
    assert(activeState.ruleCount === 1, `expected one visible rule, received ${activeState.ruleCount}`);
    assert(state.triggerCount === 1, `expected one visible trigger, received ${state.triggerCount}`);
    assert(state.productNavWidth >= 160, `ProductNav is crushed at ${state.productNavWidth}px`);
    assert(!state.horizontalOverflow, "desktop journey overflows horizontally");
    assert(state.duplicateIds.length === 0, `duplicate ids: ${state.duplicateIds.join(", ")}`);
    assert(state.unlabeledControls === 0, `${state.unlabeledControls} controls lack labels`);
    assert(state.liveRegionCount >= 1, "Alert Manager has no live status region");
    assert(focusEvidence.visible, `Create rule lacks visible keyboard focus: ${JSON.stringify(focusEvidence)}`);
    assertCleanTelemetry(telemetry, "create/evaluate/history journey");
    return {
      ...state,
      ruleCount: activeState.ruleCount,
      focusVisible: focusEvidence.visible,
      focusEvidence,
      create,
      active,
      history,
      createRequests: controller.createCount,
      evaluationRequests: controller.evaluationCount,
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureMobileHistory() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installManagerRuntime(page, accountAData());
  try {
    await openManager(page, "history");
    const state = await inspect(page);
    const firstTriggerTop = await page.locator(".alert-trigger-list article").first().evaluate((node) => Math.round(node.getBoundingClientRect().top));
    assert(!state.horizontalOverflow, "390px Alert Manager overflows horizontally");
    assert(state.rootWidth <= 390, `mobile root width is ${state.rootWidth}px`);
    assert(state.productNavWidth <= 390, `mobile ProductNav width is ${state.productNavWidth}px`);
    assert(state.liveRegionCount >= 1, "mobile Alert Manager has no live status region");
    assert(firstTriggerTop < 844, `mobile trigger starts below the first viewport at ${firstTriggerTop}px`);
    assertCleanTelemetry(telemetry, "mobile history");
    return {
      ...state,
      firstTriggerTop,
      screenshot: await screenshot(page, "alert-manager-mobile-390x844", false),
      tallScreenshot: await screenshot(page, "alert-manager-mobile-390x844-tall", true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureFailureAndLifecycleStates() {
  const cases = [
    ["alert-manager-lifecycle", lifecycleData(), "rules"],
    ["alert-manager-quota-blocked", evaluationState("quota-blocked", "daily-quota-exhausted", 1), "runs"],
    ["alert-manager-partial-lkg", evaluationState("partial", "last-known-good-used", 2), "runs"],
    ["alert-manager-provider-unavailable", evaluationState("partial", "provider-unavailable", 1), "runs"],
    ["alert-manager-worker-offline", workerState("offline", 0), "rules"],
    ["alert-manager-worker-restarted", workerState("restarted", 1), "rules"],
  ];
  const output = {};
  for (const [name, data, tab] of cases) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const telemetry = observe(page);
    await installManagerRuntime(page, data);
    try {
      await openManager(page, tab);
      const state = await inspect(page);
      assert(!state.horizontalOverflow, `${name} overflows horizontally`);
      assertCleanTelemetry(telemetry, name);
      output[name] = {
        ...state,
        screenshot: await screenshot(page, name, true),
        providerRequestCount: telemetry.providerRequests.length,
        errors: telemetry.errors,
      };
    } finally {
      await context.close();
    }
  }
  return output;
}

async function captureOptimisticConflict() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installManagerRuntime(page, accountAData(), { conflictOnce: true });
  try {
    await openManager(page, "rules");
    await page.getByTitle("Pause rule").first().click();
    await page.getByText(/changed in another session/i).waitFor({ state: "visible" });
    const state = await inspect(page);
    assert(telemetry.httpFailures.some((row) => row.status === 409), "controlled conflict did not emit HTTP 409");
    assertCleanTelemetry(telemetry, "optimistic conflict", [409]);
    return {
      ...state,
      screenshot: await screenshot(page, "alert-manager-version-conflict", true),
      expectedErrors: telemetry.httpFailures.filter((row) => row.status === 409),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureAccountIsolation() {
  const accountB = await captureAccount("alert-manager-account-b-isolated", emptyManagerData(), 0, 0);
  const accountA = await captureAccount("alert-manager-account-a", accountAData(), 2, 1);
  return { available: true, isolated: true, accountA, accountB, providerRequestCount: 0, errors: [] };
}

async function captureAccount(name, data, expectedRules, expectedTriggers) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installManagerRuntime(page, data);
  try {
    await openManager(page, "rules");
    const rulesState = await inspect(page);
    const accountScreenshot = await elementScreenshot(page, ".alert-manager-main", name);
    await page.getByRole("tab", { name: /Trigger history/ }).click();
    const state = await inspect(page);
    assert(rulesState.ruleCount === expectedRules, `${name} expected ${expectedRules} rules, received ${rulesState.ruleCount}`);
    assert(state.triggerCount === expectedTriggers, `${name} expected ${expectedTriggers} triggers, received ${state.triggerCount}`);
    assertCleanTelemetry(telemetry, name);
    return {
      ...state,
      ruleCount: rulesState.ruleCount,
      screenshot: accountScreenshot,
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureDrilldownReturn() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  const screenshots = {};
  try {
    await page.goto(`${baseUrl}/?view=alert-manager&mode=fixture&tab=history`, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await waitForManager(page, "fixture");
    for (const label of ["Analyst", "News", "Brief", "Map"]) {
      await page.locator(".alert-evidence-links").getByRole("link", { name: label, exact: true }).click();
      const returnLink = page.getByRole("link", { name: "Return to Alert Manager", exact: true }).first();
      await returnLink.waitFor({ state: "visible", timeout: 120_000 });
      assert(new URL(page.url()).searchParams.get("mode") === "fixture", `${label} drilldown escaped fixture mode`);
      screenshots[label.toLowerCase()] = await screenshot(page, `alert-manager-drilldown-${label.toLowerCase()}`, false);
      await returnLink.click();
      await waitForManager(page, "fixture");
      assert(new URL(page.url()).searchParams.get("tab") === "history", `${label} did not restore trigger history`);
      assert(new URL(page.url()).searchParams.get("selectedTrigger") === "fixture-alert-trigger-aapl", `${label} did not restore selected trigger`);
    }
    assertCleanTelemetry(telemetry, "exact drilldown/return");
    return {
      routes: ["Analyst", "News", "Brief", "Map"],
      returned: true,
      screenshots,
      cancelledRequestCount: telemetry.cancelledRequests.length,
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function installManagerRuntime(page, initialData, options = {}) {
  let data = recalculate(clone(initialData));
  let createCount = 0;
  let evaluationCount = 0;
  let conflictUsed = false;
  await page.route("**/api/account/alert-manager**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    if (pathname.endsWith("/alert-manager") && request.method() === "GET") {
      await route.fulfill(jsonResponse(accountEnvelope(data)));
      return;
    }
    if (pathname.endsWith("/alert-manager/rules") && request.method() === "POST") {
      createCount += 1;
      const body = request.postDataJSON();
      const rule = clone(fixture.data.rules[0]);
      Object.assign(rule, body, {
        resource_id: `visual-rule-${createCount}`,
        state: "active",
        state_reason: "scheduled",
        version: 1,
        metric: body.rule_type === "source_degradation" ? "source_status" : "last_price",
        operator: body.rule_type === "price_below" ? "below" : "above",
      });
      data.rules.push(rule);
      data = recalculate(data);
      await route.fulfill(jsonResponse(actionEnvelope("watchlist_alert_rule", "created", { rule }), 201));
      return;
    }
    if (pathname.endsWith("/alert-manager/evaluations") && request.method() === "POST") {
      evaluationCount += 1;
      const evaluation = clone(fixture.data.evaluations[0]);
      evaluation.run_id = `visual-evaluation-${evaluationCount}`;
      const trigger = clone(fixture.data.triggers[0]);
      trigger.trigger_id = `visual-trigger-${evaluationCount}`;
      trigger.rule_id = data.rules[0]?.resource_id || "visual-rule-1";
      trigger.message = `${trigger.symbol} matched the controlled stored observation.`;
      trigger.evidence_links = clone(fixture.data.triggers[0].evidence_links);
      data.evaluations.unshift(evaluation);
      data.triggers.unshift(trigger);
      data = recalculate(data);
      await route.fulfill(jsonResponse(actionEnvelope("watchlist_alert_evaluation", "completed", { evaluation }), 201));
      return;
    }
    if (/\/alert-manager\/rules\/[^/]+$/.test(pathname) && request.method() === "PATCH") {
      if (options.conflictOnce && !conflictUsed) {
        conflictUsed = true;
        await route.fulfill(jsonResponse(actionEnvelope("watchlist_alert_rule", "conflict", { current_version: 2 }), 409));
        return;
      }
      const id = decodeURIComponent(pathname.split("/").at(-1));
      const body = request.postDataJSON();
      const rule = data.rules.find((row) => row.resource_id === id);
      if (rule) {
        rule.state = body.action === "resume" ? "active" : body.action === "pause" ? "paused" : "cancelled";
        rule.state_reason = `${body.action}-requested`;
        rule.version = Number(rule.version || 1) + 1;
      }
      data = recalculate(data);
      await route.fulfill(jsonResponse(actionEnvelope("watchlist_alert_rule", rule?.state || "updated", { rule })));
      return;
    }
    if (/\/alert-manager\/rules\/[^/]+$/.test(pathname) && request.method() === "DELETE") {
      const id = decodeURIComponent(pathname.split("/").at(-1));
      data.rules = data.rules.filter((row) => row.resource_id !== id);
      data = recalculate(data);
      await route.fulfill(jsonResponse(actionEnvelope("watchlist_alert_rule", "deleted", { resource_id: id, deleted: true })));
      return;
    }
    if (/\/alert-manager\/triggers\/[^/]+$/.test(pathname) && request.method() === "PATCH") {
      const id = decodeURIComponent(pathname.split("/").at(-1));
      const trigger = data.triggers.find((row) => row.trigger_id === id);
      if (trigger) {
        trigger.review_state = "acknowledged";
        trigger.version = Number(trigger.version || 1) + 1;
        trigger.clocks.reviewed_at = "2026-07-15T14:05:00+00:00";
      }
      data = recalculate(data);
      await route.fulfill(jsonResponse(actionEnvelope("watchlist_alert_trigger", "acknowledged", { trigger })));
      return;
    }
    await route.fallback();
  });
  return {
    get createCount() { return createCount; },
    get evaluationCount() { return evaluationCount; },
  };
}

function emptyManagerData() {
  const data = clone(fixture.data);
  data.rules = [];
  data.triggers = [];
  data.evaluations = [];
  data.worker = { ...data.worker, state: "stopped", reason: "explicit-opt-in-required" };
  return recalculate(data);
}

function accountAData() { return recalculate(clone(fixture.data)); }

function lifecycleData() {
  const data = accountAData();
  const paused = clone(data.rules[1]);
  const expired = { ...clone(data.rules[0]), resource_id: "visual-expired", symbol: "MSFT", state: "expired", state_reason: "expiration-reached" };
  const cancelled = { ...clone(data.rules[0]), resource_id: "visual-cancelled", symbol: "NVDA", state: "cancelled", state_reason: "cancel-requested" };
  data.rules = [data.rules[0], paused, expired, cancelled];
  return recalculate(data);
}

function evaluationState(status, reason, gaps) {
  const data = accountAData();
  const evaluation = clone(data.evaluations[0]);
  evaluation.status = status;
  evaluation.data_gap_count = gaps;
  evaluation.quota_blocked_count = status === "quota-blocked" ? 1 : 0;
  evaluation.triggered_count = 0;
  evaluation.detail = { market_provider_calls: 0, reason };
  data.evaluations = [evaluation];
  data.triggers = [];
  data.rules[0].state_reason = reason;
  return recalculate(data);
}

function workerState(state, restartCount) {
  const data = accountAData();
  data.worker = { ...data.worker, state, enabled: state !== "offline", restart_count: restartCount, reason: state === "offline" ? "heartbeat-expired" : "manual-restart-verified" };
  return recalculate(data);
}

function recalculate(data) {
  data.summary = {
    ...(data.summary || {}),
    status: "ready",
    rule_count: data.rules.length,
    active_count: data.rules.filter((row) => row.state === "active").length,
    due_count: data.rules.filter((row) => row.state === "active" && row.schedule?.next_due_at).length,
    trigger_count: data.triggers.length,
    new_trigger_count: data.triggers.filter((row) => row.review_state === "new").length,
    provider_call_count: 0,
  };
  return data;
}

function accountEnvelope(data) {
  const envelope = clone(fixture);
  envelope.data = recalculate(clone(data));
  envelope.status = "ready";
  envelope.summary = { ...(envelope.summary || {}), status: "ready", provider_call_count: 0 };
  return envelope;
}

function actionEnvelope(payloadType, status, fields) {
  return {
    schema_version: "phase_2b.v1",
    payload_type: payloadType,
    generated_at: "2026-07-15T14:05:00+00:00",
    status,
    source_status: "account-local",
    data: { contract_version: "watchlist_alert_manager.v1", ...fields, summary: { status, provider_call_count: 0 } },
    summary: { status, provider_call_count: 0 },
    caveats: [],
  };
}

async function openManager(page, tab) {
  await page.goto(`${baseUrl}/?view=alert-manager&mode=cache&tab=${tab}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await waitForManager(page, "ready");
  await assertProductStyles(page);
}

async function waitForManager(page, accountState) {
  const root = page.locator('[data-phase6o-alert-manager="true"]');
  await root.waitFor({ state: "visible", timeout: 120_000 });
  await page.locator(`[data-account-state="${accountState}"]`).waitFor({ state: "visible", timeout: 120_000 });
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.querySelector('[data-phase6o-alert-manager="true"]');
    const nav = document.querySelector(".alert-manager-workspace-grid > .product-nav");
    const ids = Array.from(document.querySelectorAll("[id]")).map((node) => node.id);
    const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
    const controls = Array.from(document.querySelectorAll("button,select,input,a[href]"));
    const unlabeledControls = controls.filter((node) => {
      const labels = "labels" in node && node.labels ? Array.from(node.labels).map((item) => item.textContent?.trim()).filter(Boolean).join(" ") : "";
      return !(node.getAttribute("aria-label") || node.getAttribute("title") || node.textContent?.trim() || labels);
    }).length;
    return {
      rootWidth: Math.round(root?.getBoundingClientRect().width || 0),
      productNavWidth: Math.round(nav?.getBoundingClientRect().width || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      duplicateIds: [...new Set(duplicateIds)],
      unlabeledControls,
      liveRegionCount: document.querySelectorAll('[aria-live="polite"], [aria-live="assertive"]').length,
      ruleCount: document.querySelectorAll(".alert-rule-table tbody tr").length,
      triggerCount: document.querySelectorAll(".alert-trigger-list article").length,
      workerState: root?.getAttribute("data-worker-state"),
      accountState: root?.getAttribute("data-account-state"),
    };
  });
}

async function inspectFocusVisible(page, accessibleName) {
  const control = page.getByRole("button", { name: accessibleName, exact: true });
  await page.evaluate(() => { if (document.activeElement instanceof HTMLElement) document.activeElement.blur(); });
  const maxTabs = Math.min(220, await page.locator('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])').count() + 2);
  for (let tabs = 1; tabs <= maxTabs; tabs += 1) {
    await page.keyboard.press("Tab");
    const evidence = await control.evaluate((node, tabCount) => {
      const style = getComputedStyle(node);
      const reached = document.activeElement === node;
      return { visible: reached && style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) >= 2, reached, outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth, tabs: tabCount };
    }, tabs);
    if (evidence.reached) return evidence;
  }
  return { visible: false, reached: false, outlineStyle: "unknown", outlineWidth: "0px", tabs: maxTabs };
}

async function assertProductStyles(page) {
  const styles = await page.evaluate(() => {
    const root = document.querySelector(".alert-manager");
    const grid = document.querySelector(".alert-manager-layout");
    const rootStyle = root ? getComputedStyle(root) : null;
    const gridStyle = grid ? getComputedStyle(grid) : null;
    return { rootDisplay: rootStyle?.display, rootColor: rootStyle?.color, gridDisplay: gridStyle?.display, gridColumns: gridStyle?.gridTemplateColumns };
  });
  assert(styles.rootDisplay !== "none", "Alert Manager product CSS is missing");
  assert(styles.gridDisplay === "grid", `Alert Manager layout is ${styles.gridDisplay}`);
  assert(styles.rootColor && styles.rootColor !== "rgba(0, 0, 0, 0)", "Alert Manager text style is unresolved");
}

function observe(page) {
  const providerRequests = [];
  const errors = [];
  const httpFailures = [];
  const requestFailures = [];
  const cancelledRequests = [];
  page.on("request", (request) => {
    if (/alphavantage|finnhub|query1\.finance|coingecko|binance|gdelt|usgs|opensky/i.test(request.url())) providerRequests.push(request.url());
  });
  page.on("response", (response) => {
    if (response.status() < 400 || response.url().includes("favicon")) return;
    httpFailures.push({ status: response.status(), url: response.url(), resourceType: response.request().resourceType() });
  });
  page.on("requestfailed", (request) => {
    const failure = { url: request.url(), resourceType: request.resourceType(), errorText: request.failure()?.errorText || "unknown-request-failure" };
    if (isExpectedNavigationCancellation(failure)) cancelledRequests.push(failure);
    else requestFailures.push(failure);
  });
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => {
    if (message.type() !== "error" || message.text().includes("favicon") || message.text().startsWith("Failed to load resource:")) return;
    errors.push(`console:${message.text()}`);
  });
  return { providerRequests, errors, httpFailures, requestFailures, cancelledRequests };
}

function isExpectedNavigationCancellation(failure) {
  if (failure.errorText !== "net::ERR_ABORTED") return false;
  const url = new URL(failure.url);
  const appOrigin = new URL(baseUrl).origin;
  return (failure.resourceType === "fetch" && url.origin === appOrigin && url.searchParams.has("_rsc"))
    || (failure.resourceType === "image" && url.hostname === "tile.openstreetmap.org");
}

function assertCleanTelemetry(telemetry, label, allowedStatuses = []) {
  assert(telemetry.providerRequests.length === 0, `${label} made provider requests: ${telemetry.providerRequests.join(" | ")}`);
  assert(telemetry.errors.length === 0, `${label} emitted browser errors: ${telemetry.errors.join(" | ")}`);
  const unexpectedHttp = telemetry.httpFailures.filter((row) => !allowedStatuses.includes(row.status));
  assert(unexpectedHttp.length === 0, `${label} emitted HTTP failures: ${JSON.stringify(unexpectedHttp)}`);
  assert(telemetry.requestFailures.length === 0, `${label} emitted request failures: ${JSON.stringify(telemetry.requestFailures)}`);
}

async function screenshot(page, name, fullPage) {
  const file = path.join(outputDirectory, `${name}.png`);
  if (fullPage) await primeFullPagePaint(page);
  await page.screenshot({ path: file, fullPage, animations: "disabled" });
  const bytes = (await readFile(file)).byteLength;
  assert(bytes > 12_000, `${name}.png is unexpectedly small (${bytes} bytes)`);
  return { file, bytes };
}

async function elementScreenshot(page, selector, name) {
  const file = path.join(outputDirectory, `${name}.png`);
  const target = page.locator(selector);
  await target.scrollIntoViewIfNeeded();
  await target.screenshot({ path: file, animations: "disabled" });
  const bytes = (await readFile(file)).byteLength;
  assert(bytes > 8_000, `${name}.png is unexpectedly small (${bytes} bytes)`);
  return { file, bytes };
}

async function primeFullPagePaint(page) {
  const dimensions = await page.evaluate(() => ({ height: document.documentElement.scrollHeight, viewport: window.innerHeight }));
  const step = Math.max(300, Math.floor(dimensions.viewport * 0.75));
  for (let top = 0; top < dimensions.height; top += step) {
    await page.evaluate((nextTop) => window.scrollTo(0, nextTop), top);
    await page.waitForTimeout(20);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(80);
}

function jsonResponse(body, status = 200) {
  return { status, contentType: "application/json", headers: { "cache-control": "no-store" }, body: JSON.stringify(body) };
}

function clone(value) { return structuredClone(value); }
function assert(condition, message) { if (!condition) throw new Error(message); }
