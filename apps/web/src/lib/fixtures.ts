import { readFile } from "node:fs/promises";
import path from "node:path";

import {
  API_CONTRACT_VERSION,
  FIXTURE_DEFINITIONS,
  type ContractEnvelope,
  type FixtureDefinition,
  type FixtureKey,
  type RuntimeMode,
  REQUIRED_ENVELOPE_FIELDS,
  asRecordArray,
  isRecord,
} from "./contracts";

export interface RuntimeFetchState {
  mode: RuntimeMode;
  source: "static-fixture" | "runtime-api" | "runtime-fallback";
  baseUrl: string | null;
  requestedUrl: string | null;
  includeRuntime: boolean;
  warning: string | null;
}

export interface RuntimeRequestContext {
  symbol?: string;
  assetClass?: "equity" | "etf" | "crypto";
  timeframe?: string;
  interval?: string;
  range?: string;
  expiry?: string;
  portfolio?: string;
  period?: string;
  benchmark?: string;
  collection?: string;
  surface?: string;
  researchMode?: "demo" | "local";
  runtimeMode?: RuntimeMode;
  memoryType?: string;
  tag?: string;
  chartType?: "line" | "candlestick";
  panels?: string[];
  compare?: string;
  delivery?: string;
  layout?: string;
  panel?: string;
  origin?: string;
  originState?: string;
  change?: string;
  changeType?: string;
  list?: string;
  changeSeverity?: string;
  changeStatus?: string;
}

const RUNTIME_SUPPORTED_KEYS = new Set<FixtureKey>([
  "market-intelligence",
  "equity-intelligence",
  "financial-fundamentals",
  "options-quant",
  "portfolio-risk",
  "research-memory",
  "daily-brief",
  "attention-desk",
  "screener-drilldown",
  "market-map-screener",
  "crypto-intelligence",
  "symbol-directory",
  "symbol-workstation",
  "analyst-workspace",
  "watchlist-desk",
  "war-room-map",
  "map-news-event-fusion",
  "war-room",
  "news",
  "layers",
  "event-graph",
  "command-workspace",
]);
const SYMBOL_RUNTIME_KEYS = new Set<FixtureKey>([
  "equity-intelligence",
  "financial-fundamentals",
  "options-quant",
  "crypto-intelligence",
  "symbol-workstation",
  "analyst-workspace",
]);
export interface LoadedFixture {
  definition: FixtureDefinition;
  envelope: ContractEnvelope | null;
  issues: string[];
  runtime?: RuntimeFetchState;
}

export interface RuntimeHealthSnapshot {
  mode: RuntimeMode;
  source: "runtime-api" | "runtime-offline" | "fixture-mode";
  reachable: boolean;
  status: string;
  baseUrl: string | null;
  requestedUrl: string | null;
  routeCount: number | null;
  providerCount: number | null;
  unavailableProviderCount: number | null;
  generatedAt: string | null;
  launcherCommand: string;
  warning: string | null;
  envelope: ContractEnvelope | null;
}

const repositoryRoot = path.resolve(process.cwd(), "../..");
const fixtureDirectory = path.join(repositoryRoot, "static", "api-fixtures");

export function getFixtureDirectory(): string {
  return fixtureDirectory;
}

export async function loadAllFixtures(): Promise<LoadedFixture[]> {
  return Promise.all(FIXTURE_DEFINITIONS.map(loadFixture));
}

export async function loadStaticFixture(definition: FixtureDefinition): Promise<LoadedFixture> {
  return loadFixture(definition);
}

export async function loadCompactSymbolSummary(
  definition: FixtureDefinition,
  symbol: string,
): Promise<LoadedFixture> {
  const filename = path.join(fixtureDirectory, "symbol-workstation-summaries.json");
  try {
    const parsed = JSON.parse(await readFile(filename, "utf8")) as unknown;
    if (!isRecord(parsed) || !isRecord(parsed.data)) {
      throw new Error("compact summary catalog is malformed");
    }
    const entry = asRecordArray(parsed.data.summaries).find((candidate) => {
      if (!isRecord(candidate.data)) return false;
      const workstation = asRecordArray(candidate.data.workstations)[0];
      return isRecord(workstation.identity) && workstation.identity.symbol === symbol;
    });
    if (!entry) {
      return {
        definition,
        envelope: null,
        issues: [`No exact offline summary exists for ${symbol}; no fallback symbol was substituted.`],
      };
    }
    const issues = validateEnvelope(entry, definition);
    return {
      definition,
      envelope: issues.length ? null : entry as unknown as ContractEnvelope,
      issues,
    };
  } catch (error) {
    return {
      definition,
      envelope: null,
      issues: [
        `symbol-workstation-summaries.json: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ],
    };
  }
}

export async function loadCompactAnalystWorkspace(
  definition: FixtureDefinition,
  symbol: string,
  mode: RuntimeMode,
  requestContext: RuntimeRequestContext = {},
): Promise<LoadedFixture> {
  const filename = path.join(fixtureDirectory, "analyst-workspace-catalog.json");
  let fallback: LoadedFixture;
  try {
    const parsed = JSON.parse(await readFile(filename, "utf8")) as unknown;
    if (!isRecord(parsed) || !isRecord(parsed.data)) {
      throw new Error("compact analyst workspace catalog is malformed");
    }
    const entry = asRecordArray(parsed.data.workspaces).find((candidate) => {
      if (!isRecord(candidate.data) || !isRecord(candidate.data.identity)) return false;
      return candidate.data.identity.symbol === symbol;
    });
    if (!entry) {
      fallback = {
        definition,
        envelope: null,
        issues: [`No exact offline analyst workspace exists for ${symbol}; no fallback symbol was substituted.`],
      };
    } else {
      if (isRecord(entry.data) && isRecord(entry.data.context)) {
        entry.data.context.return_state = {
          origin: requestContext.origin,
          originState: requestContext.originState,
          list: requestContext.list,
          type: requestContext.changeType,
          severity: requestContext.changeSeverity,
          status: requestContext.changeStatus,
          change: requestContext.change,
          symbol,
          interval: requestContext.interval,
          range: requestContext.range,
          layout: requestContext.layout,
          panel: requestContext.panel,
        };
        if (requestContext.panel) entry.data.context.focused_panel = requestContext.panel;
        if (requestContext.layout) entry.data.context.layout_preset = requestContext.layout;
      }
      if (requestContext.change && isRecord(entry.data)) {
        const desk = JSON.parse(
          await readFile(path.join(fixtureDirectory, "watchlist-desk.json"), "utf8"),
        ) as unknown;
        const deskData = isRecord(desk) && isRecord(desk.data) ? desk.data : {};
        const inbox = isRecord(deskData.change_inbox) ? deskData.change_inbox : {};
        const selected = asRecordArray(inbox.changes).find(
          (row) => row.change_id === requestContext.change && row.symbol === symbol,
        );
        if (selected) {
          const mappedPanel = panelForChangeType(String(selected.change_type ?? ""));
          entry.data.change_context = {
            status: "exact",
            change_id: selected.change_id,
            symbol: selected.symbol,
            change_type: selected.change_type,
            field: selected.field,
            severity: selected.severity,
            before: selected.before,
            after: selected.after,
            observation: selected.observation,
            focused_panel: mappedPanel,
            source_url: null,
            caveat: "Deterministic saved fixture evidence; no current market observation is claimed.",
            data_gap: null,
          };
          if (isRecord(entry.data.context)) entry.data.context.focused_panel = mappedPanel;
        }
      }
      const issues = validateEnvelope(entry, definition);
      fallback = {
        definition,
        envelope: issues.length ? null : entry as unknown as ContractEnvelope,
        issues,
      };
    }
  } catch (error) {
    fallback = {
      definition,
      envelope: null,
      issues: [
        `analyst-workspace-catalog.json: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ],
    };
  }
  if (mode === "fixture") return fallback;
  return loadRuntimeFixture(
    definition,
    mode,
    fallback,
    { ...requestContext, symbol },
  );
}

export async function loadCompactAnalystPrimaryPanel(
  symbol: string,
): Promise<ContractEnvelope | null> {
  const filename = path.join(fixtureDirectory, "analyst-workspace-primary-panels.json");
  try {
    const parsed = JSON.parse(await readFile(filename, "utf8")) as unknown;
    if (!isRecord(parsed) || !isRecord(parsed.data)) return null;
    const entry = asRecordArray(parsed.data.primary_panels).find((candidate) => {
      if (!isRecord(candidate.data)) return false;
      const current = asRecordArray(candidate.data.workstations)[0];
      return isRecord(current.identity) && current.identity.symbol === symbol;
    });
    if (!entry || entry.payload_type !== "symbol_workstation") return null;
    return entry as unknown as ContractEnvelope;
  } catch {
    return null;
  }
}

function panelForChangeType(value: string): string {
  if (value === "event" || value === "news") return "catalysts";
  if (value === "fundamental") return "financials";
  if (value === "source-status") return "sources";
  return "chart-core";
}

export function findLoadedFixture(fixtures: LoadedFixture[], key: FixtureKey): LoadedFixture {
  return fixtures.find((fixture) => fixture.definition.key === key) ?? fixtures[0];
}

async function loadFixture(definition: FixtureDefinition): Promise<LoadedFixture> {
  const filename = path.join(fixtureDirectory, definition.filename);

  try {
    const raw = await readFile(filename, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    const issues = validateEnvelope(parsed, definition);

    return {
      definition,
      envelope: issues.length === 0 ? (parsed as ContractEnvelope) : null,
      issues,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      definition,
      envelope: null,
      issues: [`${definition.filename}: ${message}`],
    };
  }
}

function validateEnvelope(value: unknown, definition: FixtureDefinition): string[] {
  const issues: string[] = [];

  if (!isRecord(value)) {
    return [`${definition.filename}: fixture root must be an object`];
  }

  for (const field of REQUIRED_ENVELOPE_FIELDS) {
    if (!(field in value)) {
      issues.push(`${definition.filename}: missing ${field}`);
    }
  }

  if (value.contract_version !== API_CONTRACT_VERSION) {
    issues.push(`${definition.filename}: expected contract_version ${API_CONTRACT_VERSION}`);
  }

  if (value.payload_type !== definition.payloadType) {
    issues.push(`${definition.filename}: expected payload_type ${definition.payloadType}`);
  }

  if (typeof value.generated_at !== "string" || value.generated_at.length === 0) {
    issues.push(`${definition.filename}: generated_at must be a non-empty ISO string`);
  }

  if (!isRecord(value.summary)) {
    issues.push(`${definition.filename}: summary must be an object`);
  }

  for (const arrayField of ["source_status", "unavailable", "errors", "caveats"] as const) {
    if (!Array.isArray(value[arrayField])) {
      issues.push(`${definition.filename}: ${arrayField} must be an array`);
    }
  }

  if (Array.isArray(value.caveats) && value.caveats.some((item) => typeof item !== "string")) {
    issues.push(`${definition.filename}: caveats must contain strings only`);
  }

  return issues;
}

export function rowsForFixture(fixture: LoadedFixture): Record<string, unknown>[] {
  const envelope = fixture.envelope;
  if (!envelope) {
    return [];
  }

  if (Array.isArray(envelope.data)) {
    return asRecordArray(envelope.data);
  }

  if (!isRecord(envelope.data)) {
    return [];
  }

  const candidatesByFixture: Record<FixtureKey, string[]> = {
    "market-intelligence": ["market_tape", "risk_heat", "macro_context"],
    "product-parity": ["streamlit_pages", "missing_web_surfaces", "priority_migration_queue", "lib_engines"],
    "equity-intelligence": ["price_history", "scenario_matrix", "valuation_quality", "news_events"],
    "financial-fundamentals": ["statement_metrics", "valuation_quality", "source_register"],
    "options-quant": ["chain_rows", "iv_smile", "greeks_rows", "scenario_rows", "provider_capabilities"],
    "portfolio-risk": ["holdings", "stress_tests", "source_register"],
    "research-memory": ["items", "watchlists", "reports", "source_history"],
    "daily-brief": ["claims", "sections", "source_register"],
    "attention-desk": ["items", "all_items", "source_register"],
    "screener-drilldown": ["drilldown_tiles", "sector_summaries", "source_register"],
    "market-map-screener": ["instruments", "source_register", "universe_contract"],
    "crypto-intelligence": ["derivatives_timeseries", "scenario_matrix", "liquidation_pressure_proxy"],
    "symbol-directory": ["identities", "provider_capabilities", "source_register"],
    "symbol-workstation": ["workstations", "capabilities", "source_register"],
    "analyst-workspace": ["panels", "source_register", "actions"],
    "watchlist-desk": ["items", "collections"],
    "watchlist-alert-manager": ["rules", "triggers", "evaluations"],
    "hosted-scheduler-operations": ["schedules", "runs", "audit"],
    manifest: [],
    "war-room": ["events", "event_timeline", "layer_runtime_status", "provider_health_ledger"],
    "war-room-map": ["markers", "layers", "provider_requirements", "timeline_filters", "compare_windows"],
    "war-room-map-replay": ["snapshots"],
    "map-news-event-fusion": ["markers", "related_news", "event_links", "heatmap_context", "layer_health"],
    news: ["high_severity_feed", "event_rows", "normalized_news", "impact_matrix"],
    "provider-health": [],
    layers: ["layers"],
    feeds: [],
    "ai-providers": [],
    "asset-universe": ["asset_classes", "command_asset_matrix"],
    "event-graph": ["nodes", "edges", "command_suggestions", "clusters"],
    "command-workspace": ["commands", "command_results", "contexts", "provider_requirements"],
    "research-report": ["sections", "scenario_matrix", "source_register"],
  };

  for (const key of candidatesByFixture[fixture.definition.key]) {
    const rows = asRecordArray(envelope.data[key]);
    if (rows.length > 0) {
      return rows;
    }
  }

  return [];
}

export function sourceRowsForFixtures(fixtures: LoadedFixture[]): Record<string, unknown>[] {
  return fixtures.flatMap((fixture) => (fixture.envelope ? asRecordArray(fixture.envelope.source_status) : []));
}

export function statusCounts(rows: Record<string, unknown>[]): Record<string, number> {
  return rows.reduce<Record<string, number>>((counts, row) => {
    const status = String(row.source_status ?? row.status ?? row.availability ?? "unknown");
    counts[status] = (counts[status] ?? 0) + 1;
    return counts;
  }, {});
}

export async function loadRuntimeFixture(
  definition: FixtureDefinition,
  mode: RuntimeMode,
  fallback: LoadedFixture,
  requestContext: RuntimeRequestContext = {},
): Promise<LoadedFixture> {
  if (mode === "fixture") {
    return {
      ...fallback,
      runtime: {
        mode,
        source: "static-fixture",
        baseUrl: null,
        requestedUrl: null,
        includeRuntime: false,
        warning: null,
      },
    };
  }

  if (!RUNTIME_SUPPORTED_KEYS.has(definition.key)) {
    const warning = `${definition.label}: ${mode} mode is not enabled for this route yet; static fixture fallback used.`;
    return fallbackWithRuntimeWarning(fallback, mode, null, null, mode === "live-if-available", warning);
  }

  const baseUrl = runtimeApiBaseUrl();
  const includeRuntime = mode === "live-if-available";

  if (!baseUrl) {
    const warning = `${definition.label}: ${mode} mode requested, but GLOBAL_TERMINAL_API_BASE_URL is not configured; static fixture fallback used.`;
    return fallbackWithRuntimeWarning(fallback, mode, null, null, includeRuntime, warning);
  }

  const requestedUrl = runtimeRequestUrl(baseUrl, definition, includeRuntime, requestContext);

  try {
    const response = await fetch(requestedUrl, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      const warning = `${definition.label}: runtime API returned HTTP ${response.status}; static fixture fallback used.`;
      return fallbackWithRuntimeWarning(fallback, mode, baseUrl, requestedUrl, includeRuntime, warning);
    }

    const parsed = (await response.json()) as unknown;
    const issues = validateEnvelope(parsed, definition);

    if (issues.length > 0) {
      const warning = `${definition.label}: runtime API payload failed contract validation; static fixture fallback used. ${issues.join(" ")}`;
      return fallbackWithRuntimeWarning(fallback, mode, baseUrl, requestedUrl, includeRuntime, warning);
    }

    return {
      definition,
      envelope: parsed as ContractEnvelope,
      issues: [],
      runtime: {
        mode,
        source: "runtime-api",
        baseUrl,
        requestedUrl,
        includeRuntime,
        warning: null,
      },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const warning = `${definition.label}: runtime API fetch failed (${message}); static fixture fallback used.`;
    return fallbackWithRuntimeWarning(fallback, mode, baseUrl, requestedUrl, includeRuntime, warning);
  }
}

export async function loadRuntimeHealth(mode: RuntimeMode): Promise<RuntimeHealthSnapshot> {
  const launcherCommand = "python scripts/start_local_product.py";
  if (mode === "fixture") {
    return {
      mode,
      source: "fixture-mode",
      reachable: false,
      status: "fixture-mode",
      baseUrl: null,
      requestedUrl: null,
      routeCount: null,
      providerCount: null,
      unavailableProviderCount: null,
      generatedAt: null,
      launcherCommand,
      warning: "Fixture mode is deterministic and does not require the local FastAPI runtime.",
      envelope: null,
    };
  }

  const baseUrl = runtimeApiBaseUrl();
  if (!baseUrl) {
    return {
      mode,
      source: "runtime-offline",
      reachable: false,
      status: "missing-api-base-url",
      baseUrl: null,
      requestedUrl: null,
      routeCount: null,
      providerCount: null,
      unavailableProviderCount: null,
      generatedAt: null,
      launcherCommand,
      warning: "GLOBAL_TERMINAL_API_BASE_URL is not configured; static fixtures remain the only source.",
      envelope: null,
    };
  }

  const requestedUrl = new URL("/api/runtime-health", `${baseUrl}/`).toString();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1600);

  try {
    const response = await fetch(requestedUrl, {
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      return runtimeHealthOffline(mode, baseUrl, requestedUrl, launcherCommand, `Runtime health returned HTTP ${response.status}.`);
    }

    const parsed = (await response.json()) as unknown;
    const issues = validateRuntimeHealthEnvelope(parsed);
    if (issues.length > 0) {
      return runtimeHealthOffline(mode, baseUrl, requestedUrl, launcherCommand, `Runtime health contract failed validation: ${issues.join(" ")}`);
    }

    const envelope = parsed as ContractEnvelope;
    const summary = isRecord(envelope.summary) ? envelope.summary : {};
    return {
      mode,
      source: "runtime-api",
      reachable: true,
      status: stringValue(summary.runtime_status, "api-reachable"),
      baseUrl,
      requestedUrl,
      routeCount: numberValue(summary.route_count),
      providerCount: numberValue(summary.provider_count),
      unavailableProviderCount: numberValue(summary.unavailable_provider_count),
      generatedAt: envelope.generated_at,
      launcherCommand: stringValue(summary.launcher_command, launcherCommand),
      warning: null,
      envelope,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return runtimeHealthOffline(mode, baseUrl, requestedUrl, launcherCommand, `Runtime health fetch failed (${message}).`);
  } finally {
    clearTimeout(timeout);
  }
}

function validateRuntimeHealthEnvelope(value: unknown): string[] {
  const issues: string[] = [];
  if (!isRecord(value)) {
    return ["runtime health response must be an object"];
  }
  for (const field of REQUIRED_ENVELOPE_FIELDS) {
    if (!(field in value)) {
      issues.push(`missing ${field}`);
    }
  }
  if (value.contract_version !== API_CONTRACT_VERSION) {
    issues.push(`expected contract_version ${API_CONTRACT_VERSION}`);
  }
  if (value.payload_type !== "runtime_health") {
    issues.push("expected payload_type runtime_health");
  }
  return issues;
}

function runtimeHealthOffline(
  mode: RuntimeMode,
  baseUrl: string | null,
  requestedUrl: string | null,
  launcherCommand: string,
  warning: string,
): RuntimeHealthSnapshot {
  return {
    mode,
    source: "runtime-offline",
    reachable: false,
    status: "runtime-api-offline",
    baseUrl,
    requestedUrl,
    routeCount: null,
    providerCount: null,
    unavailableProviderCount: null,
    generatedAt: null,
    launcherCommand,
    warning: `${warning} Start the local runtime with ${launcherCommand}.`,
    envelope: null,
  };
}

function stringValue(value: unknown, fallback = "unknown"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function numberValue(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function runtimeApiBaseUrl(): string | null {
  const raw = process.env.GLOBAL_TERMINAL_API_BASE_URL ?? process.env.NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL;
  return (raw?.trim() || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

function runtimeRequestUrl(
  baseUrl: string,
  definition: FixtureDefinition,
  includeRuntime: boolean,
  requestContext: RuntimeRequestContext,
): string {
  const route = definition.key === "symbol-workstation"
    && requestContext.delivery
    && requestContext.symbol
    ? requestContext.delivery === "summary"
      ? `${definition.route}/${encodeURIComponent(requestContext.symbol)}/summary`
      : `${definition.route}/${encodeURIComponent(requestContext.symbol)}/panels/${encodeURIComponent(requestContext.delivery)}`
    : definition.key === "analyst-workspace" && requestContext.symbol
      ? `${definition.route}/${encodeURIComponent(requestContext.symbol)}`
      : definition.route;
  const url = new URL(route, `${baseUrl}/`);
  if (definition.route !== "/api") {
    url.searchParams.set("include_runtime", includeRuntime ? "true" : "false");
  }
  if (SYMBOL_RUNTIME_KEYS.has(definition.key) && requestContext.symbol) {
    url.searchParams.set("symbol", requestContext.symbol);
  }
  if (definition.key === "symbol-workstation") {
    if (requestContext.assetClass) url.searchParams.set("asset_class", requestContext.assetClass);
    url.searchParams.set("interval", requestContext.interval || requestContext.timeframe || "1d");
    url.searchParams.set("range", requestContext.range || "3mo");
    url.searchParams.set("runtime_mode", requestContext.runtimeMode || (includeRuntime ? "live-if-available" : "cache"));
    url.searchParams.set("chart_type", requestContext.chartType || "candlestick");
    if (requestContext.panels?.length) url.searchParams.set("panels", requestContext.panels.join(","));
    if (requestContext.compare) url.searchParams.set("compare", requestContext.compare);
  }
  if (definition.key === "analyst-workspace") {
    if (requestContext.assetClass) url.searchParams.set("asset_class", requestContext.assetClass);
    url.searchParams.set("interval", requestContext.interval || requestContext.timeframe || "1d");
    url.searchParams.set("range", requestContext.range || "3mo");
    url.searchParams.set("runtime_mode", requestContext.runtimeMode || (includeRuntime ? "live-if-available" : "cache"));
    if (requestContext.compare) url.searchParams.set("compare", requestContext.compare);
    if (requestContext.layout) url.searchParams.set("layout", requestContext.layout);
    if (requestContext.panel) url.searchParams.set("panel", requestContext.panel);
    if (requestContext.origin) url.searchParams.set("origin", requestContext.origin);
    if (requestContext.originState) url.searchParams.set("originState", requestContext.originState);
    if (requestContext.list) url.searchParams.set("list", requestContext.list);
    if (requestContext.change) url.searchParams.set("change", requestContext.change);
    if (requestContext.changeType) url.searchParams.set("change_type", requestContext.changeType);
    if (requestContext.changeSeverity) url.searchParams.set("severity", requestContext.changeSeverity);
    if (requestContext.changeStatus) url.searchParams.set("status", requestContext.changeStatus);
  }
  if (definition.key === "watchlist-desk") {
    url.searchParams.delete("include_runtime");
    url.searchParams.set("mode", requestContext.researchMode === "local" ? "local" : "fixture");
    url.searchParams.set("list_id", requestContext.collection || "primary");
    if (requestContext.symbol) url.searchParams.set("selected", requestContext.symbol);
  }
  if (definition.key === "options-quant" && requestContext.expiry) {
    url.searchParams.set("expiry", requestContext.expiry);
  }
  if (definition.key === "portfolio-risk") {
    url.searchParams.set("portfolio", requestContext.portfolio || "demo-core");
    url.searchParams.set("period", requestContext.period || "1y");
    url.searchParams.set("benchmark", requestContext.benchmark || "SPY");
  }
  if (definition.key === "research-memory") {
    url.searchParams.delete("include_runtime");
    url.searchParams.set("mode", requestContext.researchMode || "demo");
    url.searchParams.set("collection", requestContext.collection || (requestContext.researchMode === "local" ? "local-research" : "demo-research"));
    url.searchParams.set("surface", requestContext.surface || "inbox");
    if (requestContext.memoryType) {
      url.searchParams.set("memory_type", requestContext.memoryType);
    }
    if (requestContext.tag) {
      url.searchParams.set("tag", requestContext.tag);
    }
  }
  if (definition.key === "daily-brief") {
    url.searchParams.delete("include_runtime");
    url.searchParams.set("mode", includeRuntime ? "live-if-available" : "cache");
    url.searchParams.set("period", requestContext.period || "morning");
  }
  if (definition.key === "attention-desk") {
    url.searchParams.delete("include_runtime");
    url.searchParams.set("mode", requestContext.researchMode === "demo" ? "fixture" : "cache");
  }
  return url.toString();
}

function fallbackWithRuntimeWarning(
  fallback: LoadedFixture,
  mode: RuntimeMode,
  baseUrl: string | null,
  requestedUrl: string | null,
  includeRuntime: boolean,
  warning: string,
): LoadedFixture {
  return {
    ...fallback,
    issues: [...fallback.issues, warning],
    runtime: {
      mode,
      source: "runtime-fallback",
      baseUrl,
      requestedUrl,
      includeRuntime,
      warning,
    },
  };
}
