import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5r_visual");
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

  await page.goto(`${baseUrl}/?view=daily-brief&mode=cache&period=morning&section=overview`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await waitForBriefDepth(page);
  const desktop = await inspect(page);
  assert(desktop.chartPanels >= 1, `expected chart panels, got ${desktop.chartPanels}`);
  assert(desktop.perspectiveCards >= 1, `expected research perspectives, got ${desktop.perspectiveCards}`);
  assert(desktop.miniBars >= 2, `expected mini chart bars, got ${desktop.miniBars}`);
  assert(!desktop.horizontalOverflow, "desktop Daily Brief depth view overflows horizontally");
  const desktopPath = path.join(outputDirectory, "daily-brief-depth-desktop.png");
  await page.screenshot({ path: desktopPath, fullPage: false });

  await page.getByRole("button", { name: /Inspect evidence/i }).first().click();
  await page.waitForSelector('[data-source-drawer="open"]', { timeout: 30_000 });
  const drawer = await inspect(page);
  assert(drawer.drawerState === "open", "claim evidence drawer did not open after depth panel render");
  const drawerPath = path.join(outputDirectory, "daily-brief-depth-source-drawer.png");
  await page.screenshot({ path: drawerPath, fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  const mobile = await inspect(page);
  assert(mobile.chartPanels >= 1, "mobile view lost chart panels");
  assert(mobile.perspectiveCards >= 1, "mobile view lost research perspectives");
  assert(!mobile.horizontalOverflow, "mobile Daily Brief depth view overflows horizontally");
  const mobilePath = path.join(outputDirectory, "daily-brief-depth-mobile.png");
  await page.screenshot({ path: mobilePath, fullPage: true });

  for (const file of [desktopPath, drawerPath, mobilePath]) {
    assert((await stat(file)).size > 20_000, `${path.basename(file)} is unexpectedly small`);
  }
  assert(consoleErrors.length === 0, `browser console errors: ${consoleErrors.join(" | ")}`);
  assert(pageErrors.length === 0, `page errors: ${pageErrors.join(" | ")}`);

  console.log(JSON.stringify({
    desktop,
    drawer,
    mobile,
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

async function waitForBriefDepth(page) {
  await page.waitForSelector('[data-daily-brief-state]', { timeout: 120_000 });
  await page.waitForFunction(() => Number(document.querySelector('[data-daily-brief-state]')?.getAttribute("data-claim-count") || 0) > 0, null, { timeout: 120_000 });
  await page.waitForSelector(".daily-chart-panel", { timeout: 120_000 });
  await page.waitForSelector(".daily-perspective-card", { timeout: 120_000 });
}

async function inspect(page) {
  return page.locator('[data-daily-brief-state]').evaluate((root) => {
    const rect = root.getBoundingClientRect();
    return {
      state: root.getAttribute("data-daily-brief-state"),
      claimCount: Number(root.getAttribute("data-claim-count") || 0),
      sourceCount: Number(root.getAttribute("data-source-count") || 0),
      chartPanels: root.querySelectorAll(".daily-chart-panel").length,
      perspectiveCards: root.querySelectorAll(".daily-perspective-card").length,
      miniBars: root.querySelectorAll(".daily-mini-bar").length,
      drawerState: root.querySelector('[data-source-drawer]')?.getAttribute("data-source-drawer"),
      mainWidth: Math.round(rect.width),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
