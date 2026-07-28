import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3267";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6p_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const watchlistFixture = JSON.parse(await readFile(path.join(repoRoot, "static", "api-fixtures", "watchlist-desk.json"), "utf8"));

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const report = {
  evidence_version: "phase6p.visual.v1",
  product_phase: "Phase 6P",
  base_url: baseUrl,
  captured_at: new Date().toISOString(),
  captures: {},
};

try {
  report.captures.anonymous = await captureAnonymous();
  report.captures.restored = await captureHosted("hosted-ready", "account-continuity-restored-desktop");
  report.captures.conflict = await captureHosted("conflict", "account-continuity-conflict-desktop");
  report.captures.offline = await captureHosted("offline-read-only", "account-continuity-offline-desktop");
  report.captures.mobile = await captureMobile();
  report.passed = true;
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureAnonymous() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installAccountFixture(page, { authenticated: false, continuityState: "local-only" });
  try {
    await openAccountResearch(page);
    const form = page.locator(".tenant-hosted-signin");
    await form.waitFor({ state: "visible" });
    const focus = await inspectFocus(page, page.getByRole("button", { name: "Sign in", exact: true }));
    const evidence = await inspect(page);
    assert(evidence.hostedFormVisible, "Hosted sign-in form is not visible");
    assert(evidence.productNavWidth >= 160, `Watchlist product navigation is crushed at ${evidence.productNavWidth}px`);
    assert(!evidence.horizontalOverflow, "Anonymous account journey overflows horizontally");
    assert(evidence.unlabeledControls === 0, `${evidence.unlabeledControls} account controls lack labels`);
    assert(focus.visible, `Hosted sign-in lacks visible keyboard focus: ${JSON.stringify(focus)}`);
    assertCleanTelemetry(telemetry, "anonymous account journey");
    return {
      ...evidence,
      focus,
      screenshot: await screenshot(page, "account-hosted-signin-desktop", true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function captureHosted(continuityState, filename) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installAccountFixture(page, { authenticated: true, continuityState });
  try {
    await openAccountResearch(page);
    await page.locator(`[data-phase6p-continuity="${continuityState}"]`).waitFor({ state: "visible" });
    const evidence = await inspect(page);
    assert(evidence.continuityState === continuityState, `Expected ${continuityState}, saw ${evidence.continuityState}`);
    assert(!evidence.horizontalOverflow, `${continuityState} account journey overflows horizontally`);
    assert(evidence.productNavWidth >= 160, `Watchlist product navigation is crushed at ${evidence.productNavWidth}px`);
    assert(evidence.unlabeledControls === 0, `${continuityState} has ${evidence.unlabeledControls} unlabeled controls`);
    assert(evidence.liveRegionCount >= 1, `${continuityState} has no aria-live status region`);
    if (continuityState === "conflict") assert(evidence.conflictActions === 2, "Conflict choices are incomplete");
    assertCleanTelemetry(telemetry, `${continuityState} account journey`);
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

async function captureMobile() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const telemetry = observe(page);
  await installAccountFixture(page, { authenticated: true, continuityState: "hosted-ready" });
  try {
    await openAccountResearch(page);
    await page.locator('[data-phase6p-continuity="hosted-ready"]').waitFor({ state: "visible" });
    const evidence = await inspect(page);
    assert(!evidence.horizontalOverflow, "390px hosted account journey overflows horizontally");
    assert(evidence.rootWidth <= 390, `390px account root is ${evidence.rootWidth}px wide`);
    assert(evidence.continuityWidth <= 390, `390px continuity console is ${evidence.continuityWidth}px wide`);
    assert(evidence.unlabeledControls === 0, `390px hosted journey has ${evidence.unlabeledControls} unlabeled controls`);
    assertCleanTelemetry(telemetry, "mobile hosted account journey");
    return {
      ...evidence,
      screenshot: await screenshot(page, "account-continuity-restored-mobile", false),
      tallScreenshot: await screenshot(page, "account-continuity-restored-mobile-tall", true),
      providerRequestCount: telemetry.providerRequests.length,
      errors: telemetry.errors,
    };
  } finally {
    await context.close();
  }
}

async function openAccountResearch(page) {
  await page.goto(`${baseUrl}/?view=watchlist-desk&mode=fixture`, { waitUntil: "networkidle" });
  await page.locator('[data-phase6k-tenant-research="true"]').waitFor({ state: "visible" });
  await page.locator(".tenant-research-launcher").click();
  await page.locator(".tenant-research-body").waitFor({ state: "visible" });
  await page.evaluate(() => document.fonts.ready);
}

async function installAccountFixture(page, { authenticated, continuityState }) {
  await page.route("**/api/account/**", async (route) => {
    const url = new URL(route.request().url());
    const accountPath = url.pathname.replace(/^\/api\/account\/?/, "");
    if (accountPath === "session") {
      await route.fulfill(jsonResponse(accountEnvelope(authenticated, continuityState)));
      return;
    }
    if (!authenticated) {
      await route.fulfill(jsonResponse({ detail: "Authenticated session required." }, 401));
      return;
    }
    if (accountPath === "research-desk") {
      await route.fulfill(jsonResponse(researchDeskEnvelope()));
      return;
    }
    if (accountPath === "continuity") {
      await route.fulfill(jsonResponse(continuityEnvelope(continuityState)));
      return;
    }
    if (accountPath.startsWith("research-desk/imports/preview")) {
      await route.fulfill(jsonResponse(importPreviewEnvelope()));
      return;
    }
    await route.fulfill(jsonResponse({ detail: "Controlled Phase 6P visual route." }, 404));
  });
}

function accountEnvelope(authenticated, continuityState) {
  return envelope("account_workspace", {
    identity: {
      state: authenticated ? "authenticated-hosted" : "anonymous-local",
      authenticated,
      identity_provider: authenticated ? "supabase" : "none",
      display_name: authenticated ? "Hosted research account" : null,
      role: authenticated ? "owner" : null,
      plan: authenticated ? "free" : "local-free",
      account_scope: authenticated ? "server-derived" : "local",
    },
    workspace: { tenant_scope: authenticated ? "server-derived" : "local", local_fallback_available: true },
    persistence: {
      provider: "supabase",
      state: authenticated ? continuityState : "local",
      source_status: authenticated ? (continuityState === "hosted-ready" ? "hosted-ready" : "unavailable") : "configured-unverified",
      hosted_verified: authenticated && continuityState === "hosted-ready",
    },
    runtime_truth: {
      local_test_sign_in_available: true,
      hosted_sign_in_available: true,
      hosted_auth: authenticated,
      account_write: authenticated,
    },
    summary: { provider_calls: 0, authenticated },
  });
}

function researchDeskEnvelope() {
  const rows = Array.isArray(watchlistFixture?.data?.lists) ? watchlistFixture.data.lists : [];
  const sourceRows = rows.length ? rows : [{ list_id: "primary", name: "Daily Radar", item_count: 2 }];
  return envelope("tenant_research_desk", {
    summary: { watchlist_count: 1, inbox_count: 1, unread_count: 1, provider_call_count: 0 },
    watchlists: [{
      resource_id: "twl_phase6p_visual",
      name: String(sourceRows[0]?.name || "Daily Radar"),
      item_count: 2,
      version: 3,
      items: [
        { resource_id: "twi_aapl", symbol: "AAPL", source_status: "cached", observed_at: "2026-07-15T08:00:00Z", research_href: "/?view=analyst-workspace&symbol=AAPL" },
        { resource_id: "twi_btc", symbol: "BTC-USD", source_status: "fresh", observed_at: "2026-07-15T08:02:00Z", research_href: "/?view=analyst-workspace&symbol=BTC-USD" },
      ],
    }],
    rules: [],
    inbox: [{ resource_id: "tri_phase6p", severity: "material", state: "new", title: "AAPL material move", summary: "Saved observation changed beyond the account threshold.", source_status: "cached", observed_at: "2026-07-15T08:04:00Z", research_href: "/?view=analyst-workspace&symbol=AAPL" }],
    attention: { attention_count: 1, degraded_source_count: 0, items: [] },
    sync: { state: "local-only", pending_count: 0, conflict_count: 0, queue: [] },
  });
}

function continuityEnvelope(state) {
  return envelope("account_continuity_status", {
    account_continuity_version: "account_continuity.v1",
    state,
    enabled: true,
    remote_version: state === "conflict" ? 7 : 6,
    pending_count: state === "offline-read-only" ? 2 : 0,
    conflict_count: state === "conflict" ? 1 : 0,
    last_restore_at: "2026-07-15T08:00:00Z",
    last_sync_at: "2026-07-15T08:05:00Z",
    last_recovery_at: state === "hosted-ready" ? "2026-07-15T08:06:00Z" : null,
    repository: {
      provider: "supabase",
      source_status: state === "hosted-ready" ? "hosted-ready" : "unavailable",
      hosted_verified: state === "hosted-ready",
    },
    provider_call_count: 0,
  });
}

function importPreviewEnvelope() {
  return envelope("tenant_research_import_preview", {
    preview_id: "phase6p_visual_preview",
    source_name: "Daily Radar",
    candidate_count: 2,
    provider_call_count: 0,
    candidates: [
      { candidate_id: "candidate_aapl", symbol: "AAPL", display_name: "Apple", evidence: { source_status: "cached", provider: "saved observation", observed_at: "2026-07-15T08:00:00Z" } },
      { candidate_id: "candidate_btc", symbol: "BTC-USD", display_name: "Bitcoin", evidence: { source_status: "fresh", provider: "saved observation", observed_at: "2026-07-15T08:02:00Z" } },
    ],
  });
}

function envelope(payloadType, data) {
  return { contract_version: "phase_2b.v1", payload_type: payloadType, generated_at: "2026-07-15T08:10:00Z", data, summary: { provider_call_count: 0 } };
}

function jsonResponse(body, status = 200) {
  return { status, contentType: "application/json", body: JSON.stringify(body), headers: { "Cache-Control": "no-store" } };
}

function observe(page) {
  const telemetry = { errors: [], requestFailures: [], cancelledPrefetches: [], httpFailures: [], providerRequests: [] };
  page.on("console", (message) => { if (message.type() === "error") telemetry.errors.push(`console:${message.text()}`); });
  page.on("pageerror", (error) => telemetry.errors.push(`page:${error.message}`));
  page.on("requestfailed", (request) => {
    const failure = { url: request.url(), error: request.failure()?.errorText || "unknown" };
    const isCancelledRsc = failure.error === "net::ERR_ABORTED"
      && failure.url.startsWith(baseUrl)
      && failure.url.includes("_rsc=");
    if (isCancelledRsc) telemetry.cancelledPrefetches.push(failure);
    else telemetry.requestFailures.push(failure);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) telemetry.httpFailures.push({ status: response.status(), url: response.url() });
  });
  page.on("request", (request) => {
    const url = request.url();
    if (/alphavantage|finnhub|supabase\.co|finance\.yahoo|coingecko|binance/i.test(url)) telemetry.providerRequests.push(url);
  });
  return telemetry;
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.querySelector('[data-phase6k-tenant-research="true"]');
    const nav = document.querySelector(".watchlist-desk-workspace-grid > .product-nav");
    const continuity = document.querySelector("[data-phase6p-continuity]");
    const controls = Array.from(document.querySelectorAll("button,select,input,a[href]"));
    const unlabeledControls = controls.filter((node) => {
      const labels = "labels" in node && node.labels ? Array.from(node.labels).map((item) => item.textContent?.trim()).filter(Boolean).join(" ") : "";
      return !(node.getAttribute("aria-label") || node.getAttribute("title") || node.textContent?.trim() || labels);
    }).length;
    return {
      hostedFormVisible: Boolean(document.querySelector(".tenant-hosted-signin")),
      continuityState: continuity?.getAttribute("data-phase6p-continuity") || null,
      conflictActions: document.querySelectorAll(".account-continuity-conflict button").length,
      productNavWidth: Math.round(nav?.getBoundingClientRect().width || 0),
      rootWidth: Math.round(root?.getBoundingClientRect().width || 0),
      continuityWidth: Math.round(continuity?.getBoundingClientRect().width || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      unlabeledControls,
      liveRegionCount: document.querySelectorAll('[aria-live="polite"], [aria-live="assertive"]').length,
    };
  });
}

async function inspectFocus(page, locator) {
  await page.evaluate(() => { if (document.activeElement instanceof HTMLElement) document.activeElement.blur(); });
  const count = await page.locator('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])').count();
  for (let tabs = 1; tabs <= Math.min(count + 2, 220); tabs += 1) {
    await page.keyboard.press("Tab");
    const state = await locator.evaluate((node, tabCount) => {
      const style = getComputedStyle(node);
      const reached = document.activeElement === node;
      return { reached, visible: reached && style.outlineStyle !== "none" && Number.parseFloat(style.outlineWidth) >= 2, outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth, tabs: tabCount };
    }, tabs);
    if (state.reached) return state;
  }
  return { reached: false, visible: false, tabs: count + 2 };
}

async function screenshot(page, name, fullPage) {
  const file = path.join(outputDirectory, `${name}.png`);
  await page.evaluate(async () => {
    window.scrollTo(0, 0);
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.screenshot({ path: file, fullPage, animations: "disabled", caret: "hide" });
  const bytes = (await stat(file)).size;
  assert(bytes > 12_000, `${name} screenshot is unexpectedly small (${bytes})`);
  return { file, bytes };
}

function assertCleanTelemetry(telemetry, label) {
  assert(telemetry.errors.length === 0, `${label} emitted browser errors: ${telemetry.errors.join(" | ")}`);
  assert(telemetry.requestFailures.length === 0, `${label} emitted request failures: ${JSON.stringify(telemetry.requestFailures)}`);
  assert(telemetry.httpFailures.length === 0, `${label} emitted HTTP failures: ${JSON.stringify(telemetry.httpFailures)}`);
  assert(telemetry.providerRequests.length === 0, `${label} contacted a provider directly`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
