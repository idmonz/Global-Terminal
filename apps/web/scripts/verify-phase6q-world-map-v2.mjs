import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDirectory, "../../..");
const summaryPath = path.join(repoRoot, "review_workspace", "phase6q_world_map_v2_visual", "summary.json");
const summary = JSON.parse(await readFile(summaryPath, "utf8"));

assert(summary.evidence_version === "phase6q.world-map.v2.visual.v1", "unexpected map visual evidence version");
assert(summary.passed === true, "map visual summary did not pass");
for (const key of ["desktop", "asia", "mobile", "tileFailure"]) {
  const capture = summary.captures?.[key];
  assert(capture, `missing ${key} capture`);
  assert(capture.horizontalOverflow === false, `${key} has horizontal overflow`);
  assert(capture.duplicateIds?.length === 0, `${key} has duplicate IDs`);
  assert(capture.unlabeledControls === 0, `${key} has unlabeled controls`);
  const file = capture.screenshot?.file;
  assert(typeof file === "string" && (await stat(file)).size >= 20_000, `${key} screenshot is missing or too small`);
}
assert(summary.captures.desktop.markerCount < summary.captures.desktop.eventCount, "desktop clusters are not proven");
assert(summary.captures.tileFailure.mapState === "fallback", "tile failure fallback is not proven");
console.log(JSON.stringify({ ok: true, evidence_version: summary.evidence_version, capture_count: 5 }, null, 2));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
