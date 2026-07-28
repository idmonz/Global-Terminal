import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repoRoot = path.resolve(appRoot, "../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3042";
const expectedRuntime = process.env.GT_EXPECT_RUNTIME || "online";
const runLabel = sanitizeLabel(process.env.PHASE5Y_LABEL || expectedRuntime);
const outputDirectory = path.join(repoRoot, "review_workspace", `phase5y_map_intelligence_${runLabel}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
const consoleErrors = [];
const pageErrors = [];
const results = [];

page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(`${page.url()} :: ${message.text()}`);
});
page.on("pageerror", (error) => pageErrors.push(`${page.url()} :: ${error.message}`));

try {
  await visitMap(page, "/?view=war-room-map&mode=live-if-available");
  results.push(await capture(page, "war-map-online-desktop"));

  const beforeTitle = await page.locator(".marker-detail-title").innerText();
  const focusButtons = page.locator(".global-map-focus-rail button");
  if (await focusButtons.count() > 1) {
    await focusButtons.nth(1).click();
    await page.waitForFunction((previous) => document.querySelector(".marker-detail-title")?.textContent?.trim() !== previous, beforeTitle);
  }
  results.push(await capture(page, "war-map-selected-context"));

  await page.goto(`${baseUrl}/?view=news&mode=live-if-available`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.waitForSelector('[data-product-view="news-workspace"]', { timeout: 180_000 });
  results.push(await capture(page, "news-from-map"));

  const originState = encodeURIComponent("mode=live-if-available&layers=earthquakes,chokepoints&event=marker:phase5y");
  await page.goto(`${baseUrl}/?view=asset&symbol=AAPL&assetClass=equity&mode=cache&originView=war-room-map&originState=${originState}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 180_000 });
  await page.waitForFunction(
    () => ["ready", "fallback", "error"].includes(document.querySelector("[data-chart-state]")?.getAttribute("data-chart-state") || ""),
    { timeout: 60_000 },
  );
  results.push(await capture(page, "aapl-map-origin"));

  await page.setViewportSize({ width: 390, height: 844 });
  await visitMap(page, "/?view=war-room-map&mode=live-if-available");
  results.push(await capture(page, "war-map-online-mobile"));

  const desktop = result("war-map-online-desktop");
  const selected = result("war-map-selected-context");
  const news = result("news-from-map");
  const aapl = result("aapl-map-origin");
  const mobile = result("war-map-online-mobile");

  assert(desktop.mapState === "ready" || desktop.mapState === "fallback", `desktop map state is ${desktop.mapState}`);
  assert(desktop.mapMarkerCount > 0, "desktop map has no markers");
  assert(desktop.focusButtons > 0, "priority event context rail is missing");
  assert(desktop.contextStatus !== "event-only", "default event has no linked context");
  assert(desktop.mapTop <= 430, `desktop map starts too low: ${desktop.mapTop}`);
  assert(!desktop.url.includes("time="), "current map silently switched to replay history");
  assert(!desktop.horizontalOverflow, "desktop map overflows horizontally");
  if (desktop.relatedReporting === 0) {
    assert(desktop.newsDeskLinks > 0, "empty event reporting state has no News desk action");
  }

  if (expectedRuntime === "online") {
    assert(desktop.runtimeState === "online", `expected online runtime, observed ${desktop.runtimeState}`);
    assert(desktop.sourceBackedCount > 0, "online map claims no source-backed markers");
    assert(desktop.mapMarkerCount >= 20, `online map density unexpectedly low: ${desktop.mapMarkerCount}`);
  } else {
    assert(desktop.runtimeState === "offline", `expected offline runtime, observed ${desktop.runtimeState}`);
    assert(desktop.runtimeFallback, "offline route does not expose runtime fallback");
  }

  assert(selected.inspectorTitle !== desktop.inspectorTitle || selected.url !== desktop.url, "event selection did not change map context");
  assert(selected.url.includes("event="), "selected event was not persisted in the URL");
  assert(selected.contextStatus.length > 0, "selected event context status is missing");
  assert(news.newsRows > 0 || news.newsEmptyStates > 0, "news route has neither rows nor explicit empty state");
  assert(aapl.returnToMapLinks > 0, "AAPL map-origin route has no return-to-map action");
  assert(aapl.chartState === "ready" || aapl.chartState === "fallback", `AAPL chart state is ${aapl.chartState}`);
  assert(mobile.mapTop <= 720, `mobile map starts too low: ${mobile.mapTop}`);
  assert(mobile.mapMarkerCount > 0, "mobile map has no markers");
  assert(!mobile.horizontalOverflow, "mobile map overflows horizontally");
  assert(consoleErrors.length === 0, `browser console errors: ${consoleErrors.join(" | ")}`);
  assert(pageErrors.length === 0, `page errors: ${pageErrors.join(" | ")}`);

  const summary = { baseUrl, expectedRuntime, outputDirectory, results, consoleErrors, pageErrors };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

async function visitMap(target, route) {
  await target.goto(`${baseUrl}${route}`, { waitUntil: "domcontentloaded", timeout: 180_000 });
  await target.waitForSelector('[data-product-view="global-risk-map"]', { timeout: 180_000 });
  await target.waitForFunction(
    () => ["ready", "empty", "fallback", "error"].includes(document.querySelector('[data-renderer="leaflet-war-map"]')?.getAttribute("data-map-state") || ""),
    { timeout: 180_000 },
  );
  await target.waitForFunction(
    () => document.querySelectorAll(".leaflet-tile-loaded").length > 0 || document.querySelector('[data-renderer="leaflet-war-map"]')?.getAttribute("data-map-state") === "fallback",
    { timeout: 30_000 },
  ).catch(() => undefined);
  await target.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
  });
  await target.waitForTimeout(1200);
}

async function capture(target, id) {
  const inspection = await target.evaluate(() => {
    const root = document.documentElement;
    const map = document.querySelector('[data-renderer="leaflet-war-map"]');
    const chart = document.querySelector("[data-chart-state]");
    const runtimeChip = document.querySelector(".runtime-health-chip strong");
    const runtimeText = runtimeChip?.textContent?.trim().toLowerCase() || "";
    const sourceBackedPill = Array.from(document.querySelectorAll(".global-map-header-stats .status-pill"))
      .find((node) => node.querySelector("small")?.textContent?.trim().toLowerCase() === "source-backed");
    const mapRect = document.querySelector(".global-map-canvas")?.getBoundingClientRect();
    const visible = (selector) => Array.from(document.querySelectorAll(selector)).filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 2 && rect.height > 2;
    }).length;
    return {
      url: window.location.href,
      runtimeState: runtimeText === "online" ? "online" : runtimeText === "offline" ? "offline" : runtimeText || "unknown",
      runtimeFallback: Boolean(document.querySelector(".runtime-fallback-notice"))
        || document.body.innerText.toLowerCase().includes("static fixture fallback")
        || document.body.innerText.toLowerCase().includes("runtime-fallback"),
      mapState: map?.getAttribute("data-map-state") || "",
      mapMarkerCount: Number(map?.getAttribute("data-map-marker-count") || 0),
      mapEventCount: Number(map?.getAttribute("data-map-event-count") || 0),
      mapTop: Math.round(mapRect?.top || 0),
      loadedTiles: document.querySelectorAll(".leaflet-tile-loaded").length,
      focusButtons: visible(".global-map-focus-rail button"),
      contextStatus: document.querySelector(".global-event-inspector")?.getAttribute("data-event-context-status") || "",
      inspectorTitle: document.querySelector(".marker-detail-title")?.textContent?.trim() || "",
      relatedReporting: visible(".event-news-section article"),
      newsDeskLinks: visible(".event-news-section .event-evidence-empty a"),
      transmissionPathRows: visible(".event-path-section article"),
      transmissionRows: visible(".event-asset-link"),
      sourceBackedCount: Number(sourceBackedPill?.querySelector("strong")?.textContent || 0),
      newsRows: visible(".news-workspace-row, .news-cluster-card, .news-source-row, .fusion-news-row"),
      newsEmptyStates: visible(".news-empty-state"),
      returnToMapLinks: Array.from(document.querySelectorAll("a")).filter((node) => node.textContent?.includes("Return to selected map event")).length,
      chartState: chart?.getAttribute("data-chart-state") || "",
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
    };
  });
  const screenshot = path.join(outputDirectory, `${id}.png`);
  await target.screenshot({ path: screenshot, fullPage: false });
  return { id, ...inspection, screenshot, screenshotBytes: (await stat(screenshot)).size };
}

function result(id) {
  return results.find((row) => row.id === id);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sanitizeLabel(value) {
  return String(value).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 48) || "run";
}
