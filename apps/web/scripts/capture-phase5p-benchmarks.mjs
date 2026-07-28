import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const outputDirectory = path.join(repoRoot, "review_workspace", "phase5p_benchmark");
const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const targets = [
  { id: "nasa-worldview", url: "https://worldview.earthdata.nasa.gov/", terms: ["Worldview", "Layers", "Events"] },
  { id: "worldmonitor", url: "https://worldmonitor.app/", terms: ["World", "Monitor"] },
  { id: "openbb-workspace", url: "https://docs.openbb.co/workspace", terms: ["Workspace", "widget"] },
];

await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const evidence = [];

try {
  for (const target of targets) {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    try {
      const response = await page.goto(target.url, { waitUntil: "domcontentloaded", timeout: 120_000 });
      await page.waitForTimeout(8_000);
      const body = (await page.locator("body").innerText().catch(() => "")).slice(0, 120_000);
      const screenshot = path.join(outputDirectory, `${target.id}.png`);
      await page.screenshot({ path: screenshot, fullPage: false });
      evidence.push({
        id: target.id,
        requestedUrl: target.url,
        finalUrl: page.url(),
        status: response?.status() ?? null,
        title: await page.title(),
        matchedTerms: target.terms.filter((term) => body.toLowerCase().includes(term.toLowerCase())),
        screenshot,
        pageErrorCount: errors.length,
      });
    } catch (error) {
      evidence.push({ id: target.id, requestedUrl: target.url, finalUrl: page.url(), error: error instanceof Error ? error.message : String(error), pageErrorCount: errors.length });
    } finally {
      await page.close();
    }
  }
  console.log(JSON.stringify(evidence, null, 2));
} finally {
  await browser.close();
}
