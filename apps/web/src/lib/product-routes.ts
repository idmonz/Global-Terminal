import type { FixtureKey, RuntimeMode } from "./contracts";

export type ProductAssetClass = "equity" | "etf" | "crypto";
export type AssetSurface = "overview" | "chart" | "financials" | "catalysts" | "news" | "sources" | "options";
export type AssetChartType = "line" | "candlestick";

export interface ProductAssetContext {
  symbol: string;
  assetClass: ProductAssetClass;
  interval: string;
  range: string;
  timeframe: string;
  surface: AssetSurface;
  chartType: AssetChartType;
  panels: string[];
  compare: string;
  originView: string;
  originState: string;
  fixtureKey: FixtureKey;
  supported: boolean;
  reason: string | null;
}

export const PRODUCT_INTERVALS = ["15m", "1h", "4h", "1d"] as const;
export const PRODUCT_RANGES = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"] as const;
export const PRODUCT_TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"] as const;
export const PRODUCT_PANELS = ["trend", "momentum", "risk", "comparison", "financials", "news", "asset", "sources"] as const;

const EQUITY_SYMBOLS = [
  "MSFT", "AAPL", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B", "LLY", "AVGO",
  "JPM", "XOM", "UNH", "V", "PG", "MA", "COST", "HD", "MRK", "ABBV", "CVX", "CRM",
  "AMD", "NFLX", "KO", "PEP", "ADBE", "WMT", "BAC", "TMO", "CSCO", "ACN", "MCD", "LIN",
  "ABT", "DIS", "INTU", "WFC", "QCOM", "TXN", "AMAT", "NEE", "GE", "CAT", "BA", "GS",
  "BLK", "SPGI", "LOW", "HON", "AMGN", "PFE", "COP", "SLB", "DE", "UBER", "PANW", "NOW",
  "LRCX", "MU",
];
const ETF_SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "VTI", "TLT", "GLD", "SLV", "USO", "IBIT"];
const CRYPTO_SYMBOLS = [
  "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT",
  "AVAXUSDT", "LINKUSDT", "DOTUSDT", "TRXUSDT", "LTCUSDT", "BCHUSDT", "UNIUSDT",
  "ATOMUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT",
];

const SUPPORTED_SYMBOLS: Record<ProductAssetClass, Set<string>> = {
  equity: new Set(EQUITY_SYMBOLS),
  etf: new Set(ETF_SYMBOLS),
  crypto: new Set(CRYPTO_SYMBOLS),
};
const SAFE_DYNAMIC_SYMBOL = /^[A-Z0-9][A-Z0-9=._-]{0,23}$/;

export function resolveProductAssetContext(
  rawSymbol: string | undefined,
  rawAssetClass: string | undefined,
  rawIntervalOrTimeframe: string | undefined,
  rawRangeOrSurface: string | undefined,
  rawSurface?: string | undefined,
  rawChartType?: string | undefined,
  rawPanels?: string | undefined,
  rawCompare?: string | undefined,
  rawOriginView?: string | undefined,
  rawOriginState?: string | undefined,
): ProductAssetContext {
  const symbol = normalizeSymbol(rawSymbol);
  const assetClass = normalizeAssetClass(rawAssetClass, symbol);
  const legacyCall = rawSurface === undefined && isSurface(rawRangeOrSurface);
  const interval = normalizeInterval(rawIntervalOrTimeframe);
  const range = legacyCall ? "3mo" : normalizeRange(rawRangeOrSurface);
  const surface = normalizeSurface(legacyCall ? rawRangeOrSurface : rawSurface, assetClass);
  const supported = isRuntimeEligibleSymbol(symbol, assetClass);
  const chartType = rawChartType?.toLowerCase() === "line" ? "line" : "candlestick";
  const panels = normalizePanels(rawPanels);
  const compare = normalizeCompare(rawCompare, symbol);
  const originView = ["market-map", "war-room-map", "watchlist-desk", "attention-desk"].includes(rawOriginView ?? "") ? rawOriginView as "market-map" | "war-room-map" | "watchlist-desk" | "attention-desk" : "";
  const originState = originView === "market-map"
    ? normalizeMarketMapOriginState(rawOriginState)
    : originView === "war-room-map"
      ? normalizeWarMapOriginState(rawOriginState)
      : originView === "watchlist-desk"
        ? normalizeWatchlistOriginState(rawOriginState)
      : originView === "attention-desk"
        ? normalizeAttentionOriginState(rawOriginState)
      : "";

  return {
    symbol,
    assetClass,
    interval,
    range,
    timeframe: displayTimeframe(interval, range),
    surface,
    chartType,
    panels,
    compare,
    originView,
    originState,
    fixtureKey: "symbol-workstation",
    supported,
    reason: supported ? null : "invalid-or-unsupported-symbol",
  };
}

export function canonicalAssetHref(
  symbol: string,
  assetClass: ProductAssetClass,
  interval = "1d",
  mode: RuntimeMode = "cache",
  surface: AssetSurface = "overview",
  range = "3mo",
  state: { chartType?: AssetChartType; panels?: string[] | string; compare?: string; originView?: string; originState?: string } = {},
): string {
  const params = new URLSearchParams({
    view: "asset",
    symbol: normalizeSymbol(symbol),
    assetClass,
    interval: normalizeInterval(interval),
    range: normalizeRange(range),
    surface: normalizeSurface(surface, assetClass),
    mode,
  });
  params.set("chartType", state.chartType === "line" ? "line" : "candlestick");
  const panels = normalizePanels(Array.isArray(state.panels) ? state.panels.join(",") : state.panels);
  params.set("panels", panels.join(","));
  const compare = normalizeCompare(state.compare, normalizeSymbol(symbol));
  if (compare) params.set("compare", compare);
  if (state.originView === "market-map" || state.originView === "war-room-map" || state.originView === "watchlist-desk" || state.originView === "attention-desk") {
    params.set("origin", state.originView);
    const originState = state.originView === "market-map"
      ? normalizeMarketMapOriginState(state.originState)
      : state.originView === "war-room-map"
        ? normalizeWarMapOriginState(state.originState)
      : state.originView === "attention-desk"
        ? normalizeAttentionOriginState(state.originState)
        : normalizeWatchlistOriginState(state.originState);
    if (originState) params.set("originState", originState);
  }
  return `/?${params.toString()}`;
}

export function canonicalAnalystWorkspaceHref(
  symbol: string,
  assetClass: ProductAssetClass,
  mode: RuntimeMode,
  state: {
    interval?: string;
    range?: string;
    panel?: string;
    layout?: string;
    list?: string;
    changeType?: string;
    changeSeverity?: string;
    changeStatus?: string;
    change?: string;
  } = {},
): string {
  const normalizedSymbol = normalizeSymbol(symbol);
  const panelMap: Record<string, string> = {
    chart: "chart-core",
    overview: "chart-core",
    price: "chart-core",
    performance: "chart-core",
    financials: "financials",
    fundamental: "financials",
    catalysts: "catalysts",
    event: "catalysts",
    news: "catalysts",
    sources: "sources",
    "source-status": "sources",
  };
  const requestedPanel = (state.panel ?? "chart-core").toLowerCase();
  const panel = panelMap[requestedPanel] ?? (
    ["chart-core", "technicals", "comparison"].includes(requestedPanel)
      ? requestedPanel
      : "chart-core"
  );
  const params = new URLSearchParams({
    view: "analyst-workspace",
    symbol: normalizedSymbol,
    assetClass,
    interval: normalizeInterval(state.interval),
    range: normalizeRange(state.range),
    mode,
    panel,
    layout: ["research", "chart-focus", "events-evidence"].includes(state.layout ?? "")
      ? state.layout as string
      : "research",
    origin: "watchlist-desk",
  });
  const safeFields: [string, string | undefined, RegExp][] = [
    ["list", state.list, /^[a-z0-9][a-z0-9-]{0,47}$/],
    ["changeType", state.changeType, /^(all|price|performance|fundamental|event|news|source-status)$/],
    ["changeSeverity", state.changeSeverity, /^(all|critical|material|info)$/],
    ["changeStatus", state.changeStatus, /^(all|unacknowledged|acknowledged)$/],
    ["change", state.change, /^change_[a-f0-9]{16}$/],
  ];
  safeFields.forEach(([key, value, pattern]) => {
    if (value && pattern.test(value)) params.set(key, value);
  });
  return `/?${params.toString()}`;
}

export function isSupportedProductSymbol(symbol: string, assetClass: ProductAssetClass): boolean {
  return isRuntimeEligibleSymbol(normalizeSymbol(symbol), assetClass);
}

export function isRuntimeEligibleSymbol(symbol: string, assetClass: ProductAssetClass): boolean {
  if (!SAFE_DYNAMIC_SYMBOL.test(symbol)) return false;
  if (assetClass === "crypto" || assetClass === "etf") {
    return SUPPORTED_SYMBOLS[assetClass].has(symbol);
  }
  return true;
}

export function sanitizeWarMapSearchParams(input: URLSearchParams): URLSearchParams {
  const output = new URLSearchParams({ view: "war-room-map" });
  const mode = input.get("mode");
  if (["fixture", "cache", "live-if-available"].includes(mode ?? "")) output.set("mode", mode as string);
  const layers = (input.get("layers") ?? "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => /^[a-z0-9_-]{1,48}$/.test(item))
    .slice(0, 16);
  if (layers.length) output.set("layers", layers.join(","));
  for (const key of ["time", "compareTo"] as const) {
    const value = input.get(key) ?? "";
    if (/^mapsnap_[a-f0-9]{20}$/.test(value)) output.set(key, value);
  }
  const selected = input.get("selected") ?? "";
  if (/^[A-Za-z0-9:._-]{1,100}$/.test(selected)) output.set("selected", selected);
  const severity = input.get("severity") ?? "";
  if (["all", "critical", "high", "elevated", "watch", "low"].includes(severity)) output.set("severity", severity);
  const region = input.get("region") ?? "";
  if (/^[A-Za-z0-9 _/-]{1,48}$/.test(region)) output.set("region", region);
  const mapRegion = input.get("mapRegion") ?? "";
  if (["global", "americas", "europe", "mena", "asia", "pacific", "events"].includes(mapRegion)) output.set("mapRegion", mapRegion);
  const lat = Number(input.get("lat"));
  const lon = Number(input.get("lon"));
  const zoom = Number(input.get("zoom"));
  if (Number.isFinite(lat) && lat >= -85 && lat <= 85) output.set("lat", lat.toFixed(3));
  if (Number.isFinite(lon) && lon >= -180 && lon <= 180) output.set("lon", lon.toFixed(3));
  if (Number.isFinite(zoom) && zoom >= 2 && zoom <= 10) output.set("zoom", zoom.toFixed(2));
  if (input.get("mapMode") === "fallback") output.set("mapMode", "fallback");
  return output;
}

export function normalizeAttentionOriginState(value: string | undefined): string {
  const input = new URLSearchParams(value ?? "");
  const output = new URLSearchParams({ view: "attention-desk" });
  const mode = input.get("mode");
  if (["fixture", "cache"].includes(mode ?? "")) output.set("mode", mode as string);
  const bounded: [string, string[], RegExp | null][] = [
    ["review", ["needs-review", "all", "reviewed", "acknowledged"], null],
    ["attentionSeverity", ["all", "critical", "high", "material", "info"], null],
    ["attentionKind", [], /^(all|market-change|new-evidence|source-degradation|stale-evidence|resolved)$/],
  ];
  bounded.forEach(([key, allowed, pattern]) => {
    const candidate = input.get(key) ?? "";
    if ((allowed.length && allowed.includes(candidate)) || pattern?.test(candidate)) output.set(key, candidate);
  });
  for (const key of ["attentionSource", "attentionRegion"] as const) {
    const candidate = input.get(key) ?? "";
    if (/^[A-Za-z0-9 ._:/-]{1,80}$/.test(candidate)) output.set(key, candidate);
  }
  return output.toString();
}

function normalizeSymbol(value: string | undefined): string {
  const normalized = (value ?? "").toUpperCase().replace(/[^A-Z0-9=._-]/g, "").slice(0, 24);
  return normalized || "AAPL";
}

function normalizeAssetClass(value: string | undefined, symbol: string): ProductAssetClass {
  const requested = value?.toLowerCase();
  if (requested === "crypto" || requested === "etf" || requested === "equity") return requested;
  if (symbol.endsWith("USDT")) return "crypto";
  if (SUPPORTED_SYMBOLS.etf.has(symbol)) return "etf";
  return "equity";
}

function normalizeInterval(value: string | undefined): string {
  const current = (value ?? "1d").toLowerCase();
  const legacy: Record<string, string> = { "1w": "1d", "1m": "1d", "3m": "1d", "1y": "1d" };
  const normalized = legacy[current] ?? current;
  return PRODUCT_INTERVALS.includes(normalized as (typeof PRODUCT_INTERVALS)[number]) ? normalized : "1d";
}

function normalizeRange(value: string | undefined): string {
  const current = (value ?? "3mo").toLowerCase();
  const legacy: Record<string, string> = { "1w": "5d", "1m": "1mo", "3m": "3mo" };
  const normalized = legacy[current] ?? current;
  return PRODUCT_RANGES.includes(normalized as (typeof PRODUCT_RANGES)[number]) ? normalized : "3mo";
}

function normalizeSurface(value: string | undefined, assetClass: ProductAssetClass): AssetSurface {
  const current = (value ?? "overview").toLowerCase();
  if (["overview", "chart", "catalysts", "news", "sources"].includes(current)) return current as AssetSurface;
  if (current === "financials" && assetClass !== "crypto") return "financials";
  if (current === "options" && assetClass === "equity") return "options";
  return "overview";
}

function isSurface(value: string | undefined): boolean {
  return ["overview", "chart", "financials", "catalysts", "news", "sources", "options"].includes((value ?? "").toLowerCase());
}

function normalizePanels(value: string | undefined): string[] {
  const requested = (value ?? "trend,momentum,risk,news,asset").split(",").map((item) => item.trim().toLowerCase());
  const output: string[] = [];
  requested.forEach((item) => {
    if (PRODUCT_PANELS.includes(item as (typeof PRODUCT_PANELS)[number]) && !output.includes(item)) output.push(item);
  });
  return output.length ? output : ["trend", "momentum", "risk", "news", "asset"];
}

function normalizeCompare(value: string | undefined, primary: string): string {
  const symbol = normalizeSymbol(value);
  if (!value || symbol === primary) return "";
  return SAFE_DYNAMIC_SYMBOL.test(symbol) ? symbol : "";
}

function normalizeMarketMapOriginState(value: string | undefined): string {
  if (!value || value.length > 900) return "";
  const allowed = new Set([
    "mode", "query", "sector", "industry", "country", "exchange", "eligibility",
    "freshness", "marketCap", "return1d", "return1m", "volatility", "rsi",
    "trend", "valuation", "quality", "rank", "display", "group", "size", "color",
    "selected", "compare",
  ]);
  const supplied = new URLSearchParams(value);
  const output = new URLSearchParams();
  supplied.forEach((rawValue, key) => {
    if (!allowed.has(key) || rawValue.length > 80) return;
    const safeValue = rawValue.replace(/[^A-Za-z0-9 .,=_/-]/g, "").slice(0, 80);
    if (safeValue) output.set(key, safeValue);
  });
  return output.toString();
}

function normalizeWarMapOriginState(value: string | undefined): string {
  if (!value || value.length > 900) return "";
  const output = sanitizeWarMapSearchParams(new URLSearchParams(value));
  output.delete("view");
  return output.toString();
}

function normalizeWatchlistOriginState(value: string | undefined): string {
  if (!value || value.length > 900) return "";
  const supplied = new URLSearchParams(value);
  const output = new URLSearchParams();
  const mode = supplied.get("mode");
  if (mode === "fixture" || mode === "local") output.set("mode", mode);
  const list = supplied.get("list") ?? "";
  if (/^[a-z0-9][a-z0-9-]{0,47}$/.test(list)) output.set("list", list);
  const selected = normalizeSymbol(supplied.get("selected") ?? "");
  if (SAFE_DYNAMIC_SYMBOL.test(selected)) output.set("selected", selected);
  const watchMode = supplied.get("watchMode");
  if (["price", "performance", "risk", "financials", "technicals", "catalysts", "changes"].includes(watchMode ?? "")) {
    output.set("watchMode", watchMode as string);
  }
  const sort = supplied.get("sort");
  if (["manual", "symbol", "metric-desc", "metric-asc"].includes(sort ?? "")) output.set("sort", sort as string);
  const group = supplied.get("group");
  if (["none", "sector", "exchange", "asset_class"].includes(group ?? "")) output.set("group", group as string);
  const panel = supplied.get("panel");
  if (["chart", "financials", "catalysts", "news", "sources"].includes(panel ?? "")) output.set("panel", panel as string);
  const changeType = supplied.get("changeType");
  if (["all", "price", "performance", "fundamental", "event", "news", "source-status"].includes(changeType ?? "")) {
    output.set("changeType", changeType as string);
  }
  const changeSeverity = supplied.get("changeSeverity");
  if (["all", "critical", "material", "info"].includes(changeSeverity ?? "")) {
    output.set("changeSeverity", changeSeverity as string);
  }
  const changeStatus = supplied.get("changeStatus");
  if (["all", "unacknowledged", "acknowledged"].includes(changeStatus ?? "")) {
    output.set("changeStatus", changeStatus as string);
  }
  const change = supplied.get("change") ?? "";
  if (/^change_[a-f0-9]{16}$/.test(change)) output.set("change", change);
  return output.toString();
}

function displayTimeframe(interval: string, range: string): string {
  if (interval !== "1d") return interval.toUpperCase();
  return ({ "5d": "1W", "1mo": "1M", "3mo": "3M", "1y": "1Y" } as Record<string, string>)[range] ?? "1D";
}
