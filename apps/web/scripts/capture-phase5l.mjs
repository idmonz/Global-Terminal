import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5l_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const consoleErrors = [];
const files = {};

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });

  const demoUrl = baseUrl + "/?view=research-memory&collection=demo-research&surface=inbox&mode=demo";
  await page.goto(demoUrl, { waitUntil: "networkidle", timeout: 120_000 });
  await page.waitForSelector('[data-product-view="research-memory-workstation"]', { timeout: 60_000 });
  const desktop = await inspect(page);
  assert(desktop.items === 4, "demo inbox item count is wrong");
  assert(desktop.metrics === 4, "summary metric strip is incomplete");
  assert(desktop.actions >= 4, "action rail is incomplete");
  assert(desktop.scrollWidth <= 1600, "desktop overflows viewport");
  files.desktopInbox = path.join(outputDirectory, "research-memory-demo-inbox-desktop.png");
  await page.screenshot({ path: files.desktopInbox, fullPage: false });

  await page.getByRole("link", { name: /Sources/ }).click();
  await page.waitForURL((url) => url.searchParams.get("surface") === "sources");
  await page.waitForSelector(".memory-table-wrap tbody tr");
  const sources = await inspect(page);
  assert(sources.tableRows === 2, "source history is incomplete");
  files.desktopSources = path.join(outputDirectory, "research-memory-demo-sources-desktop.png");
  await page.screenshot({ path: files.desktopSources, fullPage: false });

  await page.getByRole("link", { name: /Inbox/ }).click();
  await page.getByLabel("Title").fill("Fictional session observation");
  await page.getByLabel("Symbol", { exact: true }).fill("MSFT");
  await page.getByLabel("Private note").fill("Fictional session-only body for visual interaction verification.");
  await page.getByRole("button", { name: "Add demo note" }).click();
  await page.waitForFunction(() => document.querySelectorAll(".memory-item").length === 5);
  assert(!page.url().includes("Fictional") && !page.url().includes("MSFT"), "private form text leaked into URL");
  files.desktopInteraction = path.join(outputDirectory, "research-memory-demo-interaction-desktop.png");
  await page.screenshot({ path: files.desktopInteraction, fullPage: false });

  await page.goto(baseUrl + "/?view=asset&symbol=AAPL&assetClass=equity&timeframe=1D&surface=overview&mode=fixture", { waitUntil: "networkidle", timeout: 120_000 });
  await page.getByRole("link", { name: "Save research snapshot" }).click();
  await page.waitForURL((url) => url.searchParams.get("originId") === "aapl-equity");
  assert(!page.url().includes("title=") && !page.url().includes("body="), "origin link leaked private payload fields");
  await page.getByRole("button", { name: "Save origin snapshot" }).click();
  await page.waitForFunction(() => document.querySelectorAll(".memory-item").length === 5);
  files.desktopOrigin = path.join(outputDirectory, "research-memory-demo-origin-save.png");
  await page.screenshot({ path: files.desktopOrigin, fullPage: false });

  const focusTarget = page.getByLabel("Find saved research");
  await focusTarget.focus();
  const focusOutline = await focusTarget.evaluate((element) => getComputedStyle(element).outlineStyle);
  assert(focusOutline !== "none", "keyboard focus indicator is missing");

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto(demoUrl, { waitUntil: "networkidle", timeout: 120_000 });
  const tablet = await inspect(page);
  assert(tablet.productWidth <= 768 && tablet.scrollWidth <= 768, "tablet layout overflows");
  files.tabletInbox = path.join(outputDirectory, "research-memory-demo-inbox-tablet.png");
  await page.screenshot({ path: files.tabletInbox, fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(demoUrl, { waitUntil: "networkidle", timeout: 120_000 });
  const mobile = await inspect(page);
  assert(mobile.productWidth >= 340 && mobile.productWidth <= 390 && mobile.scrollWidth <= 390, "mobile layout overflows: " + JSON.stringify(mobile));
  files.mobileInbox = path.join(outputDirectory, "research-memory-demo-inbox-mobile.png");
  await page.screenshot({ path: files.mobileInbox, fullPage: false });

  await page.setViewportSize({ width: 1200, height: 850 });
  const localUrl = baseUrl + "/?view=research-memory&collection=local-research&surface=inbox&mode=local";
  await page.goto(localUrl, { waitUntil: "networkidle", timeout: 120_000 });
  await page.waitForSelector(".research-memory-workstation");
  const local = await inspect(page);
  assert(local.privacyText.includes("Local-private SQLite"), "local privacy state is not visible");
  assert(page.url() === localUrl, "local route added unexpected URL state");
  files.localEmpty = path.join(outputDirectory, "research-memory-local-first-run.png");
  await page.screenshot({ path: files.localEmpty, fullPage: false });

  assert(consoleErrors.length === 0, "browser console errors: " + consoleErrors.join(" | "));
  const screenshotBytes = Object.fromEntries(await Promise.all(Object.entries(files).map(async ([key, file]) => [key, (await stat(file)).size])));
  console.log(JSON.stringify({ desktop, sources, tablet, mobile, local, focusOutline, finalUrl: page.url(), screenshotBytes, browserConsoleErrorCount: consoleErrors.length }, null, 2));
} finally {
  await browser.close();
}

async function inspect(page) {
  return page.locator(".research-memory-workstation").evaluate((root) => {
    const rect = root.getBoundingClientRect();
    return {
      items: root.querySelectorAll(".memory-item").length,
      metrics: root.querySelectorAll(".memory-metric").length,
      actions: root.querySelectorAll(".memory-action-rail section").length,
      tableRows: root.querySelectorAll(".memory-table-wrap tbody tr").length,
      productWidth: Math.round(rect.width),
      viewportWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      privacyText: root.querySelector(".memory-privacy-strip")?.textContent || "",
    };
  });
}

function assert(condition, message) { if (!condition) throw new Error(message); }
