import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3061";
const apiBase = process.env.GT_API_BASE || "http://127.0.0.1:8061";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6i_visual");
const chromePath =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  const operations = await loadOperationsEvidence();
  captures.desktop = await captureLiveDesktop(operations);
  captures.mobile = await captureMobile(operations);
  captures.lifecycle = await captureLifecycle();
  captures.rateLimited = await captureInjectedState(operations, {
    name: "rate-limited",
    status: "rate-limited",
    retryReason: "provider-rate-limit",
    nextRetryAt: new Date(Date.now() + 60_000).toISOString(),
  });
  captures.overlap = await captureInjectedState(operations, {
    name: "overlap",
    status: "overlap",
    retryReason: "same-symbol-active",
  });
  captures.stale = await captureInjectedState(operations, {
    name: "stale-lkg",
    status: "partial",
    retryReason: "provider-recovery-window",
    stale: true,
  });
  captures.offlineRecovery = await captureOfflineRecovery(operations);
  captures.unknown = await captureUnknown();
  const report = {
    baseUrl,
    apiBase,
    captured_at: new Date().toISOString(),
    captures,
  };
  await writeFile(
    path.join(outputDirectory, "summary.json"),
    JSON.stringify(report, null, 2),
    "utf8",
  );
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function loadOperationsEvidence() {
  const url =
    `${apiBase}/api/analyst-workspace/AAPL/operations` +
    "?asset_class=equity&interval=1d&range=3mo" +
    "&panels=chart-core,financials,catalysts,sources";
  const response = await fetch(url);
  assert(response.ok, `operations evidence unavailable: ${response.status}`);
  return response.json();
}

async function captureLiveDesktop(operations) {
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 1,
  });
  const errors = listenForErrors(page);
  try {
    await page.goto(workspaceUrl(), {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await waitForWorkspace(page);
    await waitForDesktopPanels(page);
    await page.waitForFunction(
      () =>
        document
          .querySelector('[data-panel="chart-core"]')
          ?.textContent?.toLowerCase()
          .includes("yfinance"),
      { timeout: 120_000 },
    );
    await page.waitForTimeout(1_000);
    const state = await observeOperations(page);
    assert(state.observedProviders > 0, "desktop: no observed providers");
    assert(state.budget.includes("/ 8 calls"), "desktop: bounded budget missing");
    assert(!state.horizontalOverflow, "desktop: horizontal overflow");
    const accessibility = await assertAccessible(page, "desktop");
    assertErrorsEmpty(errors, "desktop");
    return {
      ...state,
      payloadStatus: operations.data?.readiness?.status,
      payloadBytes: Buffer.byteLength(JSON.stringify(operations)),
      accessibility,
      screenshot: await screenshot(page, "research-operations-desktop-live", false),
    };
  } finally {
    await page.close();
  }
}

async function captureMobile(operations) {
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
  });
  const errors = listenForErrors(page);
  try {
    await page.goto(workspaceUrl(), {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await waitForWorkspace(page);
    const state = await observeOperations(page);
    assert(state.stripWidth <= 390, `mobile: strip width ${state.stripWidth}`);
    assert(!state.horizontalOverflow, "mobile: horizontal overflow");
    assertErrorsEmpty(errors, "mobile");
    return {
      ...state,
      payloadStatus: operations.data?.readiness?.status,
      screenshot: await screenshot(page, "research-operations-mobile", true),
    };
  } finally {
    await page.close();
  }
}

async function captureLifecycle() {
  const page = await browser.newPage({
    viewport: { width: 1500, height: 950 },
    deviceScaleFactor: 1,
  });
  const errors = listenForErrors(page);
  let pollCount = 0;
  const jobId = "research_refresh_0123456789ab";
  const queued = jobEnvelope(jobId, "queued", 0);
  const running = jobEnvelope(jobId, "running", 50);
  const partial = jobEnvelope(jobId, "partial", 100, {
    actual_calls: 6,
    cache_hits: 2,
    stale_hits: 2,
    failed_calls: 2,
    retained_lkg: true,
    retry_reason: "provider-recovery-window",
    next_retry_at: new Date(Date.now() + 60_000).toISOString(),
  });
  await page.route("**/api/runtime/api/analyst-workspace/AAPL/refresh", (route) =>
    route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify(queued) }),
  );
  await page.route(`**/api/runtime/api/research-operations/jobs/${jobId}`, (route) => {
    pollCount += 1;
    const payload = pollCount < 2 ? running : partial;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    });
  });
  try {
    await page.goto(workspaceUrl(), {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await waitForWorkspace(page);
    await waitForDesktopPanels(page);
    await page.getByRole("button", { name: /Refresh exact workspace/ }).click();
    await page.waitForFunction(
      () => document.querySelector(".analyst-operation-status")?.textContent?.includes("50%"),
      { timeout: 20_000 },
    );
    const runningShot = await screenshot(page, "research-operations-running", false);
    await page.waitForFunction(
      () => document.querySelector(".analyst-operation-status")?.textContent?.includes("partial"),
      { timeout: 20_000 },
    );
    const state = await observeOperations(page);
    assert(state.status === "partial", `lifecycle: terminal state ${state.status}`);
    assert(state.nextSafeRetry !== "Never", "lifecycle: next retry missing");
    assertErrorsEmpty(errors, "lifecycle");
    return {
      pollCount,
      terminal: state,
      runningScreenshot: runningShot,
      partialScreenshot: await screenshot(
        page,
        "research-operations-partial-lkg",
        false,
      ),
    };
  } finally {
    await page.close();
  }
}

async function captureInjectedState(operations, options) {
  const page = await browser.newPage({
    viewport: { width: 1400, height: 900 },
    deviceScaleFactor: 1,
  });
  const errors = listenForErrors(page);
  const injected = structuredClone(operations);
  injected.data.readiness.status = options.status;
  injected.data.queue.status = options.status;
  injected.data.last_attempt = {
    ...(injected.data.last_attempt || {}),
    status: options.status,
    retry_reason: options.retryReason,
    next_retry_at: options.nextRetryAt || null,
    retained_lkg: Boolean(options.stale),
  };
  if (options.stale) {
    injected.data.panels = (injected.data.panels || []).map((panel) => ({
      ...panel,
      source_status: "stale",
      freshness: "stale",
      last_known_good: true,
    }));
  }
  await page.route("**/api/runtime/api/analyst-workspace/AAPL/operations*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(injected),
    }),
  );
  try {
    await page.goto(workspaceUrl(), {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await waitForWorkspace(page);
    await waitForDesktopPanels(page);
    await page.waitForFunction(
      (expected) =>
        document.querySelector(".analyst-operation-status")?.textContent?.includes(expected),
      options.status,
    );
    const state = await observeOperations(page);
    assert(state.status === options.status, `${options.name}: status mismatch`);
    assertErrorsEmpty(errors, options.name);
    return {
      ...state,
      screenshot: await screenshot(page, `research-operations-${options.name}`, false),
    };
  } finally {
    await page.close();
  }
}

async function captureOfflineRecovery(operations) {
  const page = await browser.newPage({
    viewport: { width: 1400, height: 900 },
    deviceScaleFactor: 1,
  });
  const errors = listenForErrors(page);
  const pattern = "**/api/runtime/api/analyst-workspace/AAPL/operations*";
  await page.route(pattern, (route) => route.abort("failed"));
  try {
    await page.goto(workspaceUrl(), {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-phase6i-research-operations="true"]');
    await page.waitForFunction(() => {
      const text =
        document.querySelector(".analyst-operation-status")?.textContent || "";
      return (
        !text.toLowerCase().includes("loading") &&
        (text.includes("operations-") || text.includes("Failed to fetch"))
      );
    });
    await waitForDesktopPanels(page);
    await page.waitForTimeout(1_000);
    const offline = await screenshot(page, "research-operations-api-offline", false);
    await page.unroute(pattern);
    await page.route(pattern, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(operations),
      }),
    );
    await page.reload({ waitUntil: "domcontentloaded", timeout: 180_000 });
    await waitForWorkspace(page);
    await waitForDesktopPanels(page);
    await page.waitForTimeout(500);
    const recovered = await observeOperations(page);
    assert(recovered.observedProviders > 0, "recovery: observed providers missing");
    errors.console = errors.console.filter(
      (entry) =>
        !entry.includes("ERR_FAILED") &&
        !entry.includes("Failed to load resource"),
    );
    assertErrorsEmpty(errors, "offline-recovery");
    return {
      recovered,
      offlineScreenshot: offline,
      recoveryScreenshot: await screenshot(
        page,
        "research-operations-api-recovered",
        false,
      ),
    };
  } finally {
    await page.close();
  }
}

async function captureUnknown() {
  const page = await browser.newPage({
    viewport: { width: 1200, height: 800 },
    deviceScaleFactor: 1,
  });
  const errors = listenForErrors(page);
  try {
    await page.goto(
      `${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=NOTAREAL123&assetClass=equity`,
      { waitUntil: "domcontentloaded", timeout: 180_000 },
    );
    await page.waitForSelector(".unknown-symbol-state", { timeout: 120_000 });
    const body = await page.locator("body").innerText();
    assert(body.includes("NOTAREAL123"), "unknown: requested symbol missing");
    assert(!body.includes("Apple Inc."), "unknown: another identity leaked");
    assertErrorsEmpty(errors, "unknown");
    return { screenshot: await screenshot(page, "research-operations-unknown", false) };
  } finally {
    await page.close();
  }
}

function jobEnvelope(jobId, status, percent, overrides = {}) {
  return {
    contract_version: "phase_2b.v1",
    payload_type: "research_refresh_job",
    generated_at: new Date().toISOString(),
    data: {
      job_id: jobId,
      request_id: "phase6i-visual",
      symbol: "AAPL",
      asset_class: "equity",
      interval: "1d",
      range: "3mo",
      panels: ["chart-core", "financials", "catalysts", "sources"],
      status,
      planned_calls: 8,
      actual_calls: 0,
      progress: {
        current: Math.round((percent / 100) * 4),
        total: 4,
        percent,
      },
      ...overrides,
    },
    summary: { status },
    source_status: [],
    unavailable: [],
    errors: [],
    caveats: [],
  };
}

function workspaceUrl() {
  return (
    `${baseUrl}/?view=analyst-workspace&mode=cache&symbol=AAPL` +
    "&assetClass=equity&interval=1d&range=3mo&layout=research&panel=chart-core"
  );
}

async function waitForWorkspace(page) {
  await page.waitForSelector('[data-phase6h-analyst-workspace="true"]', {
    timeout: 120_000,
  });
  await page.waitForSelector('[data-phase6i-research-operations="true"]', {
    timeout: 120_000,
  });
  await page.waitForFunction(
    () =>
      !document
        .querySelector(".analyst-operation-status")
        ?.textContent?.includes("loading"),
    { timeout: 120_000 },
  );
  await page.waitForTimeout(300);
}

async function waitForDesktopPanels(page) {
  await page.waitForFunction(
    () => {
      const panels = [
        ...document.querySelectorAll(".analyst-desktop-grid .analyst-panel"),
      ];
      return (
        panels.length === 4 &&
        panels.every((panel) =>
          ["ready", "last-known-good"].includes(
            panel.getAttribute("data-panel-status") || "",
          ),
        )
      );
    },
    { timeout: 120_000 },
  );
}

async function observeOperations(page) {
  return page.evaluate(() => {
    const strip = document.querySelector("[data-phase6i-research-operations]");
    const summary = strip?.querySelector(".analyst-operations-summary strong")?.textContent || "";
    const metrics = [...(strip?.querySelectorAll("dd") || [])].map(
      (node) => node.textContent?.trim() || "",
    );
    const bounds = strip?.getBoundingClientRect();
    return {
      observedProviders: Number(summary.split(" ")[0] || 0),
      status:
        strip?.querySelector(".analyst-operation-status > span")?.textContent?.trim() ||
        "",
      budget: metrics[1] || "",
      lastSuccess: metrics[2] || "",
      nextSafeRetry: metrics[3] || "",
      stripWidth: Math.round(bounds?.width || 0),
      horizontalOverflow:
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth + 1,
    };
  });
}

async function assertAccessible(page, label) {
  const audit = await page.evaluate(() => {
    const ids = [...document.querySelectorAll("[id]")]
      .map((element) => element.id)
      .filter(Boolean);
    const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
    const controls = [...document.querySelectorAll("button, a[href], input, select")];
    const unlabeled = controls
      .filter((element) => {
        const explicit = element.id
          ? document
              .querySelector(`label[for="${CSS.escape(element.id)}"]`)
              ?.textContent?.trim()
          : "";
        return !(
          element.getAttribute("aria-label")?.trim() ||
          element.getAttribute("title")?.trim() ||
          element.textContent?.trim() ||
          explicit ||
          element.closest("label")?.textContent?.trim()
        );
      })
      .map((element) => element.outerHTML.slice(0, 160));
    return {
      duplicateIds: [...new Set(duplicateIds)],
      unlabeled,
      controlCount: controls.length,
    };
  });
  assert(!audit.duplicateIds.length, `${label}: duplicate IDs`);
  assert(!audit.unlabeled.length, `${label}: unlabeled controls`);
  const target = page.getByRole("button", { name: /Refresh exact workspace/ });
  await target.focus();
  const focus = await target.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      outline: style.outlineStyle,
      width: style.outlineWidth,
      shadow: style.boxShadow,
    };
  });
  assert(
    (focus.outline !== "none" && focus.width !== "0px") ||
      focus.shadow !== "none",
    `${label}: focus indicator missing`,
  );
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
  assert(
    !errors.console.length,
    `${label}: console errors ${errors.console.join(" | ")}`,
  );
  assert(!errors.page.length, `${label}: page errors ${errors.page.join(" | ")}`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
