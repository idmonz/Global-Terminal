import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const summaryPath = path.join(repoRoot, "review_workspace", "phase6p_visual", "summary.json");
const summary = JSON.parse(await readFile(summaryPath, "utf8"));

assert(summary.evidence_version === "phase6p.visual.v1", "unexpected Phase 6P visual evidence version");
assert(summary.passed === true, "Phase 6P visual capture did not pass");
assert(summary.captures.anonymous.hostedFormVisible === true, "hosted sign-in proof is missing");
assert(summary.captures.anonymous.focus.visible === true, "hosted sign-in focus proof is missing");
assert(summary.captures.restored.continuityState === "hosted-ready", "hosted restore proof is missing");
assert(summary.captures.restored.unlabeledControls === 0, "hosted restore has unlabeled controls");
assert(summary.captures.conflict.continuityState === "conflict", "conflict proof is missing");
assert(summary.captures.conflict.conflictActions === 2, "conflict choices are incomplete");
assert(summary.captures.conflict.unlabeledControls === 0, "hosted conflict has unlabeled controls");
assert(summary.captures.offline.continuityState === "offline-read-only", "offline continuity proof is missing");
assert(summary.captures.offline.unlabeledControls === 0, "hosted offline state has unlabeled controls");
assert(summary.captures.mobile.rootWidth <= 390, "mobile account surface exceeds 390px");
assert(summary.captures.mobile.unlabeledControls === 0, "mobile account surface has unlabeled controls");

const screenshots = [];
for (const capture of Object.values(summary.captures)) collectScreenshots(capture, screenshots);
assert(screenshots.length >= 6, `expected at least 6 Phase 6P screenshots, found ${screenshots.length}`);
for (const file of screenshots) assert((await stat(file)).size > 12_000, `invalid screenshot: ${file}`);

const providerCalls = Object.values(summary.captures).reduce((total, capture) => total + Number(capture.providerRequestCount || 0), 0);
assert(providerCalls === 0, `visual fixture made ${providerCalls} direct provider requests`);
console.log(JSON.stringify({ ok: true, evidence_version: summary.evidence_version, screenshot_count: screenshots.length, provider_request_count: providerCalls }, null, 2));

function collectScreenshots(value, output) {
  if (!value || typeof value !== "object") return;
  if (typeof value.file === "string" && value.file.endsWith(".png")) output.push(value.file);
  for (const child of Object.values(value)) collectScreenshots(child, output);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
