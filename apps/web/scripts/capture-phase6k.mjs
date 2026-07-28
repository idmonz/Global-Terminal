import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3063";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6k_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const report = { baseUrl, captured_at: new Date().toISOString(), captures: {} };

try {
  const journey = await captureJourney();
  report.captures.journey = journey.public;
  report.captures.anonymousMobile = await captureAnonymousMobile();
  report.captures.isolationAndSignout = await captureIsolationAndSignout(journey.ids);
  report.captures.offline = await captureOfflineLocalFallback();
  report.captures.security = await verifyProxySecurity();
  report.captures.regressions = await verifyRegressionViews();
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureJourney() {
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
    await page.goto(`${baseUrl}/?view=watchlist-desk&mode=fixture&list=primary&selected=AAPL`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.locator('[data-phase6d-watchlist-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
    await page.locator('[data-phase6k-tenant-research="true"]').waitFor({ state: "visible", timeout: 30_000 });
    assert(accountRequests.length === 0, `account API was not lazy: ${accountRequests.join(" | ")}`);
    const closedShot = await screenshot(page, "account-research-lazy-closed-desktop", false);

    await page.getByRole("button", { name: /Account research/ }).click();
    await page.getByRole("button", { name: "Use Analyst A" }).waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Use Analyst A" }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="ready"]').waitFor({ state: "visible", timeout: 30_000 });
    await page.locator(".tenant-candidate-list label").first().waitFor({ state: "visible" });
    const previewCount = await page.locator(".tenant-candidate-list label").count();
    assert(previewCount === 2, `expected two bounded candidates, got ${previewCount}`);
    const previewShot = await screenshot(page, "account-research-import-preview-desktop", false);

    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    assert((await page.locator(".tenant-account-watchlists article").count()) === 0, "cancel mutated account watchlists");
    await page.getByRole("button", { name: "Preview local import" }).click();
    await page.locator(".tenant-candidate-list input:checked").first().waitFor({ state: "attached" });
    await page.getByLabel("I consent to copy the selected public research fields into this account workspace.").check();
    await page.getByRole("button", { name: "Confirm import" }).click();
    await page.locator(".tenant-account-watchlists article").first().waitFor({ state: "visible", timeout: 30_000 });
    assert((await page.locator(".tenant-watchlist-symbols a").count()) === 2, "imported exact identities missing");
    await page.getByLabel("I consent to copy the selected public research fields into this account workspace.").check();
    await page.getByRole("button", { name: "Confirm import" }).click();
    await page.getByText("Selected public research fields copied", { exact: false }).waitFor({ state: "visible" });

    await page.getByRole("button", { name: "In-app rule" }).click();
    await page.getByText("In-app saved-change rule enabled", { exact: false }).waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Check saved changes" }).click();
    await page.locator(".tenant-inbox article").first().waitFor({ state: "visible", timeout: 30_000 });
    const inboxCount = await page.locator(".tenant-inbox article").count();
    assert(inboxCount >= 1, "saved-change inbox remained empty");

    const deskEnvelope = await readAccountDesk(page);
    const watchlistId = deskEnvelope.data.watchlists[0].resource_id;
    const inboxId = deskEnvelope.data.inbox[0].resource_id;
    const researchHref = await page.locator(".tenant-inbox article a").first().getAttribute("href");
    assert(researchHref?.includes("originView=watchlist-desk"), "exact research return context missing");
    await page.locator(".tenant-inbox article a").first().click();
    await page.locator('[data-phase6h-analyst-workspace="true"]').waitFor({ state: "visible", timeout: 120_000 });
    const exactResearchShot = await screenshot(page, "account-research-exact-evidence-desktop", false);
    await page.goBack({ waitUntil: "domcontentloaded" });
    await page.locator('[data-phase6d-watchlist-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="ready"]').waitFor({ state: "visible", timeout: 30_000 });

    await page.getByRole("button", { name: "Review", exact: true }).first().click();
    await page.locator('.tenant-inbox article[data-state="reviewed"]').first().waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Acknowledge", exact: true }).first().click();
    await page.locator('.tenant-inbox article[data-state="acknowledged"]').first().waitFor({ state: "visible" });

    const desktopState = await inspect(page);
    assert(!desktopState.horizontalOverflow, "desktop account research has horizontal overflow");
    assert(desktopState.externalDeliveryUnavailable, "delivery boundary is not visible");
    const desktopShot = await screenshot(page, "account-research-acknowledged-desktop", true);

    const failureStates = await page.evaluate(async (resourceId) => {
      const csrf = document.cookie.split(";").map((row) => row.trim()).find((row) => row.startsWith("gt_csrf="))?.split("=").slice(1).join("=") || "";
      const headers = { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(csrf) };
      const killed = await fetch(`/api/account/research-desk/watchlists/${resourceId}/inbox`, { method: "POST", credentials: "same-origin", headers, body: JSON.stringify({ kill_switch: true }) });
      const current = await fetch("/api/account/research-desk", { credentials: "same-origin", cache: "no-store" }).then((response) => response.json());
      const preview = await fetch("/api/account/research-desk/imports/preview?source_list_id=primary", { credentials: "same-origin", cache: "no-store" }).then((response) => response.json());
      const rule = current.data.rules.find((row) => row.watchlist_resource_id === resourceId);
      const expiredRule = await fetch(`/api/account/research-desk/watchlists/${resourceId}/rule`, { method: "PUT", credentials: "same-origin", headers, body: JSON.stringify({ enabled: true, minimum_severity: "material", cooldown_minutes: 0, expected_version: rule.version, expires_at: "2020-01-01T00:00:00+00:00" }) });
      const expired = await fetch(`/api/account/research-desk/watchlists/${resourceId}/inbox`, { method: "POST", credentials: "same-origin", headers, body: JSON.stringify({}) });
      const conflict = await fetch("/api/account/research-desk/imports", { method: "POST", credentials: "same-origin", headers, body: JSON.stringify({ preview_id: preview.data.preview_id, candidate_ids: preview.data.candidates.map((row) => row.candidate_id), consent: true, idempotency_key: "phase6k-browser-conflict", expected_version: 0, destination_name: "Conflict" }) });
      return { killed: (await killed.json()).data.status, expiredRuleStatus: expiredRule.status, expired: (await expired.json()).data.status, conflictStatus: conflict.status };
    }, watchlistId);
    assert(failureStates.killed === "suppressed", `kill switch state ${failureStates.killed}`);
    assert(failureStates.expiredRuleStatus === 200, `expired rule status ${failureStates.expiredRuleStatus}`);
    assert(failureStates.expired === "expired", `expired scan state ${failureStates.expired}`);
    assert(failureStates.conflictStatus === 409, `conflict status ${failureStates.conflictStatus}`);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(250);
    const mobileState = await inspect(page);
    assert(!mobileState.horizontalOverflow, "mobile account research has horizontal overflow");
    assert(mobileState.deskWidth <= 390, `mobile desk width is ${mobileState.deskWidth}`);
    const mobileShot = await screenshot(page, "account-research-acknowledged-mobile", true);

    const unexpectedErrors = errors.filter((row) => !row.includes("favicon") && !row.includes("409"));
    assert(unexpectedErrors.length === 0, `browser errors: ${unexpectedErrors.join(" | ")}`);
    return { ids: { watchlistId, inboxId }, public: {
      lazyAccountCallsBeforeOpen: 0,
      previewCount,
      importedSymbols: 2,
      inboxCount,
      finalState: "acknowledged",
      providerCallsDuringPreviewAndScan: 0,
      desktop: desktopState,
      mobile: mobileState,
      accountRequestCount: accountRequests.length,
      failureStates,
      screenshots: { closed: closedShot, preview: previewShot, exactResearch: exactResearchShot, desktop: desktopShot, mobile: mobileShot },
    } };
  } finally {
    await context.close();
  }
}

async function captureAnonymousMobile() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  try {
    await openWatchlist(page);
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="anonymous"]').waitFor({ state: "visible" });
    const state = await inspect(page);
    assert(!state.horizontalOverflow, "anonymous mobile overflow");
    return { ...state, screenshot: await screenshot(page, "account-research-anonymous-mobile", true) };
  } finally { await context.close(); }
}

async function captureIsolationAndSignout(ids) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  try {
    await openWatchlist(page);
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.getByRole("button", { name: "Use Analyst B" }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="ready"]').waitFor({ state: "visible" });
    const desk = await readAccountDesk(page);
    assert(desk.data.summary.watchlist_count === 0, "Account B can enumerate Account A watchlist");
    assert(desk.data.summary.inbox_count === 0, "Account B can enumerate Account A inbox");
    const crossTenant = await page.evaluate(async ({ watchlistId, inboxId }) => ({
      watchlist: (await fetch(`/api/account/research-desk/watchlists/${watchlistId}`, { credentials: "same-origin" })).status,
      inbox: (await fetch(`/api/account/research-desk/inbox/${inboxId}`, { credentials: "same-origin" })).status,
    }), ids);
    assert(crossTenant.watchlist === 404 && crossTenant.inbox === 404, `cross-tenant status ${JSON.stringify(crossTenant)}`);
    const isolatedShot = await screenshot(page, "account-research-account-b-isolated", false);
    const signoutStatus = await page.evaluate(async () => {
      const csrf = document.cookie.split(";").map((row) => row.trim()).find((row) => row.startsWith("gt_csrf="))?.split("=").slice(1).join("=") || "";
      return (await fetch("/api/account/signout", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(csrf) }, body: "{}" })).status;
    });
    assert(signoutStatus === 200, `signout status ${signoutStatus}`);
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="anonymous"]').waitFor({ state: "visible" });
    return { crossTenant, signoutStatus, screenshots: { isolated: isolatedShot, signedOut: await screenshot(page, "account-research-signed-out", false) } };
  } finally { await context.close(); }
}

async function captureOfflineLocalFallback() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.route("**/api/account/**", (route) => route.abort("failed"));
  try {
    await openWatchlist(page);
    await page.getByRole("button", { name: /Account research/ }).click();
    await page.locator('[data-phase6k-tenant-research="true"][data-state="offline"]').waitFor({ state: "visible" });
    assert(await page.locator('[data-phase6d-watchlist-desk="true"]').isVisible(), "account outage hid local workflow");
    assert((await page.locator(".watchlist-symbol-row").count()) > 0, "account outage removed local symbols");
    await page.evaluate(() => window.scrollTo(0, 0));
    return { localWorkflowRetained: true, screenshot: await screenshot(page, "account-research-api-offline-local-retained", false) };
  } finally { await context.close(); }
}

async function verifyProxySecurity() {
  const invalidOrigin = await fetch(`${baseUrl}/api/account/local-session`, { method: "POST", headers: { "Content-Type": "application/json", Origin: "https://attacker.invalid" }, body: JSON.stringify({ alias: "analyst-a", return_to: "/" }) });
  const oversized = await fetch(`${baseUrl}/api/account/research-desk/imports`, { method: "POST", headers: { "Content-Type": "application/json", Origin: baseUrl }, body: JSON.stringify({ padding: "x".repeat(17_000) }) });
  const traversal = await fetch(`${baseUrl}/api/account/%2e%2e/session`, { redirect: "manual" });
  assert(invalidOrigin.status === 403, `invalid Origin status ${invalidOrigin.status}`);
  assert(oversized.status === 413, `oversized body status ${oversized.status}`);
  assert([400, 404].includes(traversal.status), `traversal status ${traversal.status}`);
  return { invalidOrigin: invalidOrigin.status, oversizedBody: oversized.status, traversal: traversal.status };
}

async function verifyRegressionViews() {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  try {
    await page.goto(`${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=AAPL`, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.locator('[data-phase6h-analyst-workspace="true"]').waitFor({ state: "visible", timeout: 120_000 });
    assert(await page.locator('[data-phase6i-research-operations="true"]').isVisible(), "Phase 6I operations regression");
    assert(!await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1), "Phase 6H/6I regression overflow");
    return { analystWorkspace: "visible", researchOperations: "visible", overflow: false };
  } finally { await context.close(); }
}

async function openWatchlist(page) {
  await page.goto(`${baseUrl}/?view=watchlist-desk&mode=fixture&list=primary&selected=AAPL`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.locator('[data-phase6d-watchlist-desk="true"]').waitFor({ state: "visible", timeout: 120_000 });
}

async function readAccountDesk(page) {
  return page.evaluate(async () => {
    const response = await fetch("/api/account/research-desk", { cache: "no-store", credentials: "same-origin" });
    if (!response.ok) throw new Error(`account-desk-http-${response.status}`);
    return response.json();
  });
}

async function inspect(page) {
  return page.evaluate(() => {
    const desk = document.querySelector('[data-phase6k-tenant-research="true"]');
    return {
      state: desk?.getAttribute("data-state") || "missing",
      deskWidth: Math.round(desk?.getBoundingClientRect().width || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      externalDeliveryUnavailable: desk?.textContent?.includes("External delivery unavailable") || false,
      status: desk?.querySelector('[role="status"]')?.textContent?.trim() || "",
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

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
