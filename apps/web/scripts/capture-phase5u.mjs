import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const runLabel = sanitizeLabel(process.env.PHASE5U_LABEL || "final");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase5u_${runLabel}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3000";

const desktopRoutes = [
  { id: "war-map-cache-desktop", url: "/?view=war-room-map&mode=cache", waitFor: '[data-product-view="global-risk-map"]', expectFallback: false },
  { id: "war-map-fixture-desktop", url: "/?view=war-room-map&mode=fixture", waitFor: '[data-product-view="global-risk-map"]', expectFallback: false },
  { id: "war-map-fallback-desktop", url: "/?view=war-room-map&mode=fixture&mapMode=fallback", waitFor: '[data-product-view="global-risk-map"]', expectFallback: true },
  { id: "news-fixture-desktop", url: "/?view=news&mode=fixture", waitFor: '[data-product-view="news-workspace"]', expectFallback: false },
];

const mobileRoutes = [
  { id: "war-map-cache-mobile", url: "/?view=war-room-map&mode=cache", waitFor: '[data-product-view="global-risk-map"]', expectFallback: false },
  { id: "war-map-fixture-mobile", url: "/?view=war-room-map&mode=fixture", waitFor: '[data-product-view="global-risk-map"]', expectFallback: false },
];

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const consoleErrors = [];
const pageErrors = [];
const results = [];

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(`${page.url()} :: ${message.text()}`);
  });
  page.on("pageerror", (error) => pageErrors.push(`${page.url()} :: ${error.message}`));

  for (const route of desktopRoutes) {
    await visit(page, route);
    const inspection = await inspect(page);
    const screenshotPath = path.join(outputDirectory, `${route.id}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    const screenshotBytes = (await stat(screenshotPath)).size;
    results.push({ ...route, ...inspection, screenshot: screenshotPath, screenshotBytes });
  }

  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of mobileRoutes) {
    await visit(page, route);
    const inspection = await inspect(page);
    const screenshotPath = path.join(outputDirectory, `${route.id}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    const screenshotBytes = (await stat(screenshotPath)).size;
    results.push({ ...route, ...inspection, screenshot: screenshotPath, screenshotBytes });
  }

  const summary = {
    runLabel,
    baseUrl,
    outputDirectory,
    consoleErrorCount: consoleErrors.length,
    pageErrorCount: pageErrors.length,
    results,
    consoleErrors,
    pageErrors,
  };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));

  const desktopCache = result("war-map-cache-desktop");
  assert(desktopCache.maps > 0, "desktop cache route did not render a map surface");
  assert(desktopCache.mapMarkerCount > 0, "desktop cache route has no map markers");
  assert(["ready", "fallback"].includes(desktopCache.mapState), `desktop cache map state is ${desktopCache.mapState}`);
  assert(desktopCache.sourceStrip > 0, "desktop cache route is missing the compact source boundary");
  assert(desktopCache.opsToolbar > 0, "desktop cache route is missing the operations toolbar");
  assert(desktopCache.layerControls > 0, "desktop cache route is missing layer controls");
  assert(desktopCache.eventInspector > 0, "desktop cache route is missing the event inspector");
  assert(desktopCache.eventRows > 0, "desktop cache route is missing the event stream");
  assert(desktopCache.mapTop <= 430, `desktop map begins too low for a map-first desk: ${desktopCache.mapTop}`);
  assert(!desktopCache.horizontalOverflow, "desktop cache route overflows horizontally");

  const fixtureDesktop = result("war-map-fixture-desktop");
  assert(fixtureDesktop.mapMarkerCount > 0, "fixture route has no markers");
  assert(fixtureDesktop.sourceStrip > 0 && fixtureDesktop.opsToolbar > 0, "fixture route is missing Phase 5U controls");
  assert(fixtureDesktop.mapTop <= 430, `fixture desktop map begins too low: ${fixtureDesktop.mapTop}`);

  const fallbackDesktop = result("war-map-fallback-desktop");
  assert(fallbackDesktop.mapState === "fallback", `fallback route did not use fallback renderer: ${fallbackDesktop.mapState}`);
  assert(fallbackDesktop.mapMarkerCount > 0, "fallback route lost marker rows");
  assert(fallbackDesktop.mapTop <= 430, `fallback desktop map begins too low: ${fallbackDesktop.mapTop}`);

  const mobileCache = result("war-map-cache-mobile");
  assert(mobileCache.maps > 0, "mobile cache route did not render a map");
  assert(mobileCache.mapMarkerCount > 0, "mobile cache route has no markers");
  assert(mobileCache.sourceStrip > 0 && mobileCache.opsToolbar > 0, "mobile cache route is missing Phase 5U controls");
  assert(mobileCache.mapTop <= 720, `mobile map begins too low for first-viewport work: ${mobileCache.mapTop}`);
  assert(!mobileCache.horizontalOverflow, "mobile cache route overflows horizontally");

  const mobileFixture = result("war-map-fixture-mobile");
  assert(mobileFixture.mapMarkerCount > 0, "mobile fixture route has no markers");
  assert(mobileFixture.mapTop <= 720, `mobile fixture map begins too low: ${mobileFixture.mapTop}`);
  assert(!mobileFixture.horizontalOverflow, "mobile fixture route overflows horizontally");

  const newsFixture = result("news-fixture-desktop");
  assert(newsFixture.newsRows > 0 || newsFixture.newsEmptyStates > 0, "news fixture route lost story/source rows");
  assert(consoleErrors.length === 0, `browser console errors: ${consoleErrors.join(" | ")}`);
  assert(pageErrors.length === 0, `page errors: ${pageErrors.join(" | ")}`);
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function visit(page, route) {
  await page.goto(`${baseUrl}${route.url}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.waitForSelector(route.waitFor, { timeout: 180_000 });
  if (route.url.includes("war-room-map")) {
    await page.waitForSelector('[data-phase5u-map-first="true"]', { timeout: 180_000 });
    await page.waitForFunction(
      () => ["ready", "empty", "fallback", "error"].includes(document.querySelector('[data-renderer="leaflet-war-map"]')?.getAttribute("data-map-state") || ""),
      { timeout: 180_000 },
    );
    if (!route.expectFallback) {
      await page.waitForFunction(
        () => document.querySelectorAll(".leaflet-tile-loaded").length > 0 || document.querySelector('[data-renderer="leaflet-war-map"]')?.getAttribute("data-map-state") === "fallback",
        { timeout: 30_000 },
      ).catch(() => undefined);
    }
  }
  await page.waitForTimeout(450);
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const text = document.body.innerText || "";
    const visible = (selector) => Array.from(document.querySelectorAll(selector)).filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 2 && rect.height > 2;
    }).length;
    const firstRect = (selector) => {
      const node = document.querySelector(selector);
      const rect = node?.getBoundingClientRect();
      return rect ? { top: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height) } : { top: 0, width: 0, height: 0 };
    };
    const mapRoot = document.querySelector('[data-renderer="leaflet-war-map"]');
    const canvasRect = firstRect(".global-map-canvas");
    return {
      title: document.title,
      h1: document.querySelector("h1")?.textContent?.trim() || "",
      h2: document.querySelector("h2")?.textContent?.trim() || "",
      maps: visible(".leaflet-container, .leaflet-war-map, .global-map-canvas, .global-map-fallback, [data-renderer='leaflet-war-map']"),
      mapState: mapRoot?.getAttribute("data-map-state") || "",
      mapMarkerCount: Number(mapRoot?.getAttribute("data-map-marker-count") || 0),
      mapEventCount: Number(mapRoot?.getAttribute("data-map-event-count") || 0),
      loadedTiles: document.querySelectorAll(".leaflet-tile-loaded").length,
      mapTop: canvasRect.top,
      mapWidth: canvasRect.width,
      mapHeight: canvasRect.height,
      sourceStrip: visible("[data-phase5u-source-strip='true']"),
      opsToolbar: visible(".war-map-ops-toolbar"),
      runtimeDetail: visible(".war-map-runtime-detail"),
      timeline: visible(".war-map-ops-timeline"),
      diffStrip: visible(".war-map-ops-diff"),
      layerControls: visible(".global-map-layer-row"),
      eventInspector: visible(".global-event-inspector"),
      eventRows: visible(".global-map-event-list button"),
      relatedReporting: visible(".event-evidence-section article"),
      marketTransmission: visible(".event-asset-link"),
      sourceGaps: visible(".global-map-source-gaps div"),
      newsRows: visible(".news-workspace-row, .news-cluster-card, .news-source-row, .fusion-news-row"),
      newsEmptyStates: visible(".news-empty-state"),
      productNavLinks: visible(".product-nav-link"),
      hasContractDiagnosticsText: text.includes("Contract diagnostics"),
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
      bodyTextLength: text.length,
    };
  });
}

function result(id) {
  return results.find((row) => row.id === id);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sanitizeLabel(value) {
  return String(value).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 48) || "final";
}
