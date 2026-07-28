import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3367";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6q_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const managerFixture = JSON.parse(await readFile(path.join(repoRoot, "static", "api-fixtures", "watchlist-alert-manager.json"), "utf8"));
const schedulerFixture = JSON.parse(await readFile(path.join(repoRoot, "static", "api-fixtures", "hosted-scheduler-operations.json"), "utf8"));

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const report = {
  evidence_version: "phase6q.visual.v1",
  product_phase: "Phase 6Q",
  base_url: baseUrl,
  captured_at: new Date().toISOString(),
  captures: {},
};

try {
  report.captures.initialHtml = await measureInitialHtml();
  report.captures.safeDefault = await captureSafeDefault();
  report.captures.enableJourney = await captureEnableJourney();
  report.captures.running = await captureState("running", "hosted-schedule-running-desktop");
  report.captures.completed = await captureState("completed", "hosted-schedule-completed-source-desktop");
  report.captures.noDue = await captureState("no-due", "hosted-schedule-no-due-desktop");
  report.captures.idempotentReplay = await captureState("idempotent-replay", "hosted-schedule-idempotent-replay-desktop");
  report.captures.quotaBlocked = await captureState("quota-blocked", "hosted-schedule-quota-blocked-desktop");
  report.captures.providerOffline = await captureState("provider-offline", "hosted-schedule-provider-offline-desktop");
  report.captures.partialLkg = await captureState("partial-lkg", "hosted-schedule-partial-lkg-desktop");
  report.captures.leaseExpired = await captureState("lease-expired", "hosted-schedule-lease-expired-desktop");
  report.captures.recovered = await captureState("recovered", "hosted-schedule-recovered-desktop");
  report.captures.killed = await captureState("killed", "hosted-schedule-killed-desktop");
  report.captures.cleanup = await captureState("cleanup", "hosted-schedule-cleanup-desktop");
  report.captures.accountIsolation = await captureAccountIsolation();
  report.captures.sessionExpired = await captureSessionExpired();
  report.captures.mobile = await captureMobile();
  report.captures.regressions = await captureRegressions();
  report.passed = true;
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function measureInitialHtml() {
  const response = await fetch(`${baseUrl}/?view=alert-manager&mode=fixture&tab=schedule`);
  const html = await response.text();
  const bytes = Buffer.byteLength(html, "utf8");
  assert(response.ok, `Alert Manager initial HTML returned ${response.status}`);
  assert(html.includes("Watchlist Alert Manager"), "Alert Manager marker is absent from initial HTML");
  assert(bytes < 100_000, `Alert Manager initial HTML is ${bytes} bytes`);
  return { status: response.status, bytes, limit_bytes: 100_000, passed: true };
}

async function captureSafeDefault() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  try {
    await page.goto(`${baseUrl}/?view=alert-manager&mode=fixture&tab=schedule`, { waitUntil: "networkidle", timeout: 180_000 });
    await waitForSchedule(page);
    const evidence = await inspect(page);
    assert(evidence.hostedStatus === "hosted-unverified", `safe default status is ${evidence.hostedStatus}`);
    assert(evidence.globalKillVisible, "safe default does not expose the armed global kill switch");
    assert(evidence.unverifiedVisible, "safe default does not expose hosted-unverified truth");
    assert(evidence.scheduleState === "disabled", `safe default schedule is ${evidence.scheduleState}`);
    assertEvidence(evidence, "safe default");
    assertCleanTelemetry(telemetry, "safe default");
    return {
      ...evidence,
      screenshot: await screenshot(page, "hosted-schedule-safe-default-desktop", true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureEnableJourney() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  const controller = await installRuntime(page, schedulerState("disabled"));
  try {
    await openRuntimeSchedule(page);
    const consent = page.locator(".hosted-consent input").first();
    await consent.check();
    const enable = page.getByRole("button", { name: "Enable", exact: true });
    await page.keyboard.press("Tab");
    const focus = await inspectFocus(enable);
    assert(focus.visible, `Enable lacks visible keyboard focus: ${JSON.stringify(focus)}`);
    await enable.click();
    await page.locator('.hosted-schedule-card[data-schedule-state="enabled"]').waitFor({ state: "visible" });
    const evidence = await inspect(page);
    assert(controller.patchCount === 1, `expected one bounded control mutation, received ${controller.patchCount}`);
    assert(evidence.scheduleState === "enabled", `enable journey ended in ${evidence.scheduleState}`);
    assert(evidence.unverifiedVisible, "controlled enable incorrectly promoted hosted verification");
    assertEvidence(evidence, "enable journey");
    assertCleanTelemetry(telemetry, "enable journey");
    return {
      ...evidence,
      focus,
      patchCount: controller.patchCount,
      screenshot: await screenshot(page, "hosted-schedule-enabled-unverified-desktop", true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureState(state, filename) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 950 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installRuntime(page, schedulerState(state));
  try {
    await openRuntimeSchedule(page);
    const evidence = await inspect(page);
    const expectedSchedule = ["killed", "cleanup"].includes(state) ? (state === "cleanup" ? "deleted" : "killed") : "enabled";
    const expectedRun = {
      running: "running",
      completed: "completed",
      "idempotent-replay": "completed",
      "quota-blocked": "quota-blocked",
      "provider-offline": "provider-unavailable",
      "partial-lkg": "partial",
      "lease-expired": "failed",
      recovered: "partial",
    }[state];
    assert(evidence.scheduleState === expectedSchedule, `${state} state card is ${evidence.scheduleState}`);
    if (expectedRun) assert(evidence.latestRunStatus === expectedRun, `${state} run truth is ${evidence.latestRunStatus}`);
    if (state === "no-due") assert(evidence.latestRunStatus === "", "no-due state substituted a run");
    if (state === "killed") assert(evidence.globalKillVisible, "killed state does not expose the global kill switch");
    assertEvidence(evidence, state);
    assertCleanTelemetry(telemetry, state);
    return {
      ...evidence,
      screenshot: await screenshot(page, filename, true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureAccountIsolation() {
  const accountA = await captureAccount("account-a", schedulerState("completed"), 1, "hosted-schedule-account-a-desktop");
  const accountB = await captureAccount("account-b", schedulerState("empty"), 0, "hosted-schedule-account-b-isolated-desktop");
  assert(accountA.scheduleCount === 1 && accountB.scheduleCount === 0, "controlled Account A/B schedule rows are not isolated");
  return { isolated: true, accountA, accountB, providerRequestCount: 0, errors: [] };
}

async function captureAccount(label, state, expectedCount, filename) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installRuntime(page, state);
  try {
    await openRuntimeSchedule(page);
    const evidence = await inspect(page);
    const scheduleCount = await page.locator(".hosted-schedule-card").count();
    assert(scheduleCount === expectedCount, `${label} expected ${expectedCount} schedule rows, received ${scheduleCount}`);
    assertEvidence(evidence, label);
    assertCleanTelemetry(telemetry, label);
    return {
      ...evidence,
      scheduleCount,
      screenshot: await screenshot(page, filename, true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureSessionExpired() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await page.route("**/api/account/alert-manager", async (route) => route.fulfill(jsonResponse({ detail: "Controlled expired session." }, 401)));
  try {
    await page.goto(`${baseUrl}/?view=alert-manager&mode=cache&tab=schedule`, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.locator('.alert-manager[data-account-state="signed-out"]').waitFor({ state: "visible", timeout: 120_000 });
    await waitForSchedule(page);
    const evidence = await inspect(page);
    assert(documentText(await page.locator("body").textContent()).includes("Sign-in required"), "session expiry truth is absent");
    assertEvidence(evidence, "session expired");
    assertControlledTelemetry(telemetry, "session expired", [401]);
    return {
      ...evidence,
      screenshot: await screenshot(page, "hosted-schedule-session-expired-desktop", true),
      providerRequestCount: telemetry.providerRequests.length,
      expectedHttpStatus: 401,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureRegressions() {
  const routes = [
    ["alert-manager", "/?view=alert-manager&mode=fixture&tab=rules"],
    ["watchlist", "/?view=watchlist-desk&mode=fixture&list=primary"],
    ["attention", "/?view=attention-desk&mode=fixture"],
    ["analyst", "/?view=analyst-workspace&symbol=AAPL&assetClass=equity&mode=fixture"],
    ["map", "/?view=war-room-map&mode=fixture"],
    ["news", "/?view=news&mode=fixture"],
  ];
  const output = {};
  for (const [name, route] of routes) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const telemetry = observe(page);
    try {
      await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
      await page.locator("main").first().waitFor({ state: "visible", timeout: 120_000 });
      await page.evaluate(() => document.fonts.ready);
      const layout = await page.evaluate(() => ({
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
        rootWidth: Math.round(document.documentElement.getBoundingClientRect().width),
      }));
      assert(!layout.horizontalOverflow, `${name} regression surface overflows horizontally`);
      assert(telemetry.errors.length === 0, `${name} regression emitted browser errors: ${telemetry.errors.join(" | ")}`);
      assert(telemetry.providerRequests.length === 0, `${name} regression contacted a market provider`);
      output[name] = {
        ...layout,
        screenshot: await screenshot(page, `phase6q-regression-${name}`, false),
        providerRequestCount: telemetry.providerRequests.length,
        errors: telemetry.errors,
      };
    } finally {
      await context.close();
    }
  }
  return { routes: Object.keys(output), surfaces: output, providerRequestCount: 0, errors: [] };
}

async function captureMobile() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installRuntime(page, schedulerState("partial-lkg"));
  try {
    await openRuntimeSchedule(page);
    const evidence = await inspect(page);
    assert(evidence.rootWidth <= 390, `390px root is ${evidence.rootWidth}px wide`);
    assert(evidence.panelWidth <= 390, `390px scheduler panel is ${evidence.panelWidth}px wide`);
    assertEvidence(evidence, "mobile");
    assertCleanTelemetry(telemetry, "mobile");
    return {
      ...evidence,
      screenshot: await screenshot(page, "hosted-schedule-mobile-390x844", false),
      tallScreenshot: await screenshot(page, "hosted-schedule-mobile-390x844-tall", true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function openRuntimeSchedule(page) {
  await page.goto(`${baseUrl}/?view=alert-manager&mode=cache&tab=schedule`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.locator('.alert-manager[data-account-state="ready"]').waitFor({ state: "visible", timeout: 120_000 });
  await waitForSchedule(page);
  await page.evaluate(() => document.fonts.ready);
}

async function waitForSchedule(page) {
  await page.locator(".hosted-schedule-panel").waitFor({ state: "visible", timeout: 120_000 });
  await page.getByText("At-least-once, idempotent effects", { exact: true }).waitFor({ state: "visible" });
  await page.evaluate(() => document.fonts.ready);
}

async function installRuntime(page, initialScheduler) {
  let scheduler = structuredClone(initialScheduler);
  let patchCount = 0;
  await page.route("**/api/account/alert-manager/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/account/alert-manager/scheduler") {
      await route.fulfill(jsonResponse(scheduler));
      return;
    }
    if (url.pathname.startsWith("/api/account/alert-manager/scheduler/schedules/") && route.request().method() === "PATCH") {
      patchCount += 1;
      const body = route.request().postDataJSON();
      scheduler = schedulerState(body?.action === "enable" ? "enabled" : String(body?.action || "disabled"));
      await route.fulfill(jsonResponse(scheduler));
      return;
    }
    await route.fulfill(jsonResponse({ detail: "Controlled Phase 6Q route." }, 404));
  });
  await page.route("**/api/account/alert-manager", async (route) => route.fulfill(jsonResponse(managerFixture)));
  return { get patchCount() { return patchCount; } };
}

function schedulerState(state) {
  const envelope = structuredClone(schedulerFixture);
  const data = envelope.data;
  const schedule = data.schedules[0];
  const runStatus = {
    running: "running",
    completed: "completed",
    "idempotent-replay": "completed",
    "quota-blocked": "quota-blocked",
    "provider-offline": "provider-unavailable",
    "partial-lkg": "partial",
    "lease-expired": "failed",
    recovered: "partial",
  }[state];
  const scheduleState = state === "killed" ? "killed" : state === "cleanup" ? "deleted" : state === "disabled" ? "disabled" : "enabled";
  schedule.state = scheduleState;
  schedule.enabled_at = scheduleState === "enabled" ? "2026-07-27T06:00:00Z" : null;
  schedule.killed_at = state === "killed" ? "2026-07-27T06:20:00Z" : null;
  schedule.deleted_at = state === "cleanup" ? "2026-07-27T06:30:00Z" : null;
  schedule.last_completed_at = ["completed", "idempotent-replay", "partial-lkg", "recovered"].includes(state) ? "2026-07-27T06:17:00Z" : null;
  schedule.next_due_at = schedule.state === "enabled" ? "2026-07-27T07:17:00Z" : null;
  data.readiness = {
    configured_is_not_verified: true,
    global_kill_switch: state === "killed" || state === "disabled" || state === "cleanup",
    hosted_scheduler_verified: false,
    operator_enabled: !["killed", "disabled", "cleanup"].includes(state),
    status: "hosted-unverified",
  };
  data.summary = {
    schedule_count: 1,
    enabled_count: schedule.state === "enabled" ? 1 : 0,
    active_run_count: 0,
    completed_run_count: ["completed", "idempotent-replay", "partial-lkg", "recovered"].includes(state) ? 1 : 0,
    provider_call_count: 0,
    status: state,
  };
  data.runs = runStatus ? [{
    scheduler_run_id: "controlled-visual-run",
    status: runStatus,
    attempt_count: state === "recovered" ? 2 : 1,
    trigger_count: state === "completed" || state === "idempotent-replay" ? 1 : 0,
    source: {
      provider: state === "completed" || state === "idempotent-replay" ? "yfinance" : "controlled-visual-fixture",
      source_status: state === "completed" || state === "idempotent-replay" ? "live/fresh" : state === "provider-offline" ? "unavailable" : "fixture",
    },
    quota: state === "quota-blocked" ? { used: 4, budget: 4, remaining: 0 } : { used: state === "completed" ? 1 : 0, budget: 4, remaining: state === "completed" ? 3 : 4 },
    clocks: { completed_at: "2026-07-27T06:17:00Z" },
    result: {
      caveat: state === "idempotent-replay" ? "Controlled replay fixture; duplicate effects were suppressed." : "Controlled visual fixture. This is not deployed hosted evidence.",
      data_gap: state === "completed" ? "No licensed realtime stream." : state === "lease-expired" ? "Lease expired before completion; recovery remains explicit." : "Provider was unavailable or controlled; prior last-known-good evidence is retained.",
    },
  }] : [];
  if (state === "empty") {
    data.schedules = [];
    data.runs = [];
    data.latest_run = null;
    data.summary.schedule_count = 0;
    data.summary.enabled_count = 0;
  }
  data.latest_run = data.runs[0] || null;
  envelope.summary = data.summary;
  return envelope;
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const panel = document.querySelector(".hosted-schedule-panel");
    const productNav = document.querySelector(".product-nav");
    const card = document.querySelector(".hosted-schedule-card");
    const runStatus = document.querySelector(".hosted-run-summary .alert-state");
    const visibleControls = [...document.querySelectorAll("button, input, select")].filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
    const unlabeledControls = visibleControls.filter((node) => {
      if (node.getAttribute("aria-label") || node.getAttribute("title")) return false;
      if (node instanceof HTMLButtonElement) return !node.textContent?.trim();
      return !node.closest("label") && !node.id;
    }).length;
    return {
      rootWidth: Math.round(root.getBoundingClientRect().width),
      panelWidth: panel ? Math.round(panel.getBoundingClientRect().width) : 0,
      productNavWidth: productNav ? Math.round(productNav.getBoundingClientRect().width) : 0,
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
      hostedStatus: panel?.getAttribute("data-hosted-status") || "",
      scheduleState: card?.getAttribute("data-schedule-state") || "",
      latestRunStatus: runStatus?.textContent?.trim() || "",
      globalKillVisible: document.body.textContent?.includes("Global kill armed") || false,
      unverifiedVisible: document.body.textContent?.includes("Hosted unverified") || false,
      atLeastOnceVisible: document.body.textContent?.includes("At-least-once, idempotent effects") || false,
      zeroCallVisible: document.body.textContent?.includes("Reads: 0 provider calls") || false,
      liveRegionCount: document.querySelectorAll('[aria-live], [role="status"]').length,
      unlabeledControls,
      duplicateIds: [...document.querySelectorAll("[id]")].map((node) => node.id).filter((id, index, all) => all.indexOf(id) !== index),
    };
  });
}

async function inspectFocus(locator) {
  return locator.evaluate((node) => {
    const style = getComputedStyle(node);
    return {
      reached: document.activeElement === node,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      visible: document.activeElement === node && style.outlineStyle !== "none" && parseFloat(style.outlineWidth) >= 2,
    };
  });
}

function assertEvidence(evidence, label) {
  assert(!evidence.horizontalOverflow, `${label} overflows horizontally`);
  assert(evidence.duplicateIds.length === 0, `${label} has duplicate ids: ${evidence.duplicateIds.join(", ")}`);
  assert(evidence.unlabeledControls === 0, `${label} has ${evidence.unlabeledControls} unlabeled controls`);
  assert(evidence.liveRegionCount >= 1, `${label} has no live status region`);
  assert(evidence.atLeastOnceVisible, `${label} hides at-least-once semantics`);
  assert(evidence.zeroCallVisible, `${label} hides zero-call read truth`);
}

function observe(page) {
  const telemetry = { errors: [], requestFailures: [], httpFailures: [], providerRequests: [] };
  page.on("console", (message) => { if (message.type() === "error") telemetry.errors.push(`console:${message.text()}`); });
  page.on("pageerror", (error) => telemetry.errors.push(`page:${error.message}`));
  page.on("requestfailed", (request) => {
    const failure = { url: request.url(), errorText: request.failure()?.errorText || "unknown" };
    const expectedRscAbort = failure.errorText === "net::ERR_ABORTED" && failure.url.startsWith(baseUrl) && failure.url.includes("_rsc=");
    if (!expectedRscAbort) telemetry.requestFailures.push(failure);
  });
  page.on("response", (response) => { if (response.status() >= 400) telemetry.httpFailures.push({ status: response.status(), url: response.url() }); });
  page.on("request", (request) => {
    const url = request.url().toLowerCase();
    if (["alphavantage", "finnhub", "query1.finance.yahoo", "query2.finance.yahoo", "coingecko", "binance"].some((host) => url.includes(host))) telemetry.providerRequests.push(request.url());
  });
  return telemetry;
}

function assertCleanTelemetry(telemetry, label) {
  assert(telemetry.errors.length === 0, `${label} emitted browser errors: ${telemetry.errors.join(" | ")}`);
  assert(telemetry.requestFailures.length === 0, `${label} emitted request failures: ${JSON.stringify(telemetry.requestFailures)}`);
  assert(telemetry.httpFailures.length === 0, `${label} emitted HTTP failures: ${JSON.stringify(telemetry.httpFailures)}`);
  assert(telemetry.providerRequests.length === 0, `${label} contacted market providers: ${telemetry.providerRequests.join(" | ")}`);
}

function assertControlledTelemetry(telemetry, label, expectedStatuses) {
  const unexpectedErrors = telemetry.errors.filter((message) => !expectedStatuses.some((status) => message.includes(`${status} (`)));
  assert(unexpectedErrors.length === 0, `${label} emitted browser errors: ${unexpectedErrors.join(" | ")}`);
  assert(telemetry.requestFailures.length === 0, `${label} emitted request failures: ${JSON.stringify(telemetry.requestFailures)}`);
  const unexpected = telemetry.httpFailures.filter((row) => !expectedStatuses.includes(row.status));
  assert(unexpected.length === 0, `${label} emitted unexpected HTTP failures: ${JSON.stringify(unexpected)}`);
  assert(telemetry.providerRequests.length === 0, `${label} contacted market providers: ${telemetry.providerRequests.join(" | ")}`);
}

function documentText(value) {
  return typeof value === "string" ? value : "";
}

async function screenshot(page, name, fullPage) {
  const file = path.join(outputDirectory, `${name}.png`);
  await page.screenshot({ path: file, fullPage });
  const metadata = await stat(file);
  assert(metadata.size > 10_000, `${name} screenshot is unexpectedly small`);
  return { file, bytes: metadata.size };
}

function jsonResponse(body, status = 200) {
  return { status, contentType: "application/json", body: JSON.stringify(body), headers: { "Cache-Control": "no-store" } };
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
