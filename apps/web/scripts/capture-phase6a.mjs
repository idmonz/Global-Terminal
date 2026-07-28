import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const baseUrl = process.env.GT_BASE_URL || "http://127.0.0.1:3045";
const expectedRuntime = process.env.GT_EXPECT_RUNTIME || "online";
const label = String(process.env.PHASE6A_LABEL || expectedRuntime).replace(/[^a-zA-Z0-9_-]/g, "_");
const outputDirectory = path.join(repoRoot, "review_workspace", `phase6a_visual_${label}`);
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const results = [];

try {
  results.push(await captureMap("market-map-desktop", { width: 1600, height: 1000 }));
  results.push(await captureFinancials("aapl-financials", { width: 1600, height: 1000 }));
  results.push(await captureMap("market-map-mobile", { width: 390, height: 844 }, true));
  results.push(await captureFinancials("aapl-financials-mobile", { width: 390, height: 844 }, true));
  results.push(await captureUnknown());

  if (expectedRuntime === "online") {
    results.push(await captureRoundTrip());
  }

  const report = { baseUrl, expectedRuntime, captured_at: new Date().toISOString(), results };
  await writeFile(path.join(outputDirectory, "summary.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}

async function captureMap(name, viewport, fullPage = false) {
  return withPage(name, viewport, fullPage, async (page) => {
    await page.goto(`${baseUrl}/?view=market-map&mode=live-if-available&selected=AAPL`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 180_000 });
    await page.waitForTimeout(500);
    const observed = await page.evaluate(() => {
      const root = document.querySelector('[data-market-map-state="ready"]');
      const runtime = document.querySelector("[data-runtime-health-state]");
      return {
        runtimeReachable: runtime?.getAttribute("data-runtime-health-reachable"),
        rows: Number(root?.getAttribute("data-market-map-rows") || 0),
        snapshotStatus: root?.getAttribute("data-market-snapshot-status"),
        refreshStatus: root?.getAttribute("data-market-refresh-status"),
        refreshCalls: Number(root?.getAttribute("data-market-refresh-calls") || 0),
        tiles: document.querySelectorAll(".market-map-tile").length,
        snapshotText: document.querySelector(".market-map-universe-strip > div:last-child")?.textContent?.replace(/\s+/g, " ").trim(),
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      };
    });
    if (expectedRuntime === "offline") {
      assert(observed.runtimeReachable === "false", `${name}: expected controlled offline runtime`);
      assert(observed.rows > 0, `${name}: fixture fallback has no rows`);
    } else {
      assert(observed.runtimeReachable === "true", `${name}: runtime API is not reachable`);
      assert(observed.rows > 60, `${name}: materialized breadth regressed to ${observed.rows}`);
      assert(observed.tiles === observed.rows, `${name}: tile count ${observed.tiles}/${observed.rows}`);
      assert(observed.refreshStatus === "succeeded", `${name}: refresh status is ${observed.refreshStatus}`);
      if (expectedRuntime === "stale") {
        assert(observed.snapshotStatus === "stale", `${name}: expected stale snapshot, got ${observed.snapshotStatus}`);
      } else {
        assert(["fresh", "stale"].includes(observed.snapshotStatus), `${name}: snapshot status is ${observed.snapshotStatus}`);
      }
      assert(/refresh/.test(observed.snapshotText || ""), `${name}: refresh duration is not visible`);
    }
    assert(!observed.horizontalOverflow, `${name}: page-level horizontal overflow`);
    return observed;
  });
}

async function captureFinancials(name, viewport, fullPage = false) {
  return withPage(name, viewport, fullPage, async (page) => {
    await page.goto(`${baseUrl}/?view=asset&symbol=AAPL&assetClass=equity&interval=1d&range=3mo&mode=live-if-available&surface=financials&compare=SPY`, {
      waitUntil: "domcontentloaded",
      timeout: 180_000,
    });
    await page.waitForSelector('[data-product-view="asset-workspace"]', { timeout: 180_000 });
    await page.waitForSelector('[data-phase6a-sec-facts="true"]', { timeout: 180_000 });
    await page.waitForSelector('[data-phase6a-earnings-calendar="true"]', { timeout: 180_000 });
    await page.waitForTimeout(500);
    const observed = await page.evaluate(() => {
      const runtime = document.querySelector("[data-runtime-health-state]");
      const facts = document.querySelector('[data-phase6a-sec-facts="true"]');
      const earnings = document.querySelector('[data-phase6a-earnings-calendar="true"]');
      return {
        runtimeReachable: runtime?.getAttribute("data-runtime-health-reachable"),
        factCount: Number(facts?.getAttribute("data-sec-fact-count") || 0),
        factStatus: facts?.getAttribute("data-sec-fact-status"),
        earningsCount: Number(earnings?.getAttribute("data-earnings-row-count") || 0),
        earningsStatus: earnings?.getAttribute("data-earnings-status"),
        hasUnit: /USD|shares|USD\/shares/.test(facts?.textContent || ""),
        hasForm: /10-K|10-Q/.test(facts?.textContent || ""),
        horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      };
    });
    if (expectedRuntime === "offline") {
      assert(observed.runtimeReachable === "false", `${name}: expected controlled offline runtime`);
    } else {
      assert(observed.runtimeReachable === "true", `${name}: runtime API is not reachable`);
      assert(observed.factCount > 0, `${name}: no official SEC facts`);
      assert(observed.hasUnit && observed.hasForm, `${name}: SEC unit/form context missing`);
      assert(observed.earningsCount > 0 || observed.earningsStatus === "unavailable", `${name}: earnings truth is neither useful nor honest`);
    }
    assert(!observed.horizontalOverflow, `${name}: page-level horizontal overflow`);
    await page.locator('[data-phase6a-sec-facts="true"]').scrollIntoViewIfNeeded();
    await page.waitForTimeout(250);
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
    assert(observed.unknown, "unknown symbol state is not explicit");
    assert(!observed.leakedApple, "unknown symbol leaked AAPL identity");
    return observed;
  });
}

async function captureRoundTrip() {
  return withPage("market-map-aapl-round-trip", { width: 1600, height: 1000 }, false, async (page) => {
    const mapUrl = `${baseUrl}/?view=market-map&mode=live-if-available&query=AAPL&selected=AAPL&size=equal&color=relative_volume`;
    await page.goto(mapUrl, { waitUntil: "domcontentloaded", timeout: 180_000 });
    await page.waitForSelector('[data-market-map-state="ready"]', { timeout: 180_000 });
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
    assert(observed.query === "AAPL" && observed.selected === "AAPL", "round trip lost AAPL discovery state");
    assert(observed.size === "equal" && observed.color === "relative_volume", "round trip lost encoding state");
    return observed;
  });
}

async function withPage(name, viewport, fullPage, inspect) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = { console: [], page: [] };
  page.on("console", (message) => { if (message.type() === "error") errors.console.push(message.text()); });
  page.on("pageerror", (error) => errors.page.push(error.stack || error.message));
  try {
    const observed = await inspect(page);
    assert(errors.console.length === 0, `${name}: console errors ${errors.console.join(" | ")}`);
    assert(errors.page.length === 0, `${name}: page errors ${errors.page.join(" | ")}`);
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
