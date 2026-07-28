import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const summaryPath = process.argv[2] ? path.resolve(process.argv[2]) : path.join(repoRoot, "review_workspace", "phase6o_visual", "summary.json");
const report = JSON.parse(await readFile(summaryPath, "utf8"));

assert(report.evidence_version === "phase6o.visual.v1", "unexpected evidence version");
assert(report.passed === true, "visual harness did not declare a pass");
const captures = report.captures || {};
for (const key of ["initialHtml", "journey", "mobile", "states", "conflict", "account", "drilldown"]) assert(captures[key], `missing capture group: ${key}`);

assert(captures.initialHtml.bytes < 100_000, "initial Alert Manager HTML exceeds 100KB");
assert(captures.journey.providerRequestCount === 0, "journey made a provider request");
assert(captures.journey.productNavWidth >= 160, "desktop ProductNav is narrower than 160px");
assert(captures.journey.focusVisible === true, "keyboard focus is not visibly styled");
assert(captures.journey.liveRegionCount >= 1, "status announcements lack an aria-live region");
assert(captures.mobile.providerRequestCount === 0, "mobile review made a provider request");
assert(captures.mobile.horizontalOverflow === false, "390px layout overflows horizontally");
assert(captures.mobile.firstTriggerTop < 844, "mobile trigger is below the first 390x844 viewport");
assert(captures.account.available === true && captures.account.isolated === true, "Account A/B visual isolation is not proved");
assert(captures.account.accountA.ruleCount === 2, "Account A rules are absent");
assert(captures.account.accountB.ruleCount === 0, "Account B can see Account A rules");
assert(captures.conflict.expectedErrors.some((row) => row.status === 409), "controlled optimistic conflict is absent");
assert(captures.drilldown.returned === true, "drilldown did not return to Alert Manager");
assert(JSON.stringify(captures.drilldown.routes) === JSON.stringify(["Analyst", "News", "Brief", "Map"]), "exact four-surface drilldown matrix is incomplete");

for (const state of ["alert-manager-lifecycle", "alert-manager-quota-blocked", "alert-manager-partial-lkg", "alert-manager-provider-unavailable", "alert-manager-worker-offline", "alert-manager-worker-restarted"]) {
  assert(captures.states[state], `missing visual state: ${state}`);
  assert(captures.states[state].providerRequestCount === 0, `${state} made a provider request`);
}

const requiredFiles = [
  "alert-manager-create-empty-desktop.png",
  "alert-manager-active-rule-desktop.png",
  "alert-manager-trigger-history-desktop.png",
  "alert-manager-mobile-390x844.png",
  "alert-manager-lifecycle.png",
  "alert-manager-quota-blocked.png",
  "alert-manager-partial-lkg.png",
  "alert-manager-provider-unavailable.png",
  "alert-manager-worker-offline.png",
  "alert-manager-worker-restarted.png",
  "alert-manager-version-conflict.png",
  "alert-manager-account-a.png",
  "alert-manager-account-b-isolated.png",
  "alert-manager-drilldown-analyst.png",
  "alert-manager-drilldown-news.png",
  "alert-manager-drilldown-brief.png",
  "alert-manager-drilldown-map.png",
];
const screenshotPaths = collectScreenshotPaths(captures);
const byName = new Map(screenshotPaths.map((file) => [path.basename(file), file]));
for (const name of requiredFiles) {
  const file = byName.get(name);
  assert(file, `missing screenshot reference: ${name}`);
  const minimumBytes = name === "alert-manager-account-b-isolated.png" ? 8_000 : 12_000;
  assert((await stat(file)).size > minimumBytes, `${name} is unexpectedly small`);
}
for (const errors of collectNamedArrays(captures, "errors")) assert(errors.length === 0, `browser/page errors recorded: ${errors.join(" | ")}`);
for (const count of collectNamedNumbers(captures, "providerRequestCount")) assert(count === 0, `provider request count is ${count}`);

console.log(JSON.stringify({
  ok: true,
  evidence_version: report.evidence_version,
  screenshot_count: screenshotPaths.length,
  required_screenshot_count: requiredFiles.length,
  initial_html_bytes: captures.initialHtml.bytes,
  product_nav_width: captures.journey.productNavWidth,
  focus_visible: captures.journey.focusVisible,
  live_region_count: captures.journey.liveRegionCount,
  provider_request_count: 0,
}, null, 2));

function collectScreenshotPaths(value, output = []) {
  if (Array.isArray(value)) { for (const item of value) collectScreenshotPaths(item, output); return output; }
  if (!value || typeof value !== "object") return output;
  if (typeof value.file === "string" && value.file.endsWith(".png")) output.push(value.file);
  for (const item of Object.values(value)) collectScreenshotPaths(item, output);
  return [...new Set(output)];
}

function collectNamedArrays(value, key, output = []) {
  if (Array.isArray(value)) { for (const item of value) collectNamedArrays(item, key, output); return output; }
  if (!value || typeof value !== "object") return output;
  if (Array.isArray(value[key])) output.push(value[key]);
  for (const item of Object.values(value)) collectNamedArrays(item, key, output);
  return output;
}

function collectNamedNumbers(value, key, output = []) {
  if (Array.isArray(value)) { for (const item of value) collectNamedNumbers(item, key, output); return output; }
  if (!value || typeof value !== "object") return output;
  if (typeof value[key] === "number") output.push(value[key]);
  for (const item of Object.values(value)) collectNamedNumbers(item, key, output);
  return output;
}

function assert(condition, message) { if (!condition) throw new Error(message); }
