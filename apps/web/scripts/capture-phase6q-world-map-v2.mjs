import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3467";
const outputDirectory = path.join(repoRoot, "review_workspace", "phase6q_world_map_v2_visual");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const captures = {};

try {
  const desktopContext = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const desktop = await desktopContext.newPage();
  const desktopTelemetry = telemetry(desktop);
  await visitMap(desktop, "/?view=war-room-map&mode=live-if-available&mapRegion=global");
  captures.desktop = await capture(desktop, "world-map-live-desktop", desktopTelemetry);

  const asiaButton = desktop.getByRole("button", { name: "Asia", exact: true });
  await asiaButton.click();
  await desktop.waitForFunction(() => new URLSearchParams(window.location.search).get("mapRegion") === "asia");
  await desktop.waitForTimeout(800);
  captures.asia = await capture(desktop, "world-map-asia-preset", desktopTelemetry);
  await desktopContext.close();

  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const mobile = await mobileContext.newPage();
  const mobileTelemetry = telemetry(mobile);
  await visitMap(mobile, "/?view=war-room-map&mode=live-if-available&mapRegion=global");
  captures.mobile = await capture(mobile, "world-map-live-mobile", mobileTelemetry);
  const mobileTallPath = path.join(outputDirectory, "world-map-live-mobile-tall.png");
  await mobile.screenshot({ path: mobileTallPath, fullPage: true });
  captures.mobile.tallScreenshot = { file: mobileTallPath, bytes: (await stat(mobileTallPath)).size };
  await mobileContext.close();

  const failureContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const failurePage = await failureContext.newPage();
  const failureTelemetry = telemetry(failurePage);
  await failurePage.route("https://tile.openstreetmap.org/**", (route) => route.abort("failed"));
  await failurePage.goto(`${baseUrl}/?view=war-room-map&mode=fixture&mapRegion=global`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await failurePage.waitForSelector('[data-product-view="global-risk-map"]', { timeout: 180_000 });
  await failurePage.waitForFunction(
    () => document.querySelector('[data-renderer="leaflet-war-map"]')?.getAttribute("data-map-state") === "fallback",
    { timeout: 60_000 },
  );
  captures.tileFailure = await capture(failurePage, "world-map-tile-failure-fallback", failureTelemetry);
  await failureContext.close();

  assert(["ready", "fallback"].includes(captures.desktop.mapState), `desktop map state ${captures.desktop.mapState}`);
  assert(captures.desktop.basemapState === "ready" || captures.desktop.mapState === "fallback", `desktop basemap state ${captures.desktop.basemapState}`);
  assert(captures.desktop.eventCount >= 20, `desktop event density ${captures.desktop.eventCount}`);
  assert(captures.desktop.markerCount > 0, "desktop map has no rendered markers");
  assert(captures.desktop.markerCount < captures.desktop.eventCount, "global zoom did not cluster the event surface");
  assert(captures.desktop.wildfireLayerVisible, "NASA EONET Wildfires layer is not visible");
  assert(captures.desktop.regionControlCount >= 7, "region preset controls are incomplete");
  assert(captures.desktop.loadedTiles > 0 || captures.desktop.mapState === "fallback", "desktop map has no loaded basemap tiles");
  assert(!captures.desktop.horizontalOverflow, "desktop page overflows horizontally");
  assert(captures.desktop.errors.length === 0, `desktop browser errors: ${captures.desktop.errors.join(" | ")}`);

  assert(captures.asia.url.includes("mapRegion=asia"), "Asia preset is absent from URL state");
  assert(/[?&]lat=/.test(captures.asia.url) && /[?&]lon=/.test(captures.asia.url) && /[?&]zoom=/.test(captures.asia.url), "shareable viewport coordinates are missing");
  assert(captures.asia.activeRegion === "Asia", `active region is ${captures.asia.activeRegion}`);
  assert(!captures.asia.horizontalOverflow, "Asia preset page overflows horizontally");
  assert(captures.asia.errors.length === 0, `Asia preset browser errors: ${captures.asia.errors.join(" | ")}`);

  assert(captures.mobile.eventCount >= 20, `mobile event density ${captures.mobile.eventCount}`);
  assert(captures.mobile.mapWidth <= 390, `mobile map width ${captures.mobile.mapWidth}`);
  assert(captures.mobile.regionControlCount >= 7, "mobile region controls are incomplete");
  assert(captures.mobile.layersExpanded === false, "mobile map layers should be collapsed by default");
  assert(captures.mobile.visibleLayerRows === 0, "collapsed mobile layer drawer still covers the map");
  assert(!captures.mobile.horizontalOverflow, "mobile page overflows horizontally");
  assert(captures.mobile.errors.length === 0, `mobile browser errors: ${captures.mobile.errors.join(" | ")}`);

  assert(captures.tileFailure.mapState === "fallback", `tile failure state ${captures.tileFailure.mapState}`);
  assert(captures.tileFailure.basemapState === "fallback", `tile failure basemap state ${captures.tileFailure.basemapState}`);
  assert(captures.tileFailure.fallbackVisible, "accessible fallback map is not visible");
  assert(!captures.tileFailure.horizontalOverflow, "fallback page overflows horizontally");

  const summary = {
    evidence_version: "phase6q.world-map.v2.visual.v1",
    product_phase: "Phase 6Q map intelligence continuation",
    base_url: baseUrl,
    captured_at: new Date().toISOString(),
    captures,
    passed: true,
  };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function visitMap(page, route) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.waitForSelector('[data-product-view="global-risk-map"]', { timeout: 180_000 });
  await page.waitForFunction(
    () => ["ready", "fallback", "empty", "error"].includes(document.querySelector('[data-renderer="leaflet-war-map"]')?.getAttribute("data-map-state") || ""),
    { timeout: 180_000 },
  );
  await page.evaluate(async () => { if (document.fonts?.ready) await document.fonts.ready; });
  await page.waitForTimeout(1000);
}

function telemetry(page) {
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  return errors;
}

async function capture(page, id, errors) {
  const inspection = await page.evaluate(() => {
    const root = document.documentElement;
    const map = document.querySelector('[data-renderer="leaflet-war-map"]');
    const mapRect = document.querySelector(".global-map-canvas")?.getBoundingClientRect();
    const activeRegion = document.querySelector(".global-map-region-controls button.active")?.textContent?.trim() || "";
    const layerLabels = Array.from(document.querySelectorAll(".global-map-layer-row b")).map((node) => node.textContent?.trim() || "");
    return {
      url: window.location.href,
      mapState: map?.getAttribute("data-map-state") || "",
      basemapState: map?.getAttribute("data-basemap-state") || "",
      markerCount: Number(map?.getAttribute("data-map-marker-count") || 0),
      eventCount: Number(map?.getAttribute("data-map-event-count") || 0),
      mapWidth: Math.round(mapRect?.width || 0),
      mapHeight: Math.round(mapRect?.height || 0),
      loadedTiles: document.querySelectorAll(".leaflet-tile-loaded").length,
      wildfireLayerVisible: layerLabels.includes("Wildfires"),
      layersExpanded: document.querySelector(".global-map-layer-overlay")?.classList.contains("expanded") || false,
      visibleLayerRows: Array.from(document.querySelectorAll(".global-map-layer-row")).filter((node) => {
        const style = window.getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.display !== "none" && rect.width > 0 && rect.height > 0;
      }).length,
      regionControlCount: document.querySelectorAll(".global-map-region-controls button").length,
      activeRegion,
      fallbackVisible: Boolean(document.querySelector(".global-map-fallback")),
      duplicateIds: Array.from(document.querySelectorAll("[id]")).map((node) => node.id).filter((id, index, values) => values.indexOf(id) !== index),
      unlabeledControlDetails: Array.from(document.querySelectorAll("button, select, input")).filter((node) => {
        const label =
          node.getAttribute("aria-label") ||
          node.getAttribute("title") ||
          node.textContent?.trim() ||
          node.closest("label")?.textContent?.trim() ||
          Array.from(node.labels || []).map((labelNode) => labelNode.textContent?.trim()).find(Boolean);
        return !label;
      }).map((node) => ({
        tag: node.tagName.toLowerCase(),
        type: node.getAttribute("type") || "",
        id: node.id,
        className: node.getAttribute("class") || "",
        placeholder: node.getAttribute("placeholder") || "",
      })),
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
    };
  });
  assert(inspection.mapWidth > 300 && inspection.mapHeight > 400, `${id} map surface is too small`);
  assert(inspection.duplicateIds.length === 0, `${id} duplicate IDs: ${inspection.duplicateIds.join(",")}`);
  assert(inspection.unlabeledControlDetails.length === 0, `${id} has unlabeled controls: ${JSON.stringify(inspection.unlabeledControlDetails)}`);
  const screenshot = path.join(outputDirectory, `${id}.png`);
  await page.screenshot({ path: screenshot, fullPage: false });
  return {
    ...inspection,
    unlabeledControls: inspection.unlabeledControlDetails.length,
    errors: [...errors],
    screenshot: { file: screenshot, bytes: (await stat(screenshot)).size },
  };
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
