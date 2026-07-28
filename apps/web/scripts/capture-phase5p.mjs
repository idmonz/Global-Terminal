import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5p_visual");
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

  await page.goto(`${baseUrl}/?view=war-room-map&mode=fixture`, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await waitForReplayAndMap(page, "fixture");
  const fixtureDesktop = await inspect(page);
  assert(fixtureDesktop.snapshotCount === 2, `expected two fictional replay snapshots, got ${fixtureDesktop.snapshotCount}`);
  assert(fixtureDesktop.compareActive, "fictional replay comparison is not active");
  assert(fixtureDesktop.markerCount >= 2, "fixture comparison map has no markers");
  assert(fixtureDesktop.loadedTiles > 0, "fixture map tiles are blank");
  assert(fixtureDesktop.diffCards === 5, `expected five diff domains, got ${fixtureDesktop.diffCards}`);
  assert(!fixtureDesktop.horizontalOverflow, "desktop document overflows horizontally");
  const fixtureDesktopPath = path.join(outputDirectory, "risk-replay-fixture-desktop.png");
  await page.screenshot({ path: fixtureDesktopPath, fullPage: false });

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.waitForTimeout(500);
  const tablet = await inspect(page);
  assert(tablet.mapWidth >= 480, `tablet map width is too small: ${tablet.mapWidth}`);
  assert(!tablet.horizontalOverflow, "tablet document overflows horizontally");
  const tabletPath = path.join(outputDirectory, "risk-replay-fixture-tablet.png");
  await page.screenshot({ path: tabletPath, fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  const mobile = await inspect(page);
  assert(mobile.mapWidth >= 340, `mobile map width is too small: ${mobile.mapWidth}`);
  assert(!mobile.horizontalOverflow, "mobile document overflows horizontally");
  const mobilePath = path.join(outputDirectory, "risk-replay-fixture-mobile.png");
  await page.screenshot({ path: mobilePath, fullPage: true });

  await page.setViewportSize({ width: 1200, height: 800 });
  await page.goto(`${baseUrl}/?view=war-room-map&mode=fixture&mapMode=fallback`, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForSelector('[data-map-state="fallback"]', { timeout: 120_000 });
  const fallback = await inspect(page);
  assert(fallback.markerCount >= 2, "fallback replay map lost markers");
  const fallbackPath = path.join(outputDirectory, "risk-replay-fallback.png");
  await page.screenshot({ path: fallbackPath, fullPage: false });

  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto(`${baseUrl}/?view=war-room-map&mode=cache`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.waitForSelector('[data-replay-state]', { timeout: 120_000 });
  await page.waitForFunction(() => !["loading"].includes(document.querySelector('[data-replay-state]')?.getAttribute("data-replay-state") || ""), { timeout: 180_000 });
  const initialLocalState = await page.locator('[data-replay-state]').getAttribute("data-replay-state");
  const capture = page.getByRole("button", { name: /Capture observation/i });
  assert(await capture.isEnabled(), "capture action is disabled despite configured local API");
  const beforeCount = Number(await page.locator('[data-replay-state]').getAttribute("data-snapshot-count") || 0);
  await capture.click();
  await page.waitForFunction((count) => {
    const root = document.querySelector('[data-replay-state]');
    return root?.getAttribute("data-replay-state") === "ready" && Number(root.getAttribute("data-snapshot-count") || 0) >= Number(count || 0);
  }, beforeCount, { timeout: 180_000 });
  await page.waitForURL((url) => /^mapsnap_[a-f0-9]{20}$/.test(url.searchParams.get("time") || ""), { timeout: 30_000 });
  const firstCaptureCount = Number(await page.locator('[data-replay-state]').getAttribute("data-snapshot-count") || 0);
  assert(firstCaptureCount >= 1, "capture did not create or return an observed snapshot");

  const compareSelect = page.locator(".snapshot-timeline-heading select");
  if (await compareSelect.isEnabled()) {
    await compareSelect.selectOption({ index: 1 });
    await page.waitForURL((url) => /^mapsnap_[a-f0-9]{20}$/.test(url.searchParams.get("compareTo") || ""), { timeout: 30_000 });
    await page.waitForFunction(() => {
      const root = document.querySelector('[data-replay-state]');
      return root?.getAttribute("data-replay-state") === "ready" && root.getAttribute("data-compare-active") === "true";
    }, null, { timeout: 120_000 });
    await page.waitForTimeout(750);
    await page.waitForSelector('[data-replay-state="ready"][data-compare-active="true"]', { timeout: 120_000 });
  }
  const compareActive = await page.locator('[data-replay-state]').getAttribute("data-compare-active") === "true";
  assert(firstCaptureCount < 2 || compareActive, "two or more captured observations did not activate compare mode");
  const live = await inspect(page);
  assert(live.markerCount > 0, "captured current map is blank");
  assert(live.loadedTiles > 0, "captured current map has no loaded tiles");
  const livePath = path.join(outputDirectory, "risk-replay-local-capture.png");
  await page.screenshot({ path: livePath, fullPage: false });

  for (const file of [fixtureDesktopPath, tabletPath, mobilePath, fallbackPath, livePath]) {
    assert((await stat(file)).size > 20_000, `${path.basename(file)} is unexpectedly small`);
  }
  assert(consoleErrors.length === 0, `browser console errors: ${consoleErrors.join(" | ")}`);
  assert(pageErrors.length === 0, `page errors: ${pageErrors.join(" | ")}`);

  console.log(JSON.stringify({
    fixtureDesktop,
    tablet,
    mobile,
    fallback,
    localCapture: live,
    initialLocalState,
    firstCaptureCount,
    compareActive,
    canonicalUrl: page.url(),
    consoleErrorCount: consoleErrors.length,
    pageErrorCount: pageErrors.length,
  }, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function waitForReplayAndMap(page, replayState) {
  await page.waitForSelector(`[data-replay-state="${replayState}"]`, { timeout: 120_000 });
  await page.waitForFunction(() => ["ready", "empty", "fallback", "error"].includes(document.querySelector('[data-renderer="leaflet-war-map"]')?.getAttribute("data-map-state") || ""), { timeout: 120_000 });
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-tile-loaded").length > 0, { timeout: 30_000 });
}

async function inspect(page) {
  return page.locator('[data-replay-state]').evaluate((root) => {
    const mapRoot = root.querySelector('[data-renderer="leaflet-war-map"]');
    const mapCanvas = root.querySelector(".global-map-canvas");
    const rect = mapCanvas?.getBoundingClientRect();
    return {
      replayState: root.getAttribute("data-replay-state"),
      snapshotCount: Number(root.getAttribute("data-snapshot-count") || 0),
      compareActive: root.getAttribute("data-compare-active") === "true",
      mapState: mapRoot?.getAttribute("data-map-state"),
      markerCount: Number(mapRoot?.getAttribute("data-map-marker-count") || 0),
      loadedTiles: root.querySelectorAll(".leaflet-tile-loaded").length,
      mapWidth: Math.round(rect?.width || 0),
      mapHeight: Math.round(rect?.height || 0),
      diffCards: root.querySelectorAll(".replay-diff-strip article").length,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
