import { mkdir, stat } from "node:fs/promises";
import { appendFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5h_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";
const productUrl = `${baseUrl}/?view=war-room-map&mode=cache&layers=chokepoints&timeline=24h&compare=off&event=none`;

await mkdir(outputDirectory, { recursive: true });
const runLogPath = path.join(outputDirectory, "playwright-run.log");
writeFileSync(runLogPath, "start\n", "utf8");

const browser = await chromium.launch({ executablePath: chromePath, headless: true });
appendFileSync(runLogPath, "browser-launched\n", "utf8");
const browserConsoleErrors = [];

try {
  const desktop = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  desktop.on("console", (message) => {
    if (message.type() === "error") browserConsoleErrors.push(message.text());
  });
  await desktop.goto(productUrl, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await desktop.waitForSelector('[data-product-view="global-risk-map"]', { timeout: 120_000 });
  await desktop.waitForFunction(() => {
    const map = document.querySelector('[data-renderer="leaflet-war-map"]');
    return map && ["ready", "empty", "fallback", "error"].includes(map.getAttribute("data-map-state") || "");
  }, { timeout: 120_000 });
  await desktop.waitForFunction(
    () => document.querySelectorAll(".leaflet-tile-loaded").length > 0,
    { timeout: 15_000 },
  );

  const initial = await inspectMap(desktop);
  assert(initial.state === "ready", `expected ready map, received ${initial.state}`);
  assert(initial.markerCount > 0, "expected at least one rendered marker");
  assert(initial.mapWidth >= 700 && initial.mapHeight >= 500, `map is undersized: ${initial.mapWidth}x${initial.mapHeight}`);
  assert(initial.loadedTiles > 0, "expected at least one loaded Leaflet tile");

  const desktopPath = path.join(outputDirectory, "global-risk-map-cache-desktop.png");
  await desktop.screenshot({ path: desktopPath, fullPage: false });
  appendFileSync(runLogPath, `desktop-captured ${desktopPath}\n`, "utf8");

  await desktop.getByRole("button", { name: "Last 7d" }).click();
  await desktop.waitForURL((url) => url.searchParams.get("timeline") === "7d");
  const firstEvent = desktop.locator(".global-map-event-list button").first();
  await firstEvent.click();
  await desktop.waitForURL((url) => ![null, "none"].includes(url.searchParams.get("event")));
  const compareSelect = desktop.locator(".global-map-compare-control select");
  const compareOptions = await compareSelect.locator("option").count();
  if (compareOptions > 1) {
    await compareSelect.selectOption({ index: 1 });
    await desktop.waitForURL((url) => url.searchParams.get("compare") !== "off");
  }
  assert(new URL(desktop.url()).searchParams.has("layers"), "canonical map URL is missing layers state");
  assert(new URL(desktop.url()).searchParams.has("compare"), "canonical map URL is missing compare state");
  assert(new URL(desktop.url()).searchParams.has("event"), "canonical map URL is missing event state");
  const canonicalUrl = desktop.url();

  await desktop.setViewportSize({ width: 390, height: 844 });
  await desktop.waitForTimeout(1_000);
  appendFileSync(runLogPath, "mobile-viewport-ready\n", "utf8");
  const mobileInspection = await inspectMap(desktop);
  assert(mobileInspection.markerCount > 0, "mobile map did not render markers");
  assert(mobileInspection.mapWidth >= 340 && mobileInspection.mapHeight >= 500, `mobile map is undersized: ${mobileInspection.mapWidth}x${mobileInspection.mapHeight}`);

  const mobilePath = path.join(outputDirectory, "global-risk-map-cache-mobile.png");
  await desktop.screenshot({ path: mobilePath, fullPage: false });
  appendFileSync(runLogPath, `mobile-captured ${mobilePath}\n`, "utf8");

  await desktop.setViewportSize({ width: 1200, height: 800 });
  await desktop.goto(`${productUrl}&mapMode=fallback`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await desktop.waitForSelector('[data-map-state="fallback"]', { timeout: 30_000 });
  const fallbackInspection = await inspectMap(desktop);
  assert(fallbackInspection.markerCount > 0, "fallback map did not retain event rows");
  const fallbackPath = path.join(outputDirectory, "global-risk-map-fallback.png");
  await desktop.screenshot({ path: fallbackPath, fullPage: false });
  appendFileSync(runLogPath, `fallback-captured ${fallbackPath}\n`, "utf8");

  const desktopBytes = (await stat(desktopPath)).size;
  const mobileBytes = (await stat(mobilePath)).size;
  const fallbackBytes = (await stat(fallbackPath)).size;
  assert(desktopBytes > 20_000, `desktop screenshot is unexpectedly small: ${desktopBytes}`);
  assert(mobileBytes > 12_000, `mobile screenshot is unexpectedly small: ${mobileBytes}`);

  console.log(JSON.stringify({
    desktop: { ...initial, screenshotBytes: desktopBytes },
    mobile: { ...mobileInspection, screenshotBytes: mobileBytes },
    fallback: { ...fallbackInspection, screenshotBytes: fallbackBytes },
    canonicalUrl,
    browserConsoleErrorCount: browserConsoleErrors.length,
  }, null, 2));
  appendFileSync(runLogPath, "complete\n", "utf8");
} catch (error) {
  appendFileSync(runLogPath, `error ${error instanceof Error ? error.stack : String(error)}\n`, "utf8");
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function inspectMap(page) {
  return page.locator('[data-renderer="leaflet-war-map"]').evaluate((root) => {
    const canvas = root.querySelector(".global-map-canvas");
    const rect = canvas?.getBoundingClientRect();
    return {
      state: root.getAttribute("data-map-state"),
      markerCount: Number(root.getAttribute("data-map-marker-count") || 0),
      eventCount: Number(root.getAttribute("data-map-event-count") || 0),
      loadedTiles: root.querySelectorAll(".leaflet-tile-loaded").length,
      mapWidth: Math.round(rect?.width || 0),
      mapHeight: Math.round(rect?.height || 0),
    };
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
