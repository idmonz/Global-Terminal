import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const API_CONTRACT_VERSION = "phase_2b.v1";
const REQUIRED_FIELDS = [
  "contract_version",
  "payload_type",
  "generated_at",
  "data",
  "summary",
  "source_status",
  "unavailable",
  "errors",
  "caveats",
];

const FIXTURES = [
  ["product-parity.json", "product_parity_inventory"],
  ["market-intelligence.json", "market_intelligence"],
  ["equity-intelligence.json", "equity_intelligence"],
  ["financial-fundamentals.json", "financial_fundamentals"],
  ["options-quant.json", "options_quant"],
  ["portfolio-risk.json", "portfolio_risk"],
  ["research-memory.json", "research_memory"],
  ["daily-brief.json", "daily_brief"],
  ["screener-drilldown.json", "screener_drilldown"],
  ["market-map-screener.json", "market_map_screener"],
  ["crypto-intelligence.json", "crypto_intelligence"],
  ["symbol-directory.json", "symbol_directory"],
  ["symbol-workstation.json", "symbol_workstation"],
  ["analyst-workspace.json", "analyst_workspace"],
  ["watchlist-alert-manager.json", "watchlist_alert_manager"],
  ["hosted-scheduler-operations.json", "hosted_scheduler_operations"],
  ["analyst-workspace-catalog.json", "analyst_workspace"],
  ["manifest.json", "api_route_manifest"],
  ["war-room.json", "war_room"],
  ["war-room-map.json", "war_room_map"],
  ["war-room-map-replay.json", "war_room_map_replay"],
  ["map-news-event-fusion.json", "map_news_event_fusion"],
  ["news.json", "news_dashboard"],
  ["provider-health.json", "provider_health"],
  ["layers.json", "layer_runtime"],
  ["feeds.json", "feed_registry"],
  ["ai-providers.json", "ai_provider_status"],
  ["asset-universe.json", "asset_universe"],
  ["event-asset-graph.json", "event_asset_graph"],
  ["command-workspace.json", "command_workspace"],
  ["research-report.json", "research_report"],
];

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(scriptDirectory, "..");
const repositoryRoot = path.resolve(webRoot, "../..");
const fixtureDirectory = path.join(repositoryRoot, "static", "api-fixtures");
const issues = [];

for (const [filename, expectedPayloadType] of FIXTURES) {
  const fullPath = path.join(fixtureDirectory, filename);
  let envelope;

  try {
    envelope = JSON.parse(await readFile(fullPath, "utf8"));
  } catch (error) {
    issues.push(`${filename}: ${error instanceof Error ? error.message : String(error)}`);
    continue;
  }

  if (!isRecord(envelope)) {
    issues.push(`${filename}: root must be an object`);
    continue;
  }

  for (const field of REQUIRED_FIELDS) {
    if (!(field in envelope)) {
      issues.push(`${filename}: missing ${field}`);
    }
  }

  if (envelope.contract_version !== API_CONTRACT_VERSION) {
    issues.push(`${filename}: expected contract_version ${API_CONTRACT_VERSION}`);
  }

  if (envelope.payload_type !== expectedPayloadType) {
    issues.push(`${filename}: expected payload_type ${expectedPayloadType}`);
  }

  if (typeof envelope.generated_at !== "string" || envelope.generated_at.length === 0) {
    issues.push(`${filename}: generated_at must be a non-empty string`);
  }

  if (!isRecord(envelope.summary)) {
    issues.push(`${filename}: summary must be an object`);
  }

  for (const arrayField of ["source_status", "unavailable", "errors", "caveats"]) {
    if (!Array.isArray(envelope[arrayField])) {
      issues.push(`${filename}: ${arrayField} must be an array`);
    }
  }

  if (Array.isArray(envelope.caveats) && envelope.caveats.some((item) => typeof item !== "string")) {
    issues.push(`${filename}: caveats must contain strings only`);
  }
}

if (issues.length > 0) {
  console.error(`Fixture validation failed for ${fixtureDirectory}`);
  for (const issue of issues) {
    console.error(`- ${issue}`);
  }
  process.exit(1);
}

console.log(`Validated ${FIXTURES.length} phase_2b.v1 fixtures from ${fixtureDirectory}`);

function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
