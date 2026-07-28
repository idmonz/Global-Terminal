"use client";

import {
  Activity,
  BarChart3,
  Building2,
  CalendarDays,
  Database,
  Gauge,
  Keyboard,
  LayoutDashboard,
  MapPinned,
  Newspaper,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  TerminalSquare,
} from "lucide-react";
import Link from "next/link";
import {
  FormEvent,
  KeyboardEvent,
  type CSSProperties,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  CatalystPanel,
  ChartPanel,
  FinancialPanel,
  NewsPanel,
  PanelLoading,
  SourcesPanel,
  TechnicalsPanel,
  Unavailable,
} from "@/components/ProgressiveSymbolWorkstation";
import { AccountWorkspaceBar, type AccountLayoutValue } from "@/components/AccountWorkspaceBar";
import {
  ContractEnvelope,
  RuntimeMode,
  asRecordArray,
  isRecord,
} from "@/lib/contracts";
import { ProductAssetContext } from "@/lib/product-routes";

type Row = Record<string, unknown>;
type Panel =
  | "chart-core"
  | "technicals"
  | "financials"
  | "catalysts"
  | "news"
  | "sources"
  | "comparison";
type LayoutPreset = "research" | "chart-focus" | "events-evidence";

interface PanelState {
  envelope: ContractEnvelope | null;
  etag: string | null;
  loading: boolean;
  error: string | null;
  cacheKey: string;
  retainedLkg: boolean;
}

interface PanelFetchResult {
  envelope: ContractEnvelope | null;
  etag: string | null;
  notModified: boolean;
}

interface LocalLayout {
  preset: LayoutPreset;
  splitPercent: number;
  focusedPanel: Panel;
  visiblePanels: Panel[];
}

interface OperationsState {
  envelope: ContractEnvelope | null;
  loading: boolean;
  error: string | null;
  activeJob: Row | null;
}

const STORAGE_KEY = "global-terminal.analyst-layout.v1";
const PANELS: {
  panel: Panel;
  label: string;
  shortLabel: string;
  icon: typeof BarChart3;
}[] = [
  { panel: "chart-core", label: "Price chart", shortLabel: "Chart", icon: BarChart3 },
  { panel: "technicals", label: "Technical evidence", shortLabel: "Technicals", icon: Gauge },
  { panel: "financials", label: "Financial statements", shortLabel: "Financials", icon: Building2 },
  { panel: "catalysts", label: "Catalyst monitor", shortLabel: "Catalysts", icon: CalendarDays },
  { panel: "news", label: "Exact company news", shortLabel: "News", icon: Newspaper },
  { panel: "sources", label: "Source ledger", shortLabel: "Sources", icon: Database },
  { panel: "comparison", label: "Relative comparison", shortLabel: "Compare", icon: Activity },
];
const TIMEFRAME_LINKED = new Set<Panel>(["chart-core", "technicals", "comparison"]);
const DEFAULT_VISIBLE: Panel[] = ["chart-core", "financials", "catalysts", "sources"];

export const inflightPanelRequests = new Map<string, Promise<PanelFetchResult>>();

export function AnalystWorkspace({
  envelope: initialEnvelope,
  context,
  runtimeMode,
  apiBaseUrl,
  primaryEnvelope,
}: {
  envelope: ContractEnvelope;
  context: ProductAssetContext;
  runtimeMode: RuntimeMode;
  apiBaseUrl: string;
  primaryEnvelope: ContractEnvelope | null;
}) {
  const [workspaceEnvelope, setWorkspaceEnvelope] = useState(initialEnvelope);
  const initialWorkspace = workspace(initialEnvelope);
  const initialContext = record(initialWorkspace.context);
  const initialLayouts = record(initialWorkspace.layouts);
  const [symbol, setSymbol] = useState(text(record(initialWorkspace.identity).symbol, context.symbol));
  const [symbolInput, setSymbolInput] = useState(symbol);
  const [interval, setInterval] = useState(text(initialContext.interval, context.interval));
  const [range, setRange] = useState(text(initialContext.range, context.range));
  const [compare, setCompare] = useState(text(initialContext.compare, context.compare));
  const [layout, setLayout] = useState<LocalLayout>(() => ({
    preset: layoutPreset(initialLayouts.preset),
    splitPercent: boundedSplit(initialLayouts.split_percent),
    focusedPanel: panelId(initialContext.focused_panel),
    visiblePanels: panelList(initialLayouts.visible_panels, DEFAULT_VISIBLE),
  }));
  const initialPrimaryKey = [
    symbol,
    "chart-core",
    text(initialContext.interval, context.interval),
    text(initialContext.range, context.range),
    text(initialContext.compare, context.compare) || "none",
    runtimeMode,
  ].join(":");
  const initialPrimaryState: PanelState | undefined = primaryEnvelope && isExactPanel(primaryEnvelope, symbol)
    ? {
        envelope: primaryEnvelope,
        etag: null,
        loading: false,
        error: null,
        cacheKey: initialPrimaryKey,
        retainedLkg: false,
      }
    : undefined;
  const [panelStates, setPanelStates] = useState<Partial<Record<Panel, PanelState>>>(
    initialPrimaryState ? { "chart-core": initialPrimaryState } : {},
  );
  const panelCache = useRef<Record<string, PanelState>>(
    initialPrimaryState ? { [initialPrimaryKey]: initialPrimaryState } : {},
  );
  const primaryRevalidated = useRef(new Set<string>());
  const panelButtons = useRef<Partial<Record<Panel, HTMLButtonElement | null>>>({});
  const [isDesktop, setIsDesktop] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [operationsState, setOperationsState] = useState<OperationsState>({
    envelope: null,
    loading: true,
    error: null,
    activeJob: null,
  });

  const currentWorkspace = workspace(workspaceEnvelope);
  const identity = record(currentWorkspace.identity);
  const resolvedAssetClass = text(identity.asset_class, context.assetClass);
  const loadedPrimary = panelWorkstation(panelStates["chart-core"]?.envelope ?? null);
  const loadedPrimaryQuote = record(loadedPrimary.quote);
  const quote = Object.keys(loadedPrimaryQuote).length
    ? loadedPrimaryQuote
    : record(currentWorkspace.quote);
  const loadedPrimaryClock = record(loadedPrimary.market_clock);
  const workspaceContext = record(currentWorkspace.context);
  const change = record(currentWorkspace.change_context);
  const manifest = asRecordArray(currentWorkspace.panels);
  const requestPlan = record(currentWorkspace.request_plan);
  const focusedPanel = layout.focusedPanel;
  const operationsData = operations(operationsState.envelope);
  const operationsPanels = asRecordArray(operationsData.panels);
  const operationsBudget = record(operationsData.budget);
  const operationsQueue = record(operationsData.queue);
  const operationsReadiness = record(operationsData.readiness);
  const lastAttempt = record(operationsData.last_attempt);
  const lastSuccess = record(operationsData.last_success);
  const displayedJob = operationsState.activeJob ?? (
    Object.keys(lastAttempt).length ? lastAttempt : null
  );

  function panelKey(panel: Panel, mode: RuntimeMode = runtimeMode) {
    const linked = TIMEFRAME_LINKED.has(panel);
    return [
      symbol,
      panel,
      linked ? interval : "identity",
      linked ? range : "identity",
      panel === "comparison" ? compare || "none" : "none",
      mode,
    ].join(":");
  }

  function updateUrl(updates: Record<string, string>) {
    const url = new URL(window.location.href);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    });
    window.history.replaceState({}, "", url);
  }

  function restoreAccountLayout(saved: AccountLayoutValue) {
    const restored: LocalLayout = {
      preset: layoutPreset(saved.preset),
      splitPercent: boundedSplit(saved.splitPercent),
      focusedPanel: panelId(saved.focusedPanel),
      visiblePanels: panelList(saved.visiblePanels, DEFAULT_VISIBLE),
    };
    setLayout(restored);
    updateUrl({ layout: restored.preset, split: String(restored.splitPercent), panel: restored.focusedPanel });
  }

  async function loadPanel(
    panel: Panel,
    force = false,
    modeOverride: RuntimeMode = runtimeMode,
  ) {
      const key = panelKey(panel, modeOverride);
      const existing = panelCache.current[key];
      if (!force && existing?.envelope) {
        setPanelStates((current) => ({ ...current, [panel]: existing }));
        return;
      }
      const loadingState: PanelState = {
        envelope: existing?.envelope ?? null,
        etag: existing?.etag ?? null,
        loading: true,
        error: null,
        cacheKey: key,
        retainedLkg: false,
      };
      setPanelStates((current) => ({ ...current, [panel]: loadingState }));

      const query = new URLSearchParams({
        asset_class: resolvedAssetClass,
        interval,
        range,
        runtime_mode: modeOverride,
        chart_type: "candlestick",
      });
      if (panel === "comparison" && compare) query.set("compare", compare);
      const endpoint = `${apiBaseUrl}/api/symbol-workstation/${encodeURIComponent(symbol)}/panels/${panel}?${query}`;
      let request = inflightPanelRequests.get(key);
      if (!request) {
        request = fetchPanel(endpoint, force ? existing?.etag ?? null : null);
        inflightPanelRequests.set(key, request);
        void request.then(
          () => inflightPanelRequests.delete(key),
          () => inflightPanelRequests.delete(key),
        );
      }
      try {
        const result = await request;
        const loaded = result.notModified ? existing?.envelope ?? null : result.envelope;
        if (!loaded || !isExactPanel(loaded, symbol)) {
          throw new Error("identity-mismatch");
        }
        const ready: PanelState = {
          envelope: loaded,
          etag: result.etag ?? existing?.etag ?? null,
          loading: false,
          error: null,
          cacheKey: key,
          retainedLkg: false,
        };
        panelCache.current[key] = ready;
        setPanelStates((current) => ({ ...current, [panel]: ready }));
      } catch (error) {
        const retained = existing?.envelope && isExactPanel(existing.envelope, symbol)
          ? existing.envelope
          : null;
        const failed: PanelState = {
          envelope: retained,
          etag: existing?.etag ?? null,
          loading: false,
          error: error instanceof Error ? error.message : "panel-request-failed",
          cacheKey: key,
          retainedLkg: Boolean(retained),
        };
        if (retained) panelCache.current[key] = failed;
        setPanelStates((current) => ({ ...current, [panel]: failed }));
      }
  }

  async function loadOperations() {
    const query = new URLSearchParams({
      asset_class: resolvedAssetClass,
      interval,
      range,
      panels: DEFAULT_VISIBLE.join(","),
    });
    setOperationsState((current) => ({ ...current, loading: true, error: null }));
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/analyst-workspace/${encodeURIComponent(symbol)}/operations?${query}`,
        { cache: "no-store", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error(`operations-http-${response.status}`);
      const envelope = await response.json() as ContractEnvelope;
      if (text(record(operations(envelope).identity).symbol, "") !== symbol) {
        throw new Error("operations-identity-mismatch");
      }
      setOperationsState((current) => ({
        ...current,
        envelope,
        loading: false,
        error: null,
      }));
    } catch (error) {
      setOperationsState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "operations-request-failed",
      }));
    }
  }

  async function pollRefreshJob(jobId: string) {
    for (let attempt = 0; attempt < 80; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 250));
      const response = await fetch(
        `${apiBaseUrl}/api/research-operations/jobs/${encodeURIComponent(jobId)}`,
        { cache: "no-store", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error(`refresh-job-http-${response.status}`);
      const envelope = await response.json() as ContractEnvelope;
      const job = isRecord(envelope.data) ? envelope.data : {};
      setOperationsState((current) => ({ ...current, activeJob: job }));
      const status = text(job.status, "unavailable");
      if (!["queued", "running"].includes(status)) return job;
    }
    throw new Error("refresh-job-timeout");
  }

  async function refreshExactWorkspace(panels: Panel[] = DEFAULT_VISIBLE) {
    if (operationsState.activeJob && ["queued", "running"].includes(text(operationsState.activeJob.status, ""))) return;
    const idempotencyKey = `${symbol}-${Date.now().toString(36)}`;
    setOperationsState((current) => ({
      ...current,
      error: null,
      activeJob: {
        status: "queued",
        symbol,
        progress: { current: 0, total: panels.length, percent: 0 },
      },
    }));
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/analyst-workspace/${encodeURIComponent(symbol)}/refresh`,
        {
          method: "POST",
          cache: "no-store",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({
            asset_class: resolvedAssetClass,
            interval,
            range,
            panels,
            idempotency_key: idempotencyKey,
          }),
        },
      );
      const envelope = await response.json() as ContractEnvelope;
      const job = isRecord(envelope.data) ? envelope.data : {};
      if (response.status === 409) {
        setOperationsState((current) => ({
          ...current,
          activeJob: job,
          error: "Another refresh for this exact symbol is already active.",
        }));
        return;
      }
      if (!response.ok || !text(job.job_id, "")) {
        throw new Error(`refresh-http-${response.status}`);
      }
      setOperationsState((current) => ({ ...current, activeJob: job }));
      const terminal = await pollRefreshJob(text(job.job_id, ""));
      setHistory((current) => [
        `${symbol} refresh ${text(terminal.status)}`,
        ...current,
      ].slice(0, 6));
      await loadOperations();
      await Promise.all(
        panels.map((panel) => loadPanel(panel, true, "cache")),
      );
    } catch (error) {
      setOperationsState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "refresh-request-failed",
        activeJob: current.activeJob
          ? { ...current.activeJob, status: "failed" }
          : { status: "failed", symbol },
      }));
    }
  }

  useEffect(() => {
    const media = window.matchMedia("(min-width: 901px)");
    const sync = () => setIsDesktop(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    let timer = 0;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = normalizeLocalLayout(JSON.parse(raw));
      timer = window.setTimeout(
        () => setLayout((current) => ({ ...current, ...saved })),
        0,
      );
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    }
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const targets = isDesktop
      ? layout.visiblePanels.slice(0, 4)
      : [focusedPanel];
    targets.forEach((panel) => {
      const key = panelKey(panel);
      const revalidateSavedPrimary = panel === "chart-core"
        && runtimeMode !== "fixture"
        && !primaryRevalidated.current.has(key);
      if (revalidateSavedPrimary) primaryRevalidated.current.add(key);
      void loadPanel(panel, revalidateSavedPrimary);
    });
    // loadPanel intentionally reads the synchronized state listed below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    focusedPanel,
    interval,
    isDesktop,
    layout.visiblePanels,
    range,
    symbol,
  ]);

  useEffect(() => {
    void loadOperations();
    // The operations read is provider-call free and follows exact URL state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interval, range, resolvedAssetClass, symbol]);

  function focusPanel(panel: Panel) {
    setLayout((current) => ({ ...current, focusedPanel: panel }));
    setHistory((current) => [`${symbol} ${panel}`, ...current.filter((row) => row !== `${symbol} ${panel}`)].slice(0, 6));
    updateUrl({ panel });
    if (!isDesktop) void loadPanel(panel);
  }

  function changeTimeframe(nextInterval: string, nextRange: string) {
    setInterval(nextInterval);
    setRange(nextRange);
    setPanelStates((current) => {
      const retained = { ...current };
      TIMEFRAME_LINKED.forEach((panel) => delete retained[panel]);
      return retained;
    });
    updateUrl({ interval: nextInterval, range: nextRange });
  }

  async function switchSymbol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const requested = symbolInput.toUpperCase().replace(/[^A-Z0-9=._-]/g, "").slice(0, 24);
    if (!requested || requested === symbol) return;
    setWorkspaceError(null);
    const query = new URLSearchParams({
      asset_class: requested.endsWith("USDT") ? "crypto" : "equity",
      interval,
      range,
      runtime_mode: runtimeMode,
      layout: layout.preset,
      panel: layout.focusedPanel,
    });
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/analyst-workspace/${encodeURIComponent(requested)}?${query}`,
        { cache: "no-store", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error(`workspace-http-${response.status}`);
      const loaded = await response.json() as ContractEnvelope;
      const loadedWorkspace = workspace(loaded);
      if (text(record(loadedWorkspace.identity).symbol, "") !== requested) {
        throw new Error("workspace-identity-mismatch");
      }
      panelCache.current = {};
      setPanelStates({});
      setWorkspaceEnvelope(loaded);
      setSymbol(requested);
      setHistory((current) => [`${requested} workspace`, ...current].slice(0, 6));
      updateUrl({ symbol: requested });
    } catch {
      setWorkspaceError(`No exact ${requested} workspace is available. The ${symbol} workspace was retained.`);
    }
  }

  function saveLayout() {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
    setHistory((current) => [`Saved ${layout.preset} layout`, ...current].slice(0, 6));
  }

  function resetLayout() {
    const reset: LocalLayout = {
      preset: "research",
      splitPercent: 58,
      focusedPanel: "chart-core",
      visiblePanels: DEFAULT_VISIBLE,
    };
    window.localStorage.removeItem(STORAGE_KEY);
    setLayout(reset);
    updateUrl({ layout: reset.preset, panel: reset.focusedPanel });
  }

  function handleKeys(event: KeyboardEvent<HTMLElement>) {
    if (!event.altKey) return;
    const index = Number(event.key) - 1;
    const target = PANELS[index];
    if (!target) return;
    event.preventDefault();
    focusPanel(target.panel);
    panelButtons.current[target.panel]?.focus();
  }

  const returnHref = workspaceReturnHref(record(workspaceContext.return_state));
  const visibleDesktop = layout.visiblePanels.slice(0, 4);
  const primaryPanel = visibleDesktop.includes("chart-core")
    ? "chart-core"
    : visibleDesktop[0] ?? "chart-core";
  const secondaryPanels = visibleDesktop.filter((panel) => panel !== primaryPanel);

  return (
    <section
      className="analyst-workspace"
      aria-labelledby="analyst-workspace-title"
      onKeyDown={handleKeys}
      data-phase6h-analyst-workspace="true"
      data-symbol={symbol}
      data-focused-panel={focusedPanel}
      data-layout={layout.preset}
      data-mobile-lazy-field="hidden_mobile_panels_eagerly_fetched"
      data-mobile-lazy-value={String(requestPlan.hidden_mobile_panels_eagerly_fetched)}
      style={{ "--analyst-primary": `${layout.splitPercent}%` } as CSSProperties}
    >
      <header className="analyst-context-bar">
        <div className="analyst-identity">
          <span className="eyebrow">Synchronized analyst workspace</span>
          <h1 id="analyst-workspace-title">
            <code>{symbol}</code> {text(identity.name, "Exact instrument")}
          </h1>
          <p>{text(identity.exchange)} / {text(identity.asset_class)} / {text(identity.currency)}</p>
        </div>
        <div className="analyst-quote">
          <strong>{formatPrice(quote.last_price)}</strong>
          <span className={tone(quote.change_pct)}>{formatPercent(quote.change_pct)}</span>
          <small>{text(quote.provider)} / {text(quote.source_status)}</small>
        </div>
        <dl className="analyst-clocks">
          <Metric label="Market" value={shortTime(loadedPrimaryClock.market_data_as_of || workspaceContext.market_clock)} />
          <Metric label="Retrieved" value={shortTime(loadedPrimaryClock.retrieved_at || workspaceContext.source_clock)} />
          <Metric label="State" value={text(loadedPrimaryClock.market_data_status, text(workspaceContext.market_data_status))} />
        </dl>
      </header>

      <OperationsStrip
        budget={operationsBudget}
        error={operationsState.error}
        job={displayedJob}
        lastSuccess={lastSuccess}
        loading={operationsState.loading}
        onRefresh={() => void refreshExactWorkspace()}
        queue={operationsQueue}
        readiness={operationsReadiness}
      />

      <AccountWorkspaceBar layout={layout} onRestore={restoreAccountLayout} />

      <div className="analyst-toolbar">
        <form onSubmit={switchSymbol} className="analyst-symbol-switch">
          <label htmlFor="analyst-symbol-input">Symbol</label>
          <input
            id="analyst-symbol-input"
            value={symbolInput}
            onChange={(event) => setSymbolInput(event.target.value.toUpperCase())}
            maxLength={24}
            autoComplete="off"
          />
          <button type="submit" title="Open exact symbol workspace" aria-label="Open exact symbol workspace">
            <Search size={15} />
          </button>
        </form>
        <label>
          <span>Interval</span>
          <select
            aria-label="Workspace interval"
            value={interval}
            onChange={(event) => changeTimeframe(event.target.value, range)}
          >
            {["15m", "1h", "4h", "1d"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          <span>Range</span>
          <select
            aria-label="Workspace range"
            value={range}
            onChange={(event) => changeTimeframe(interval, event.target.value)}
          >
            {["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label className="analyst-compare">
          <span>Compare</span>
          <input
            aria-label="Comparison symbol"
            value={compare}
            maxLength={24}
            placeholder="SPY"
            onChange={(event) => setCompare(event.target.value.toUpperCase())}
            onBlur={() => updateUrl({ compare })}
          />
        </label>
        <div className="analyst-layout-presets" aria-label="Workspace layout preset">
          {(["research", "chart-focus", "events-evidence"] as LayoutPreset[]).map((preset) => (
            <button
              key={preset}
              type="button"
              className={layout.preset === preset ? "active" : ""}
              aria-pressed={layout.preset === preset}
              onClick={() => {
                const next = layoutForPreset(preset, layout);
                setLayout(next);
                updateUrl({ layout: preset });
              }}
            >
              {preset === "research" ? "Research" : preset === "chart-focus" ? "Chart" : "Events"}
            </button>
          ))}
        </div>
        <button type="button" className="analyst-icon-button" title="Save layout locally" aria-label="Save layout locally" onClick={saveLayout}>
          <Save size={15} />
        </button>
        <button type="button" className="analyst-icon-button" title="Reset local layout" aria-label="Reset local layout" onClick={resetLayout}>
          <RotateCcw size={15} />
        </button>
      </div>

      <div className="analyst-split-control">
        <LayoutDashboard size={14} aria-hidden="true" />
        <label htmlFor="analyst-split">Primary pane {layout.splitPercent}%</label>
        <input
          id="analyst-split"
          type="range"
          min="36"
          max="72"
          value={layout.splitPercent}
          onChange={(event) => setLayout((current) => ({ ...current, splitPercent: boundedSplit(event.target.value) }))}
        />
        <span><Keyboard size={13} /> Alt+1..7 focuses panels</span>
      </div>

      <nav className="analyst-panel-tabs" aria-label="Analyst workspace panels">
        {PANELS.map(({ panel, shortLabel, icon: Icon }, index) => (
          <button
            ref={(node) => { panelButtons.current[panel] = node; }}
            key={panel}
            type="button"
            className={focusedPanel === panel ? "active" : ""}
            aria-pressed={focusedPanel === panel}
            aria-label={`${shortLabel} panel, shortcut Alt+${index + 1}`}
            onClick={() => focusPanel(panel)}
          >
            <Icon size={15} aria-hidden="true" />
            {shortLabel}
            <PanelDot state={panelStates[panel]} />
          </button>
        ))}
      </nav>

      {workspaceError ? <div className="analyst-message" role="status">{workspaceError}</div> : null}

      {isDesktop ? (
        <div className={`analyst-desktop-grid layout-${layout.preset}`}>
          <PanelFrame
            panel={primaryPanel}
            manifest={manifest}
            operation={operationsPanels.find((row) => text(row.panel, "") === primaryPanel)}
            state={panelStates[primaryPanel]}
            focused={focusedPanel === primaryPanel}
            onFocus={() => focusPanel(primaryPanel)}
            onRefresh={() => void refreshExactWorkspace([primaryPanel])}
          />
          <div className="analyst-secondary-stack">
            {secondaryPanels.map((panel) => (
              <PanelFrame
                key={panel}
                panel={panel}
                manifest={manifest}
                operation={operationsPanels.find((row) => text(row.panel, "") === panel)}
                state={panelStates[panel]}
                focused={focusedPanel === panel}
                onFocus={() => focusPanel(panel)}
                onRefresh={() => void refreshExactWorkspace([panel])}
              />
            ))}
          </div>
          <WorkspaceRail change={change} history={history} returnHref={returnHref} symbol={symbol} runtimeMode={runtimeMode} />
        </div>
      ) : (
        <div className="analyst-mobile-panel">
          <PanelFrame
            panel={focusedPanel}
            manifest={manifest}
            operation={operationsPanels.find((row) => text(row.panel, "") === focusedPanel)}
            state={panelStates[focusedPanel]}
            focused
            onFocus={() => focusPanel(focusedPanel)}
            onRefresh={() => void refreshExactWorkspace([focusedPanel])}
          />
          <WorkspaceRail change={change} history={history} returnHref={returnHref} symbol={symbol} runtimeMode={runtimeMode} />
        </div>
      )}

      <footer className="analyst-footer">
        <span>Read-only research / not financial advice</span>
        <p>{text(quote.caveat, "Inspect provider, source status, market clock, and caveats before use.")}</p>
        {returnHref ? <Link prefetch={false} href={returnHref}>{returnHref.includes("view=alert-manager") ? "Return to Alert Manager" : returnHref.includes("view=attention-desk") ? "Return to Attention Desk" : "Return to Change Inbox"}</Link> : null}
      </footer>
    </section>
  );
}

function OperationsStrip({
  budget,
  error,
  job,
  lastSuccess,
  loading,
  onRefresh,
  queue,
  readiness,
}: {
  budget: Row;
  error: string | null;
  job: Row | null;
  lastSuccess: Row;
  loading: boolean;
  onRefresh: () => void;
  queue: Row;
  readiness: Row;
}) {
  const progress = record(job?.progress);
  const jobStatus = text(job?.status, text(queue.status, loading ? "loading" : "idle"));
  const active = ["queued", "running"].includes(jobStatus);
  const lastSuccessAt = lastSuccess.completed_at || lastSuccess.last_success_at;
  const nextRetry = job?.next_retry_at;
  return (
    <section
      className="analyst-operations-strip"
      data-phase6i-research-operations="true"
      aria-label="Exact workspace research operations"
    >
      <div className="analyst-operations-summary">
        <span className="eyebrow">Live research operations</span>
        <strong>{text(readiness.observed_provider_count, "0")} observed providers</strong>
        <small>Configured-only {text(readiness.configured_only_count, "0")}</small>
      </div>
      <dl>
        <Metric label="Queue" value={jobStatus} />
        <Metric
          label="Budget"
          value={`${text(job?.actual_calls, text(budget.actual_calls, "0"))} / ${text(budget.planned_calls, "8")} calls`}
        />
        <div className="last-success">
          <dt>Last success</dt>
          <dd>{shortTime(lastSuccessAt)}</dd>
        </div>
        <div className="next-safe-retry">
          <dt>Next safe retry</dt>
          <dd>{shortTime(nextRetry)}</dd>
        </div>
      </dl>
      <div
        className={`analyst-operation-status status-${jobStatus}`}
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <span>{active ? `${text(progress.percent, "0")}%` : jobStatus}</span>
        <small>
          {error
            ? error
            : active
            ? `${text(progress.current, "0")} of ${text(progress.total, "0")} panels`
            : text(job?.retry_reason, "Manual, bounded, no automatic retry")}
        </small>
      </div>
      <button
        type="button"
        className="analyst-refresh-workspace"
        onClick={onRefresh}
        disabled={active || loading}
        aria-label={`Refresh exact workspace, maximum ${text(budget.planned_calls, "8")} provider calls`}
      >
        <RefreshCw size={14} className={active ? "spin" : ""} aria-hidden="true" />
        <span>Refresh exact workspace</span>
        <small>max {text(budget.planned_calls, "8")}</small>
      </button>
    </section>
  );
}

function PanelFrame({
  panel,
  manifest,
  operation,
  state,
  focused,
  onFocus,
  onRefresh,
}: {
  panel: Panel;
  manifest: Row[];
  operation: Row | undefined;
  state: PanelState | undefined;
  focused: boolean;
  onFocus: () => void;
  onRefresh: () => void;
}) {
  const meta = manifest.find((row) => text(row.panel_id, "") === panel) ?? {};
  const loaded = panelWorkstation(state?.envelope ?? null);
  const loadedSummary = state?.envelope && isRecord(state.envelope.summary)
    ? state.envelope.summary
    : {};
  const displayedProvider = text(loadedSummary.provider, text(meta.provider, "on-demand"));
  const displayedStatus = text(loadedSummary.source_status, text(meta.source_status, "not-loaded"));
  const displayedClock = loadedSummary.fetched_at ?? meta.fetched_at;
  const operationStatus = text(operation?.source_status, displayedStatus);
  const sloState = text(operation?.slo_state, "not-observed");
  const operationProvider = text(operation?.provider, displayedProvider);
  return (
    <section
      className={`analyst-panel ${focused ? "focused" : ""}`}
      aria-label={`${text(meta.title, panel)} research panel`}
      data-panel={panel}
      data-panel-status={state?.error ? state.retainedLkg ? "last-known-good" : "error" : state?.loading ? "loading" : state?.envelope ? "ready" : "idle"}
      onClick={onFocus}
    >
      <header className="analyst-panel-heading">
        <div>
          <span>{text(meta.title, panel)}</span>
          <small>{operationProvider} / {operationStatus} / SLO {sloState}</small>
        </div>
        <button type="button" title={`Queue bounded refresh for ${panel}`} aria-label={`Queue bounded refresh for ${panel}`} onClick={(event) => { event.stopPropagation(); onRefresh(); }}>
          <RefreshCw size={13} className={state?.loading ? "spin" : ""} />
        </button>
      </header>
      {state?.error ? (
        <div className={state.retainedLkg ? "analyst-panel-warning lkg" : "analyst-panel-warning"} role="status">
          {state.retainedLkg
            ? `Latest refresh failed (${state.error}); same-symbol last-known-good evidence is retained.`
            : `Panel request failed (${state.error}); no substitute symbol was used.`}
        </div>
      ) : null}
      {state?.loading && !state.envelope ? <PanelLoading panel={panel} /> : null}
      {state?.envelope ? <PanelBody panel={panel} envelope={state.envelope} workstation={loaded} /> : null}
      {!state?.loading && !state?.envelope ? (
        <Unavailable title={`${text(meta.title, panel)} not loaded`} detail={text(meta.data_gap || meta.caveat, "Select or refresh this exact-symbol panel.")} />
      ) : null}
      <footer className="analyst-panel-provenance">
        <span>{operationStatus} / {sloState}</span>
        <time>{shortTime(operation?.retrieved_at || displayedClock)}</time>
        <p>{text(operation?.data_gap || operation?.caveat || meta.data_gap || meta.caveat, "No declared gap")}</p>
      </footer>
    </section>
  );
}

function PanelBody({
  panel,
  envelope,
  workstation: current,
}: {
  panel: Panel;
  envelope: ContractEnvelope;
  workstation: Row;
}) {
  if (panel === "chart-core") {
    return <ChartPanel workstation={current} chart={record(record(current.chart_views).price)} />;
  }
  if (panel === "technicals") {
    return <TechnicalsPanel workstation={current} charts={asRecordArray(record(current.chart_views).analysis)} />;
  }
  if (panel === "financials") return <FinancialPanel workstation={current} />;
  if (panel === "catalysts") return <CatalystPanel workstation={current} />;
  if (panel === "news") return <NewsPanel workstation={current} />;
  if (panel === "sources") return <SourcesPanel envelope={envelope} />;
  const comparison = record(current.comparison);
  return (
    <section className="analyst-compact-comparison">
      <strong>{text(comparison.status, "not requested")}</strong>
      <span>{text(comparison.primary_symbol)} vs {text(comparison.comparison_symbol, "select comparison")}</span>
      <p>{text(comparison.data_gap || comparison.caveat)}</p>
    </section>
  );
}

function WorkspaceRail({
  change,
  history,
  returnHref,
  symbol,
  runtimeMode,
}: {
  change: Row;
  history: string[];
  returnHref: string | null;
  symbol: string;
  runtimeMode: RuntimeMode;
}) {
  return (
    <aside className="analyst-workspace-rail" aria-label="Change evidence and verified actions">
      <section>
        <span className="eyebrow">Selected change</span>
        <h3>{text(change.change_type, "No saved change")}</h3>
        <dl>
          <Metric label="Field" value={text(change.field, "unavailable")} />
          <Metric label="Before" value={text(change.before, "unavailable")} />
          <Metric label="After" value={text(change.after, "unavailable")} />
          <Metric label="Status" value={text(change.status, "not-selected")} />
        </dl>
        <p>{text(change.data_gap || change.caveat, "Select a Change Inbox event to bind before/after evidence.")}</p>
        {safeHttp(change.source_url) ? <a href={text(change.source_url)} target="_blank" rel="noreferrer">Open exact evidence</a> : null}
      </section>
      <section>
        <span className="eyebrow">Verified actions</span>
        <nav>
          <Link prefetch={false} href={`/?view=war-room-map&selected=${encodeURIComponent(symbol)}&mode=${runtimeMode}`}><MapPinned size={14} /> Map context</Link>
          <Link prefetch={false} href={`/?view=command-workspace&symbol=${encodeURIComponent(symbol)}&mode=${runtimeMode}`}><TerminalSquare size={14} /> Command workspace</Link>
          {returnHref ? <Link prefetch={false} href={returnHref}><RotateCcw size={14} /> Change Inbox</Link> : null}
        </nav>
      </section>
      <section>
        <span className="eyebrow">Local activity</span>
        {history.length ? <ol>{history.map((row, index) => <li key={`${row}-${index}`}>{row}</li>)}</ol> : <p>No local workspace action yet.</p>}
      </section>
    </aside>
  );
}

function PanelDot({ state }: { state: PanelState | undefined }) {
  const status = state?.error
    ? state.retainedLkg ? "lkg" : "error"
    : state?.loading ? "loading"
    : state?.envelope ? "ready"
    : "idle";
  return <i className={`analyst-panel-dot ${status}`} aria-hidden="true" />;
}

async function fetchPanel(endpoint: string, etag: string | null): Promise<PanelFetchResult> {
  const response = await fetch(endpoint, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(etag ? { "If-None-Match": etag } : {}),
    },
  });
  if (response.status === 304) {
    return { envelope: null, etag, notModified: true };
  }
  if (!response.ok) throw new Error(`runtime-http-${response.status}`);
  return {
    envelope: await response.json() as ContractEnvelope,
    etag: response.headers.get("etag"),
    notModified: false,
  };
}

function isExactPanel(envelope: ContractEnvelope, symbol: string): boolean {
  return text(record(panelWorkstation(envelope).identity).symbol, "") === symbol;
}

function panelWorkstation(envelope: ContractEnvelope | null): Row {
  if (!envelope || !isRecord(envelope.data)) return {};
  return asRecordArray(envelope.data.workstations)[0] ?? {};
}

function workspace(envelope: ContractEnvelope): Row {
  return isRecord(envelope.data) ? envelope.data : {};
}

function operations(envelope: ContractEnvelope | null): Row {
  return envelope && isRecord(envelope.data) ? envelope.data : {};
}

function record(value: unknown): Row {
  return isRecord(value) ? value : {};
}

function text(value: unknown, fallback = "unavailable"): string {
  return value === null || value === undefined || value === "" || typeof value === "object"
    ? fallback
    : String(value);
}

function panelId(value: unknown): Panel {
  const current = text(value, "chart-core");
  return PANELS.some((row) => row.panel === current) ? current as Panel : "chart-core";
}

function panelList(value: unknown, fallback: Panel[]): Panel[] {
  const supplied = Array.isArray(value) ? value.map(panelId) : fallback;
  return supplied.filter((panel, index) => supplied.indexOf(panel) === index).slice(0, 7);
}

function layoutPreset(value: unknown): LayoutPreset {
  const current = text(value, "research");
  return current === "chart-focus" || current === "events-evidence" ? current : "research";
}

function boundedSplit(value: unknown): number {
  const current = Number(value);
  return Number.isFinite(current) ? Math.max(36, Math.min(72, Math.round(current))) : 58;
}

function normalizeLocalLayout(value: unknown): LocalLayout {
  const current = record(value);
  return {
    preset: layoutPreset(current.preset),
    splitPercent: boundedSplit(current.splitPercent),
    focusedPanel: panelId(current.focusedPanel),
    visiblePanels: panelList(current.visiblePanels, DEFAULT_VISIBLE),
  };
}

function layoutForPreset(preset: LayoutPreset, current: LocalLayout): LocalLayout {
  if (preset === "chart-focus") {
    return { ...current, preset, splitPercent: 72, visiblePanels: ["chart-core", "technicals", "sources"] };
  }
  if (preset === "events-evidence") {
    return { ...current, preset, splitPercent: 50, visiblePanels: ["chart-core", "catalysts", "news", "sources"] };
  }
  return { ...current, preset, splitPercent: 58, visiblePanels: DEFAULT_VISIBLE };
}

function workspaceReturnHref(state: Row): string | null {
  if (text(state.origin, "") === "alert-manager") {
    const input = new URLSearchParams(text(state.originState, ""));
    const output = new URLSearchParams({ view: "alert-manager" });
    const mode = input.get("mode");
    if (["fixture", "cache"].includes(mode ?? "")) output.set("mode", mode as string);
    const tab = input.get("tab");
    if (["rules", "history", "runs"].includes(tab ?? "")) output.set("tab", tab as string);
    const selectedTrigger = input.get("selectedTrigger");
    if (/^[A-Za-z0-9_-]{3,80}$/.test(selectedTrigger ?? "")) output.set("selectedTrigger", selectedTrigger as string);
    return `/?${output}`;
  }
  if (text(state.origin, "") === "attention-desk") {
    const input = new URLSearchParams(text(state.originState, ""));
    const output = new URLSearchParams({ view: "attention-desk" });
    const mode = input.get("mode");
    if (["fixture", "cache"].includes(mode ?? "")) output.set("mode", mode as string);
    const review = input.get("review");
    if (["needs-review", "all", "reviewed", "acknowledged"].includes(review ?? "")) output.set("review", review as string);
    return `/?${output}`;
  }
  if (text(state.origin, "") !== "watchlist" && text(state.origin, "") !== "watchlist-desk") return null;
  const params = new URLSearchParams({ view: "watchlist-desk" });
  const mapping: Record<string, string> = {
    list: "list",
    type: "changeType",
    severity: "changeSeverity",
    status: "changeStatus",
    change: "change",
    symbol: "selected",
  };
  Object.entries(mapping).forEach(([source, target]) => {
    const value = text(state[source], "");
    if (/^[A-Za-z0-9_.:-]{1,100}$/.test(value)) params.set(target, value);
  });
  params.set("watchMode", "changes");
  return `/?${params}`;
}

function safeHttp(value: unknown): boolean {
  try {
    const url = new URL(text(value, ""));
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function numeric(value: unknown): number | null {
  const current = Number(value);
  return value !== null && value !== "" && Number.isFinite(current) ? current : null;
}

function formatPrice(value: unknown): string {
  const current = numeric(value);
  return current === null
    ? "Unavailable"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: current < 10 ? 4 : 2 }).format(current);
}

function formatPercent(value: unknown): string {
  const current = numeric(value);
  return current === null ? "-" : `${current > 0 ? "+" : ""}${current.toFixed(2)}%`;
}

function tone(value: unknown): string {
  const current = numeric(value) ?? 0;
  return current > 0 ? "gain" : current < 0 ? "loss" : "flat";
}

function shortTime(value: unknown): string {
  if (!value) return "unavailable";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime())
    ? "unavailable"
    : new Intl.DateTimeFormat("en", {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      }).format(date);
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}
