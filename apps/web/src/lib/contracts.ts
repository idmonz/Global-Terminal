export const API_CONTRACT_VERSION = "phase_2b.v1";

export const REQUIRED_ENVELOPE_FIELDS = [
  "contract_version",
  "payload_type",
  "generated_at",
  "data",
  "summary",
  "source_status",
  "unavailable",
  "errors",
  "caveats",
] as const;

export type RequiredEnvelopeField = (typeof REQUIRED_ENVELOPE_FIELDS)[number];

export type FixtureKey =
  | "market-intelligence"
  | "product-parity"
  | "equity-intelligence"
  | "financial-fundamentals"
  | "options-quant"
  | "portfolio-risk"
  | "research-memory"
  | "daily-brief"
  | "attention-desk"
  | "screener-drilldown"
  | "market-map-screener"
  | "crypto-intelligence"
  | "symbol-directory"
  | "symbol-workstation"
  | "analyst-workspace"
  | "watchlist-desk"
  | "watchlist-alert-manager"
  | "hosted-scheduler-operations"
  | "manifest"
  | "war-room"
  | "war-room-map"
  | "war-room-map-replay"
  | "map-news-event-fusion"
  | "news"
  | "provider-health"
  | "layers"
  | "feeds"
  | "ai-providers"
  | "asset-universe"
  | "event-graph"
  | "command-workspace"
  | "research-report";

export type PayloadType =
  | "market_intelligence"
  | "product_parity_inventory"
  | "equity_intelligence"
  | "financial_fundamentals"
  | "options_quant"
  | "portfolio_risk"
  | "research_memory"
  | "daily_brief"
  | "attention_desk"
  | "screener_drilldown"
  | "market_map_screener"
  | "crypto_intelligence"
  | "symbol_directory"
  | "symbol_workstation"
  | "analyst_workspace"
  | "watchlist_desk"
  | "watchlist_alert_manager"
  | "hosted_scheduler_operations"
  | "api_route_manifest"
  | "runtime_health"
  | "war_room"
  | "war_room_map"
  | "war_room_map_replay"
  | "map_news_event_fusion"
  | "news_dashboard"
  | "provider_health"
  | "layer_runtime"
  | "feed_registry"
  | "ai_provider_status"
  | "asset_universe"
  | "event_asset_graph"
  | "command_workspace"
  | "research_report";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonRecord = Record<string, JsonValue>;

export type SourceStatusRow = Record<string, JsonValue>;
export type UnavailableRow = Record<string, JsonValue>;
export type ErrorRow = Record<string, JsonValue>;

export interface ContractEnvelope<TData = JsonValue> {
  contract_version: typeof API_CONTRACT_VERSION;
  payload_type: PayloadType;
  generated_at: string;
  data: TData;
  summary: JsonRecord;
  source_status: SourceStatusRow[];
  unavailable: UnavailableRow[];
  errors: ErrorRow[];
  caveats: string[];
}

export interface FixtureDefinition {
  key: FixtureKey;
  filename: string;
  label: string;
  shortLabel: string;
  payloadType: PayloadType;
  route: string;
}

export const FIXTURE_DEFINITIONS: FixtureDefinition[] = [
  {
    key: "market-intelligence",
    filename: "market-intelligence.json",
    label: "Market Intelligence",
    shortLabel: "Market",
    payloadType: "market_intelligence",
    route: "/api/market-intelligence",
  },
  {
    key: "attention-desk",
    filename: "attention-desk.json",
    label: "Unified Attention Desk",
    shortLabel: "Attention",
    payloadType: "attention_desk",
    route: "/api/attention-desk",
  },
  {
    key: "war-room-map",
    filename: "war-room-map.json",
    label: "War Map",
    shortLabel: "War Map",
    payloadType: "war_room_map",
    route: "/api/war-room-map",
  },
  {
    key: "war-room-map-replay",
    filename: "war-room-map-replay.json",
    label: "War Map Replay",
    shortLabel: "Replay",
    payloadType: "war_room_map_replay",
    route: "/api/war-room-map-replay",
  },
  {
    key: "map-news-event-fusion",
    filename: "map-news-event-fusion.json",
    label: "Map News Event Fusion",
    shortLabel: "Map Fusion",
    payloadType: "map_news_event_fusion",
    route: "/api/map-news-event-fusion",
  },
  {
    key: "equity-intelligence",
    filename: "equity-intelligence.json",
    label: "Equity Intelligence",
    shortLabel: "Equity",
    payloadType: "equity_intelligence",
    route: "/api/equity-intelligence",
  },
  {
    key: "financial-fundamentals",
    filename: "financial-fundamentals.json",
    label: "Financial / Fundamentals",
    shortLabel: "Financials",
    payloadType: "financial_fundamentals",
    route: "/api/financial-fundamentals",
  },
  {
    key: "options-quant",
    filename: "options-quant.json",
    label: "Options / Quant",
    shortLabel: "Options",
    payloadType: "options_quant",
    route: "/api/options-quant",
  },
  {
    key: "portfolio-risk",
    filename: "portfolio-risk.json",
    label: "Portfolio And Risk",
    shortLabel: "Portfolio",
    payloadType: "portfolio_risk",
    route: "/api/portfolio-risk",
  },
  {
    key: "research-memory",
    filename: "research-memory.json",
    label: "Research Memory",
    shortLabel: "Memory",
    payloadType: "research_memory",
    route: "/api/research-memory",
  },
  {
    key: "daily-brief",
    filename: "daily-brief.json",
    label: "Daily Brief",
    shortLabel: "Brief",
    payloadType: "daily_brief",
    route: "/api/daily-brief",
  },
  {
    key: "screener-drilldown",
    filename: "screener-drilldown.json",
    label: "Screener / Heatmap Drilldown",
    shortLabel: "Drilldown",
    payloadType: "screener_drilldown",
    route: "/api/screener-drilldown",
  },
  {
    key: "market-map-screener",
    filename: "market-map-screener.json",
    label: "Market Map And Screener",
    shortLabel: "Market Map",
    payloadType: "market_map_screener",
    route: "/api/market-map-snapshot",
  },
  {
    key: "crypto-intelligence",
    filename: "crypto-intelligence.json",
    label: "Crypto Intelligence",
    shortLabel: "Crypto",
    payloadType: "crypto_intelligence",
    route: "/api/crypto-intelligence",
  },
  {
    key: "symbol-directory",
    filename: "symbol-directory.json",
    label: "Universal Symbol Directory",
    shortLabel: "Symbols",
    payloadType: "symbol_directory",
    route: "/api/symbol-directory",
  },
  {
    key: "symbol-workstation",
    filename: "symbol-workstation.json",
    label: "Universal Symbol Workstation",
    shortLabel: "Asset",
    payloadType: "symbol_workstation",
    route: "/api/symbol-workstation",
  },
  {
    key: "analyst-workspace",
    filename: "analyst-workspace.json",
    label: "Synchronized Analyst Workspace",
    shortLabel: "Workspace",
    payloadType: "analyst_workspace",
    route: "/api/analyst-workspace",
  },
  {
    key: "watchlist-desk",
    filename: "watchlist-desk.json",
    label: "Watchlist Desk",
    shortLabel: "Watchlist",
    payloadType: "watchlist_desk",
    route: "/api/watchlist-desk",
  },
  {
    key: "watchlist-alert-manager",
    filename: "watchlist-alert-manager.json",
    label: "Watchlist Alert Manager",
    shortLabel: "Alerts",
    payloadType: "watchlist_alert_manager",
    route: "/api/account/alert-manager",
  },
  {
    key: "hosted-scheduler-operations",
    filename: "hosted-scheduler-operations.json",
    label: "Hosted Observation Schedule",
    shortLabel: "Schedule",
    payloadType: "hosted_scheduler_operations",
    route: "/api/account/alert-manager/scheduler",
  },
  {
    key: "product-parity",
    filename: "product-parity.json",
    label: "Product Parity Inventory",
    shortLabel: "Parity",
    payloadType: "product_parity_inventory",
    route: "/api/product-parity",
  },
  {
    key: "manifest",
    filename: "manifest.json",
    label: "Manifest / Backend Readiness",
    shortLabel: "Manifest",
    payloadType: "api_route_manifest",
    route: "/api",
  },
  {
    key: "war-room",
    filename: "war-room.json",
    label: "War Room Summary",
    shortLabel: "War Room",
    payloadType: "war_room",
    route: "/api/war-room",
  },
  {
    key: "news",
    filename: "news.json",
    label: "News Summary",
    shortLabel: "News",
    payloadType: "news_dashboard",
    route: "/api/news",
  },
  {
    key: "provider-health",
    filename: "provider-health.json",
    label: "Provider Health",
    shortLabel: "Providers",
    payloadType: "provider_health",
    route: "/api/provider-health",
  },
  {
    key: "layers",
    filename: "layers.json",
    label: "Layer Runtime",
    shortLabel: "Layers",
    payloadType: "layer_runtime",
    route: "/api/layers",
  },
  {
    key: "feeds",
    filename: "feeds.json",
    label: "Feed Registry",
    shortLabel: "Feeds",
    payloadType: "feed_registry",
    route: "/api/feeds",
  },
  {
    key: "ai-providers",
    filename: "ai-providers.json",
    label: "AI Provider Readiness",
    shortLabel: "AI",
    payloadType: "ai_provider_status",
    route: "/api/ai-providers",
  },
  {
    key: "asset-universe",
    filename: "asset-universe.json",
    label: "Asset Universe",
    shortLabel: "Assets",
    payloadType: "asset_universe",
    route: "/api/asset-universe",
  },
  {
    key: "event-graph",
    filename: "event-asset-graph.json",
    label: "Event-To-Asset Graph",
    shortLabel: "Graph",
    payloadType: "event_asset_graph",
    route: "/api/event-asset-graph",
  },
  {
    key: "research-report",
    filename: "research-report.json",
    label: "Research Report",
    shortLabel: "Report",
    payloadType: "research_report",
    route: "/api/research-report",
  },
  {
    key: "command-workspace",
    filename: "command-workspace.json",
    label: "Command Workspace",
    shortLabel: "Commands",
    payloadType: "command_workspace",
    route: "/api/command-workspace",
  },
];

export type RuntimeMode = "fixture" | "cache" | "live-if-available";

export const RUNTIME_MODES: RuntimeMode[] = ["fixture", "cache", "live-if-available"];

export function normalizeRuntimeMode(value: string | string[] | undefined): RuntimeMode {
  const raw = Array.isArray(value) ? value[0] : value;
  return RUNTIME_MODES.includes(raw as RuntimeMode) ? (raw as RuntimeMode) : "fixture";
}
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isJsonRecord(value: unknown): value is JsonRecord {
  return isRecord(value);
}

export function asRecordArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isRecord);
}

export function fixtureDefinitionForKey(key: string | undefined): FixtureDefinition {
  return FIXTURE_DEFINITIONS.find((definition) => definition.key === key) ?? FIXTURE_DEFINITIONS[0];
}
