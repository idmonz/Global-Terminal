import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5q_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const consoleErrors = [];
const pageErrors = [];

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto(`${baseUrl}/?view=daily-brief&mode=fixture&period=morning&section=overview`, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await waitForBrief(page);
  const fixtureDesktop = await inspect(page);
  assert(fixtureDesktop.state === "fixture", `expected fixture state, got ${fixtureDesktop.state}`);
  assert(fixtureDesktop.claimCount >= 4, `expected claim ledger rows, got ${fixtureDesktop.claimCount}`);
  assert(fixtureDesktop.sourceCount >= 2, `expected source register rows, got ${fixtureDesktop.sourceCount}`);
  assert(fixtureDesktop.comparisonActive, "fixture prior comparison is not active");
  assert(!fixtureDesktop.horizontalOverflow, "desktop Daily Brief overflows horizontally");
  const fixtureDesktopPath = path.join(outputDirectory, "daily-brief-fixture-desktop.png");
  await page.screenshot({ path: fixtureDesktopPath, fullPage: false });

  await page.getByRole("button", { name: /Inspect evidence/i }).first().click();
  await page.waitForSelector('[data-source-drawer="open"]', { timeout: 30_000 });
  const drawer = await inspect(page);
  assert(drawer.drawerState === "open", "claim evidence drawer did not open");
  const drawerPath = path.join(outputDirectory, "daily-brief-source-drawer.png");
  await page.screenshot({ path: drawerPath, fullPage: false });

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.waitForTimeout(500);
  const tablet = await inspect(page);
  assert(!tablet.horizontalOverflow, "tablet Daily Brief overflows horizontally");
  const tabletPath = path.join(outputDirectory, "daily-brief-tablet.png");
  await page.screenshot({ path: tabletPath, fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  const mobile = await inspect(page);
  assert(mobile.mainWidth >= 340, `mobile brief width too small: ${mobile.mainWidth}`);
  assert(!mobile.horizontalOverflow, "mobile Daily Brief overflows horizontally");
  const mobilePath = path.join(outputDirectory, "daily-brief-mobile.png");
  await page.screenshot({ path: mobilePath, fullPage: true });

  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto(`${baseUrl}/?view=daily-brief&mode=cache&period=morning&section=overview`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await waitForBrief(page);
  const captureButton = page.getByRole("button", { name: /Capture brief/i });
  assert(await captureButton.isEnabled(), "capture button is disabled in cache mode despite local API");
  await captureButton.click();
  await page.waitForFunction(() => ["captured", "reviewed"].includes(document.querySelector('[data-daily-brief-state]')?.getAttribute("data-daily-brief-state") || ""), null, { timeout: 180_000 });
  const reviewButton = page.getByRole("button", { name: /Mark reviewed/i });
  if (await reviewButton.isEnabled()) {
    await reviewButton.click();
    await page.waitForSelector('[data-daily-brief-state="reviewed"]', { timeout: 60_000 });
  }
  const captured = await inspect(page);
  assert(["captured", "reviewed"].includes(captured.state), `local capture state did not persist: ${captured.state}`);
  const capturedPath = path.join(outputDirectory, "daily-brief-local-capture.png");
  await page.screenshot({ path: capturedPath, fullPage: false });

  for (const file of [fixtureDesktopPath, drawerPath, tabletPath, mobilePath, capturedPath]) {
    assert((await stat(file)).size > 18_000, `${path.basename(file)} is unexpectedly small`);
  }
  assert(consoleErrors.length === 0, `browser console errors: ${consoleErrors.join(" | ")}`);
  assert(pageErrors.length === 0, `page errors: ${pageErrors.join(" | ")}`);

  console.log(JSON.stringify({
    fixtureDesktop,
    drawer,
    tablet,
    mobile,
    captured,
    screenshotDirectory: outputDirectory,
    consoleErrorCount: consoleErrors.length,
    pageErrorCount: pageErrors.length,
  }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function waitForBrief(page) {
  await page.waitForSelector('[data-daily-brief-state]', { timeout: 120_000 });
  await page.waitForFunction(() => Number(document.querySelector('[data-daily-brief-state]')?.getAttribute("data-claim-count") || 0) > 0, null, { timeout: 120_000 });
}

async function inspect(page) {
  return page.locator('[data-daily-brief-state]').evaluate((root) => {
    const rect = root.getBoundingClientRect();
    return {
      state: root.getAttribute("data-daily-brief-state"),
      claimCount: Number(root.getAttribute("data-claim-count") || 0),
      sourceCount: Number(root.getAttribute("data-source-count") || 0),
      comparisonActive: root.getAttribute("data-comparison-active") === "true",
      drawerState: root.querySelector('[data-source-drawer]')?.getAttribute("data-source-drawer"),
      metricCount: root.querySelectorAll(".daily-metric").length,
      claimCards: root.querySelectorAll(".daily-claim-card").length,
      mainWidth: Math.round(rect.width),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
