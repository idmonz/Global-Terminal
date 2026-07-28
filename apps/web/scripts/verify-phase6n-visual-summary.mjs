import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const summaryPath = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(repoRoot, "review_workspace", "phase6n_visual", "summary.json");
const report = JSON.parse(await readFile(summaryPath, "utf8"));

assert(report.evidence_version === "phase6n.visual.v1", "unexpected evidence version");
assert(report.passed === true, "visual harness did not declare a pass");

const captures = report.captures || {};
for (const key of ["journey", "mobile", "states", "offline", "drilldown", "account", "regressions"]) {
  assert(captures[key], `missing capture group: ${key}`);
}

assert(captures.journey.providerRequestCount === 0, "journey made a provider request");
assert(captures.journey.productNavWidth >= 160, "desktop ProductNav is narrower than 160px");
assert(captures.journey.focusVisible === true, "keyboard focus is not visibly styled");
assert(captures.journey.liveRegionCount >= 1, "status announcements lack an aria-live region");
assert(captures.mobile.providerRequestCount === 0, "mobile review made a provider request");
assert(captures.mobile.horizontalOverflow === false, "390px layout overflows horizontally");
assert(captures.mobile.firstRow?.top < 844, "first critical row is below the 390x844 first viewport");
assert(captures.offline.providerRequestCount === 0, "runtime-offline state made a provider request");
assert(captures.offline.expectedErrors?.length >= 1, "runtime-offline state did not retain its controlled transport failure");
assert(captures.drilldown.returned === true, "drilldown journey did not return to Attention");
assert(JSON.stringify(captures.drilldown.routes) === JSON.stringify(["News", "Brief", "Map", "Analyst"]), "four-surface drilldown matrix is incomplete");
assert(captures.account.available === true, "local Account A/B visual proof is unavailable");
assert(captures.account.isolated === true, "Account B isolation was not proved");
assert(captures.account.expectedErrors?.length >= 2, "account conflict/offline states did not retain both controlled HTTP failures");

for (const state of [
  "observation-run-no-due-work",
  "observation-run-quota-blocked",
  "observation-run-partial-lkg",
  "observation-run-cancelled",
  "observation-run-provider-offline",
  "observation-run-no-list",
]) {
  assert(captures.states[state], `missing operational state: ${state}`);
  assert(captures.states[state].providerRequestCount === 0, `${state} made a browser provider request`);
}

const requiredFiles = [
  "observation-run-progress-desktop.png",
  "observation-run-completed-desktop.png",
  "observation-run-mobile-critical-first.png",
  "observation-run-mobile-critical-first-tall.png",
  "observation-run-runtime-offline.png",
  "attention-account-a-reviewed.png",
  "attention-account-b-isolated.png",
  "attention-version-conflict.png",
  "attention-account-offline-local-retained.png",
  "observation-run-drilldown-news.png",
  "observation-run-drilldown-brief.png",
  "observation-run-drilldown-map.png",
  "observation-run-drilldown-analyst.png",
];
const screenshotPaths = collectScreenshotPaths(captures);
const screenshotsByName = new Map(screenshotPaths.map((file) => [path.basename(file), file]));
for (const name of requiredFiles) {
  const file = screenshotsByName.get(name);
  assert(file, `missing screenshot reference: ${name}`);
  const metadata = await stat(file);
  assert(metadata.size > 12_000, `${name} is unexpectedly small (${metadata.size} bytes)`);
}

for (const errors of collectNamedArrays(captures, "errors")) {
  assert(errors.length === 0, `browser/page errors recorded: ${errors.join(" | ")}`);
}
for (const count of collectNamedNumbers(captures, "providerRequestCount")) {
  assert(count === 0, `provider request count is ${count}`);
}

const result = {
  ok: true,
  evidence_version: report.evidence_version,
  screenshot_count: screenshotPaths.length,
  required_screenshot_count: requiredFiles.length,
  mobile_first_row_top: captures.mobile.firstRow.top,
  product_nav_width: captures.journey.productNavWidth,
  focus_visible: captures.journey.focusVisible,
  live_region_count: captures.journey.liveRegionCount,
  provider_request_count: 0,
};
console.log(JSON.stringify(result, null, 2));

function collectScreenshotPaths(value, output = []) {
  if (Array.isArray(value)) {
    for (const item of value) collectScreenshotPaths(item, output);
    return output;
  }
  if (!value || typeof value !== "object") return output;
  if (typeof value.file === "string" && value.file.endsWith(".png")) output.push(value.file);
  for (const item of Object.values(value)) collectScreenshotPaths(item, output);
  return [...new Set(output)];
}

function collectNamedArrays(value, key, output = []) {
  if (Array.isArray(value)) {
    for (const item of value) collectNamedArrays(item, key, output);
    return output;
  }
  if (!value || typeof value !== "object") return output;
  if (Array.isArray(value[key])) output.push(value[key]);
  for (const item of Object.values(value)) collectNamedArrays(item, key, output);
  return output;
}

function collectNamedNumbers(value, key, output = []) {
  if (Array.isArray(value)) {
    for (const item of value) collectNamedNumbers(item, key, output);
    return output;
  }
  if (!value || typeof value !== "object") return output;
  if (typeof value[key] === "number") output.push(value[key]);
  for (const item of Object.values(value)) collectNamedNumbers(item, key, output);
  return output;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
