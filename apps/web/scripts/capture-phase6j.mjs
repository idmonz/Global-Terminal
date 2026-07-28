import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3062";
const apiBase = process.env.GT_API_BASE || "http://127.0.0.1:8062";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6j_visual");
const chromePath =
  process.env.CHROME_PATH ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  captures.anonymous = await captureAnonymous();
  captures.accountJourney = await captureAccountJourney();
  captures.mobile = await captureMobile();
  captures.offline = await captureOfflineLocalFallback();
  captures.security = await verifyProxySecurity();
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

async function captureAnonymous() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const errors = listenForErrors(page);
  try {
    await openWorkspace(page, 64);
    const state = await inspectAccount(page);
    assert(state.status === "local", `anonymous state was ${state.status}`);
    assert(state.identity.includes("Local workspace"), "anonymous identity was not explicit");
    assert(state.message.includes("never uploaded automatically"), "explicit local-only copy missing");
    assert(state.signInEnabled, "explicit local test identity should be enabled for QA");
    assert(!state.horizontalOverflow, "anonymous desktop has horizontal overflow");
    assertErrorsEmpty(errors, "anonymous");
    return {
      ...state,
      screenshot: await screenshot(page, "account-anonymous-desktop", false),
    };
  } finally {
    await context.close();
  }
}

async function captureAccountJourney() {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  const errors = listenForErrors(page);
  try {
    await openWorkspace(page, 64);
    await page.getByLabel("Process-local test identity").selectOption("analyst-a");
    await page.getByRole("button", { name: "Use local test identity" }).click();
    await waitForAnyStatus(page, ["signed-in-local-test", "saved-local-test"]);
    await page.locator("#analyst-split").fill("64");
    await page.getByRole("button", { name: "Save account layout" }).click();
    await waitForStatus(page, "saved-local-test");
    await page.waitForFunction(() =>
      document.querySelector(".account-sync-status small")?.textContent?.includes("Workspace preference saved"),
    );

    const accountA = await readSession(page);
    const aPreference = accountA.data?.workspace?.preference;
    assert(accountA.data?.identity?.display_name === "Analyst A", "account A identity mismatch");
    assert(aPreference?.value?.splitPercent === 64, "account A layout was not saved exactly");
    const savedShot = await screenshot(page, "account-a-saved", false);

    await openWorkspace(page, 48, { expectedStatus: "saved-local-test" });
    await page.getByRole("button", { name: "Restore saved" }).click();
    await page.waitForFunction(() => new URL(location.href).searchParams.get("split") === "64");
    const restoredState = await inspectAccount(page);

    const expectedErrorStart = errors.length;
    const advanced = await page.evaluate(async (version) => {
      const csrf = document.cookie
        .split(";")
        .map((row) => row.trim())
        .find((row) => row.startsWith("gt_csrf="))
        ?.split("=")
        .slice(1)
        .join("=") || "";
      const response = await fetch("/api/account/preferences/analyst-layout", {
        method: "PUT",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": decodeURIComponent(csrf),
        },
        body: JSON.stringify({
          expected_version: version,
          value: { preset: "research", splitPercent: 67, focusedPanel: "chart-core", visiblePanels: ["chart-core", "financials", "catalysts", "sources"] },
        }),
      });
      return { status: response.status, body: await response.json() };
    }, Number(aPreference.version));
    assert(advanced.status === 200, `concurrent account update failed: ${advanced.status}`);
    await page.getByRole("button", { name: "Save account layout" }).click();
    await waitForStatus(page, "conflict");
    const conflictState = await inspectAccount(page);
    assert(conflictState.message.includes("Conflict:"), "conflict recovery guidance missing");
    const conflictShot = await screenshot(page, "account-a-version-conflict", false);

    await page.getByRole("button", { name: "Sign out of local test workspace" }).click();
    await waitForStatus(page, "local");
    await page.getByLabel("Process-local test identity").selectOption("analyst-b");
    await page.getByRole("button", { name: "Use local test identity" }).click();
    await waitForStatus(page, "signed-in-local-test");
    const accountB = await readSession(page);
    assert(accountB.data?.identity?.display_name === "Analyst B", "account B identity mismatch");
    assert(accountB.data?.workspace?.preference == null, "account B could see account A preference");

    const rejectedTenant = await page.evaluate(async () => {
      const csrf = document.cookie
        .split(";")
        .map((row) => row.trim())
        .find((row) => row.startsWith("gt_csrf="))
        ?.split("=")
        .slice(1)
        .join("=") || "";
      const response = await fetch("/api/account/preferences/analyst-layout", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(csrf) },
        body: JSON.stringify({ tenant_id: "tnt_local_a_8c31e2", expected_version: 0, value: {} }),
      });
      return response.status;
    });
    assert(rejectedTenant === 422, `client-selected tenant was not rejected: ${rejectedTenant}`);
    const bShot = await screenshot(page, "account-b-isolated", false);
    const expectedHttpErrors = errors.splice(expectedErrorStart);
    assert(expectedHttpErrors.some((row) => row.includes("409")), "expected conflict response was not observed");
    assert(expectedHttpErrors.some((row) => row.includes("422")), "expected tenant rejection was not observed");
    assert(expectedHttpErrors.every((row) => row.includes("409") || row.includes("422")), `unexpected error during security probes: ${expectedHttpErrors.join(" | ")}`);
    assertErrorsEmpty(errors, "account-journey");
    return {
      accountA: { preferenceVersion: aPreference.version, splitPercent: aPreference.value.splitPercent },
      restored: restoredState,
      concurrentWriteStatus: advanced.status,
      conflict: conflictState,
      accountB: { preferenceVisible: false, rejectedTenantStatus: rejectedTenant },
      expectedHttpErrors,
      screenshots: { saved: savedShot, conflict: conflictShot, isolated: bShot },
    };
  } finally {
    await context.close();
  }
}

async function captureMobile() {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  const errors = listenForErrors(page);
  try {
    await openWorkspace(page, 58);
    const state = await inspectAccount(page);
    assert(state.status === "local", `mobile anonymous state was ${state.status}`);
    assert(!state.horizontalOverflow, "mobile account workspace has horizontal overflow");
    assert(state.barWidth <= 390, `mobile account bar width ${state.barWidth}`);
    assertErrorsEmpty(errors, "mobile");
    return {
      ...state,
      screenshot: await screenshot(page, "account-anonymous-mobile", true),
    };
  } finally {
    await context.close();
  }
}

async function captureOfflineLocalFallback() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript(() => {
    localStorage.setItem(
      "global-terminal.analyst-workspace.layout.v1",
      JSON.stringify({ preset: "news", splitPercent: 50, focusedPanel: "catalysts", visiblePanels: ["chart-core", "catalysts", "news", "sources"] }),
    );
  });
  const page = await context.newPage();
  await page.route("**/api/account/**", (route) => route.abort("failed"));
  try {
    await openWorkspace(page, 58, { expectedStatus: "offline" });
    const state = await inspectAccount(page);
    assert(state.status === "offline", `offline account state was ${state.status}`);
    assert(state.message.includes("Local workspace remains available"), "offline local recovery copy missing");
    assert(await page.locator('[data-phase6h-analyst-workspace="true"]').isVisible(), "offline account API hid local workspace");
    const savedLocal = await page.evaluate(() => localStorage.getItem("global-terminal.analyst-workspace.layout.v1"));
    assert(savedLocal?.includes('"preset":"news"'), "offline account API removed local layout");
    return {
      ...state,
      localLayoutRetained: true,
      screenshot: await screenshot(page, "account-api-offline-local-retained", false),
    };
  } finally {
    await context.close();
  }
}

async function verifyProxySecurity() {
  const externalOrigin = await fetch(`${baseUrl}/api/account/local-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Origin: "https://attacker.invalid" },
    body: JSON.stringify({ alias: "analyst-a", return_to: "/" }),
  });
  const unsafeRedirect = await fetch(`${baseUrl}/api/account/local-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Origin: baseUrl },
    body: JSON.stringify({ alias: "analyst-a", return_to: "https://attacker.invalid" }),
  });
  const traversal = await fetch(`${baseUrl}/api/account/%2e%2e/session`, {
    headers: { Accept: "application/json" },
    redirect: "manual",
  });
  assert(externalOrigin.status === 403, `external origin status ${externalOrigin.status}`);
  assert(unsafeRedirect.status === 422, `unsafe redirect status ${unsafeRedirect.status}`);
  assert([404, 400].includes(traversal.status), `path traversal status ${traversal.status}`);
  return {
    externalOriginStatus: externalOrigin.status,
    unsafeRedirectStatus: unsafeRedirect.status,
    traversalStatus: traversal.status,
  };
}

function workspaceUrl(split) {
  return `${baseUrl}/?view=analyst-workspace&mode=fixture&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&layout=research&panel=chart-core&split=${split}`;
}

async function openWorkspace(page, split, options = {}) {
  await page.goto(workspaceUrl(split), { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.locator('[data-phase6h-analyst-workspace="true"]').waitFor({ state: "visible", timeout: 120_000 });
  await page.locator('[data-phase6j-account-workspace="true"]').waitFor({ state: "visible", timeout: 30_000 });
  await waitForStatus(page, options.expectedStatus || "local");
  if ((options.expectedStatus || "local") === "local") {
    await page.locator(".account-signin-controls button:not([disabled])").waitFor({
      state: "visible",
      timeout: 30_000,
    });
  }
}

async function waitForStatus(page, expected) {
  await page.waitForFunction(
    (value) => document.querySelector('[data-phase6j-account-workspace="true"]')?.getAttribute("data-account-status") === value,
    expected,
    { timeout: 30_000 },
  );
}

async function waitForAnyStatus(page, expected) {
  await page.waitForFunction(
    (values) => values.includes(document.querySelector('[data-phase6j-account-workspace="true"]')?.getAttribute("data-account-status") || ""),
    expected,
    { timeout: 30_000 },
  );
}

async function inspectAccount(page) {
  return page.evaluate(() => {
    const bar = document.querySelector('[data-phase6j-account-workspace="true"]');
    const status = bar?.getAttribute("data-account-status") || "missing";
    const identity = bar?.querySelector(".account-workspace-identity")?.textContent?.trim() || "";
    const message = bar?.querySelector(".account-sync-status small")?.textContent?.trim() || "";
    const signIn = bar?.querySelector(".account-signin-controls button");
    return {
      status,
      identity,
      message,
      signInEnabled: signIn instanceof HTMLButtonElement ? !signIn.disabled : false,
      barWidth: Math.round(bar?.getBoundingClientRect().width || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
}

async function readSession(page) {
  return page.evaluate(async () => {
    const response = await fetch("/api/account/session", { cache: "no-store", credentials: "same-origin" });
    if (!response.ok) throw new Error(`session-http-${response.status}`);
    return response.json();
  });
}

async function screenshot(page, name, fullPage) {
  const file = path.join(outputDirectory, `${name}.png`);
  await page.screenshot({ path: file, fullPage });
  const bytes = (await stat(file)).size;
  assert(bytes > 15_000, `${name}: screenshot unexpectedly small (${bytes})`);
  return { file, bytes };
}

function listenForErrors(page) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console:${message.text()}`);
  });
  return errors;
}

function assertErrorsEmpty(errors, scenario) {
  assert(errors.length === 0, `${scenario}: browser errors: ${errors.join(" | ")}`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
