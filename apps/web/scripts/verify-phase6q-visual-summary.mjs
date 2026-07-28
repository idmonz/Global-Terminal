import { access, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const summaryPath = path.join(repoRoot, "review_workspace", "phase6q_visual", "summary.json");
const summary = JSON.parse(await readFile(summaryPath, "utf8"));

assert(summary.evidence_version === "phase6q.visual.v1", "unexpected Phase 6Q evidence version");
assert(summary.passed === true, "Phase 6Q capture did not pass");
const captures = summary.captures || {};
assert(captures.initialHtml?.passed === true, "initial HTML evidence is absent");
assert(captures.initialHtml.bytes < captures.initialHtml.limit_bytes, "initial HTML exceeds its byte budget");
for (const key of [
  "safeDefault", "enableJourney", "running", "completed", "noDue", "idempotentReplay",
  "quotaBlocked", "providerOffline", "partialLkg", "leaseExpired", "recovered", "killed",
  "cleanup", "sessionExpired", "mobile",
]) {
  assert(captures[key], `missing ${key} capture`);
  assert(captures[key].horizontalOverflow === false, `${key} has horizontal overflow`);
  assert(captures[key].providerRequestCount === 0, `${key} made a market-provider request`);
  if (key === "sessionExpired") {
    assert((captures[key].errors || []).every((message) => message.includes("401 (Unauthorized)")), "sessionExpired contains unexpected browser errors");
  } else {
    assert((captures[key].errors || []).length === 0, `${key} contains browser errors`);
  }
}
assert(captures.safeDefault.hostedStatus === "hosted-unverified", "safe default was promoted incorrectly");
assert(captures.safeDefault.globalKillVisible === true, "safe default kill switch is not visible");
assert(captures.enableJourney.patchCount === 1, "enable journey did not make exactly one control mutation");
assert(captures.enableJourney.focus?.visible === true, "enable control lacks visible focus evidence");
assert(captures.enableJourney.unverifiedVisible === true, "enable journey falsely claims hosted verification");
assert(captures.partialLkg.latestRunStatus === "partial", "partial LKG evidence is absent");
assert(captures.running.latestRunStatus === "running", "running evidence is absent");
assert(captures.completed.latestRunStatus === "completed", "completed source evidence is absent");
assert(captures.quotaBlocked.latestRunStatus === "quota-blocked", "quota-blocked evidence is absent");
assert(captures.providerOffline.latestRunStatus === "provider-unavailable", "provider-offline evidence is absent");
assert(captures.leaseExpired.latestRunStatus === "failed", "lease-expiry evidence is absent");
assert(captures.recovered.latestRunStatus === "partial", "recovery evidence is absent");
assert(captures.cleanup.scheduleState === "deleted", "cleanup state is absent");
assert(captures.accountIsolation?.isolated === true, "Account A/B visual isolation is absent");
assert(captures.accountIsolation.accountA.scheduleCount === 1, "Account A schedule evidence is absent");
assert(captures.accountIsolation.accountB.scheduleCount === 0, "Account B isolation evidence is absent");
assert(captures.sessionExpired.expectedHttpStatus === 401, "session-expiry evidence is absent");
assert((captures.regressions?.routes || []).length === 6, "major product regression captures are incomplete");
assert(captures.mobile.rootWidth <= 390 && captures.mobile.panelWidth <= 390, "390px scheduler capture exceeds viewport");

const screenshots = [];
walk(captures, screenshots);
assert(screenshots.length >= 22, `expected at least 22 screenshots, received ${screenshots.length}`);
for (const file of screenshots) {
  await access(file);
  const metadata = await stat(file);
  assert(metadata.size > 10_000, `${file} is unexpectedly small`);
}

console.log(JSON.stringify({
  ok: true,
  evidence_version: summary.evidence_version,
  screenshot_count: screenshots.length,
  provider_request_count: Object.values(captures).reduce((total, row) => total + Number(row?.providerRequestCount || 0), 0),
  safe_default: captures.safeDefault.hostedStatus,
  focus_visible: captures.enableJourney.focus.visible,
  mobile_root_width: captures.mobile.rootWidth,
}, null, 2));

function walk(value, output) {
  if (!value || typeof value !== "object") return;
  if (typeof value.file === "string" && value.file.endsWith(".png")) output.push(value.file);
  for (const child of Object.values(value)) walk(child, output);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
