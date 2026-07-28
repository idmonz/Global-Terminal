import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3045";
const expectedRuntime = process.env.GT_EXPECT_RUNTIME || "online";
const label = String(process.env.PHASE6B_LABEL || expectedRuntime).replace(/[^a-zA-Z0-9_-]/g, "_");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase6b_visual_${label}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const results = [];

try {
  results.push(await captureMap("market-map-desktop", { width: 1600, height: 1000 }));
  results.push(await captureMap("market-map-mobile", { width: 390, height: 844 }, true));
  results.push(await captureUnknown());
  if (expectedRuntime === "online") {
    results.push(await captureHierarchy());
    results.push(await captureRoundTrip());
  }
  const report = { baseUrl, expectedRuntime, captured_at: new Date().toISOString(), results };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function openMap(page, extra = "") {
  const started = Date.now();
  await page.goto(`${baseUrl}/?view=market-map&mode=live-if-available&selected=AAPL${extra}`, {
    waitUntil: "domcontentloaded",
    timeout: 180_000,
  });
  await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 180_000 });
  await page.waitForTimeout(400);
  return Date.now() - started;
}

async function captureMap(name, viewport, fullPage = false) {
  return withPage(name, viewport, fullPage, async (page) => {
    const firstUsefulPaintMs = await openMap(page);
    const observed = await page.evaluate(() => {
      const root = document.querySelector('[data-market-map-state="ready"]');
      const runtime = document.querySelector("[data-runtime-health-state]");
      return {
        runtimeReachable: runtime?.getAttribute("data-runtime-health-reachable"),
        rows: Number(root?.getAttribute("data-market-map-rows") || 0),
        taxonomy: Number(root?.getAttribute("data-market-map-taxonomy-coverage") || 0),
        providerTaxonomy: Number(root?.getAttribute("data-market-map-provider-taxonomy") || 0),
        taxonomyConflicts: Number(root?.getAttribute("data-market-map-taxonomy-conflicts") || 0),
        industry: Number(root?.getAttribute("data-market-map-industry-coverage") || 0),
        snapshotStatus: root?.getAttribute("data-market-snapshot-status"),
        snapshotVersion: root?.getAttribute("data-market-snapshot-version"),
        refreshStatus: root?.getAttribute("data-market-refresh-status"),
        historyRows: Number(document.querySelector("[data-market-refresh-history]")?.getAttribute("data-market-refresh-history") || 0),
        tiles: document.querySelectorAll(".market-map-tile").length,
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      };
    });
    if (expectedRuntime === "offline") {
      assert(observed.runtimeReachable === "false", `${name}: expected controlled offline runtime`);
      assert(observed.rows > 0, `${name}: fixture fallback is empty`);
    } else {
      assert(observed.runtimeReachable === "true", `${name}: runtime API is not reachable`);
      assert(observed.rows >= 300, `${name}: broad universe regressed to ${observed.rows}`);
      assert(observed.tiles === observed.rows, `${name}: tile mismatch ${observed.tiles}/${observed.rows}`);
      assert(observed.taxonomy >= 250, `${name}: classification coverage is ${observed.taxonomy}`);
      assert(observed.providerTaxonomy > 0, `${name}: provider sector evidence is absent`);
      assert(observed.industry >= 60, `${name}: reviewed industry coverage regressed`);
      assert(observed.snapshotVersion === "market_snapshot.v2", `${name}: snapshot version is ${observed.snapshotVersion}`);
      assert(observed.refreshStatus === "succeeded", `${name}: refresh status is ${observed.refreshStatus}`);
      assert(observed.historyRows > 0, `${name}: refresh history is not visible`);
      if (expectedRuntime === "stale") {
        assert(observed.snapshotStatus === "stale", `${name}: expected stale, got ${observed.snapshotStatus}`);
      }
    }
    assert(!observed.horizontalOverflow, `${name}: page-level horizontal overflow`);
    return { ...observed, firstUsefulPaintMs };
  });
}

async function captureHierarchy() {
  return withPage("market-map-hierarchy", { width: 1600, height: 1000 }, false, async (page) => {
    await openMap(page);
    const button = page.locator(".market-map-sector > header button:not([disabled])").filter({ hasText: "Technology" }).first();
    const target = await button.count() ? button : page.locator(".market-map-sector > header button:not([disabled])").first();
    const sector = (await target.innerText()).trim();
    const started = Date.now();
    await target.click();
    await page.waitForFunction((value) => new URL(window.location.href).searchParams.get("sector") === value, sector);
    const interactionMs = Date.now() - started;
    const observed = await page.evaluate(() => ({
      groups: document.querySelectorAll(".market-map-sector").length,
      rows: Number(document.querySelector('[data-market-map-state="ready"]')?.getAttribute("data-market-map-rows") || 0),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    }));
    assert(observed.groups > 0 && observed.rows > 0, "hierarchy drilldown is empty");
    assert(!observed.horizontalOverflow, "hierarchy drilldown overflows");
    return { ...observed, sector, interactionMs };
  });
}

async function captureRoundTrip() {
  return withPage("market-map-aapl-round-trip", { width: 1600, height: 1000 }, false, async (page) => {
    await openMap(page, "&query=AAPL&size=equal&color=relative_volume");
    await page.getByRole("link", { name: "Open workstation", exact: true }).click();
    await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 180_000 });
    await page.getByRole("link", { name: "Return to saved screen state", exact: true }).click();
    await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 180_000 });
    const returned = new URL(page.url());
    const observed = {
      query: returned.searchParams.get("query"),
      selected: returned.searchParams.get("selected"),
      size: returned.searchParams.get("size"),
      color: returned.searchParams.get("color"),
    };
    assert(observed.query === "AAPL" && observed.selected === "AAPL", "round trip lost selection");
    assert(observed.size === "equal" && observed.color === "relative_volume", "round trip lost encoding");
    return observed;
  });
}

async function captureUnknown() {
  return withPage("unknown-symbol", { width: 1600, height: 1000 }, false, async (page) => {
    await page.goto(`${baseUrl}/?view=asset&symbol=NOTAREAL123&assetClass=equity&mode=live-if-available`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 180_000 });
    const observed = await page.evaluate(() => ({
      unknown: Boolean(document.querySelector('[data-symbol-workstation-state="unknown-symbol"]'))
        || document.body.textContent?.toLowerCase().includes("unknown symbol"),
      leakedApple: document.body.textContent?.includes("Apple Inc") || false,
    }));
    assert(observed.unknown, "unknown-symbol state is absent");
    assert(!observed.leakedApple, "unknown symbol leaked AAPL identity");
    return observed;
  });
}

async function withPage(name, viewport, fullPage, inspect) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error" || message.type() === "warning") errors.push(`${message.type()}: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
  try {
    const observed = await inspect(page);
    assert(errors.length === 0, `${name}: browser errors ${errors.join(" | ")}`);
    const screenshot = path.join(outputDirectory, `${name}.png`);
    await page.screenshot({ path: screenshot, fullPage, timeout: 120_000 });
    const screenshotBytes = (await stat(screenshot)).size;
    assert(screenshotBytes > 15_000, `${name}: screenshot is unexpectedly small`);
    return { name, ...observed, screenshot, screenshotBytes, url: page.url() };
  } finally {
    await page.close();
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
