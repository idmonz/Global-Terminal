"use client";

import {
  Activity,
  BarChart3,
  Building2,
  CalendarDays,
  Database,
  Gauge,
  Newspaper,
  RefreshCw,
  Scale,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { FinanceChart } from "@/components/FinanceChart";
import {
  ContractEnvelope,
  RuntimeMode,
  asRecordArray,
  isRecord,
} from "@/lib/contracts";
import { ProductAssetContext } from "@/lib/product-routes";

type Row = Record<string, unknown>;
type Panel = "chart-core" | "technicals" | "financials" | "catalysts" | "news" | "comparison" | "sources";

const PANEL_TABS: { panel: Panel; label: string; icon: typeof BarChart3 }[] = [
  { panel: "chart-core", label: "Chart", icon: BarChart3 },
  { panel: "technicals", label: "Technicals", icon: Gauge },
  { panel: "financials", label: "Financials", icon: Building2 },
  { panel: "catalysts", label: "Catalysts", icon: CalendarDays },
  { panel: "news", label: "News", icon: Newspaper },
  { panel: "comparison", label: "Compare", icon: Scale },
  { panel: "sources", label: "Sources", icon: Database },
];

export function ProgressiveSymbolWorkstation({
  envelope,
  context,
  runtimeMode,
  apiBaseUrl,
}: {
  envelope: ContractEnvelope;
  context: ProductAssetContext;
  runtimeMode: RuntimeMode;
  apiBaseUrl: string;
}) {
  const initialPanel = panelForSurface(context.surface);
  const [activePanel, setActivePanel] = useState<Panel>(initialPanel);
  const [interval, setInterval] = useState(context.interval);
  const [range, setRange] = useState(context.range);
  const [chartType, setChartType] = useState(context.chartType);
  const [compare, setCompare] = useState(context.compare);
  const [panelEnvelope, setPanelEnvelope] = useState<ContractEnvelope | null>(null);
  const [panelCache, setPanelCache] = useState<Record<string, ContractEnvelope>>({});
  const etags = useRef<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const summaryWorkstation = workstation(envelope);
  const loadedWorkstation = workstation(panelEnvelope);
  const activeWorkstation = Object.keys(loadedWorkstation).length
    ? loadedWorkstation
    : summaryWorkstation;
  const identity = record(summaryWorkstation.identity);
  const quote = record(summaryWorkstation.quote);
  const clock = record(activeWorkstation.market_clock);
  const chart = record(record(loadedWorkstation.chart_views).price);
  const analysisCharts = asRecordArray(record(loadedWorkstation.chart_views).analysis);
  const panelBytes = panelEnvelope ? JSON.stringify(panelEnvelope).length : 0;
  const initialBytes = useMemo(() => JSON.stringify(envelope).length, [envelope]);

  const cacheKey = useCallback(
    (panel: Panel) => [
      context.symbol,
      interval,
      range,
      chartType,
      panel,
      panel === "comparison" ? compare : "",
      runtimeMode,
    ].join(":"),
    [chartType, compare, context.symbol, interval, range, runtimeMode],
  );

  const loadPanel = useCallback(async (panel: Panel, force = false) => {
    const key = cacheKey(panel);
    if (!force && panelCache[key]) {
      setPanelEnvelope(panelCache[key]);
      setMessage(null);
      return;
    }
    setLoading(true);
    setMessage(null);
    const query = new URLSearchParams({
      asset_class: context.assetClass,
      interval,
      range,
      runtime_mode: runtimeMode,
      chart_type: chartType,
    });
    if (panel === "comparison" && compare) query.set("compare", compare);
    const path = `${apiBaseUrl}/api/symbol-workstation/${encodeURIComponent(context.symbol)}/panels/${panel}?${query.toString()}`;
    try {
      const response = await fetch(path, {
        cache: "no-store",
        headers: {
          Accept: "application/json",
          ...(force && etags.current[key] ? { "If-None-Match": etags.current[key] } : {}),
        },
      });
      if (response.status === 304 && panelCache[key]) {
        setPanelEnvelope(panelCache[key]);
        return;
      }
      if (!response.ok) throw new Error(`runtime-http-${response.status}`);
      const loaded = await response.json() as ContractEnvelope;
      const etag = response.headers.get("etag");
      if (etag) etags.current[key] = etag;
      setPanelCache((current) => ({ ...current, [key]: loaded }));
      setPanelEnvelope(loaded);
    } catch (error) {
      setPanelEnvelope(null);
      setMessage(
        error instanceof Error && error.message === "runtime-http-503"
          ? "Runtime API is offline. The verified summary remains visible; this panel was not substituted."
          : "This exact-symbol panel is unavailable. Existing summary data remains visible.",
      );
    } finally {
      setLoading(false);
    }
  }, [
    apiBaseUrl,
    cacheKey,
    chartType,
    compare,
    context.assetClass,
    context.symbol,
    interval,
    panelCache,
    range,
    runtimeMode,
  ]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadPanel(activePanel), 0);
    return () => window.clearTimeout(timer);
  }, [activePanel, chartType, compare, interval, range]); // eslint-disable-line react-hooks/exhaustive-deps

  function updateUrl(next: {
    panel?: Panel;
    interval?: string;
    range?: string;
    chartType?: "line" | "candlestick";
    compare?: string;
  }) {
    const url = new URL(window.location.href);
    if (next.panel) url.searchParams.set("surface", surfaceForPanel(next.panel));
    if (next.interval) url.searchParams.set("interval", next.interval);
    if (next.range) url.searchParams.set("range", next.range);
    if (next.chartType) url.searchParams.set("chartType", next.chartType);
    if (next.compare !== undefined) {
      if (next.compare) url.searchParams.set("compare", next.compare);
      else url.searchParams.delete("compare");
    }
    window.history.replaceState({}, "", url);
  }

  function activate(panel: Panel) {
    setActivePanel(panel);
    setPanelEnvelope(panelCache[cacheKey(panel)] ?? null);
    updateUrl({ panel });
  }

  return (
    <section
      className="progressive-symbol-workstation"
      aria-labelledby="progressive-symbol-title"
      data-phase6e-progressive-workstation="true"
      data-symbol-workstation-state={text(record(summaryWorkstation.summary).status, "available")}
      data-symbol={context.symbol}
      data-delivery-panel={activePanel}
      data-summary-bytes={String(initialBytes)}
      data-panel-bytes={String(panelBytes)}
      data-runtime-boundary="same-origin"
    >
      <header className="progressive-symbol-header">
        <div>
          <span className="eyebrow">Exact identity / progressive delivery</span>
          <h2 id="progressive-symbol-title">
            <code>{context.symbol}</code> {text(identity.name, "Verified instrument")}
          </h2>
          <p>
            {text(identity.exchange)} / {text(identity.asset_class, context.assetClass)} / {text(identity.currency)}
          </p>
        </div>
        <div className="progressive-quote">
          <strong>{formatPrice(quote.last_price)}</strong>
          <span className={returnTone(quote.change_pct)}>{formatPercent(quote.change_pct)}</span>
          <small>{text(quote.provider)} / {text(quote.source_status)}</small>
        </div>
        <div className="progressive-clock">
          <span>{text(clock.market_data_status, text(quote.source_status))}</span>
          <strong>{shortTime(clock.market_data_as_of || quote.fetched_at)}</strong>
          <small>Retrieved {shortTime(clock.retrieved_at || quote.fetched_at)}</small>
        </div>
      </header>

      <div className="progressive-control-deck">
        <label>
          <span>Interval</span>
          <select
            value={interval}
            onChange={(event) => {
              setInterval(event.target.value);
              setPanelEnvelope(null);
              updateUrl({ interval: event.target.value });
            }}
          >
            {["15m", "1h", "4h", "1d"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          <span>Range</span>
          <select
            value={range}
            onChange={(event) => {
              setRange(event.target.value);
              setPanelEnvelope(null);
              updateUrl({ range: event.target.value });
            }}
          >
            {["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <div className="progressive-segmented" aria-label="Chart type">
          {(["candlestick", "line"] as const).map((value) => (
            <button
              type="button"
              key={value}
              className={chartType === value ? "active" : ""}
              onClick={() => {
                setChartType(value);
                setPanelEnvelope(null);
                updateUrl({ chartType: value });
              }}
            >
              {value === "candlestick" ? "Candles" : "Line"}
            </button>
          ))}
        </div>
        <label className="progressive-compare-input">
          <span>Compare</span>
          <input
            value={compare}
            maxLength={24}
            placeholder="SPY"
            onChange={(event) => setCompare(event.target.value.toUpperCase())}
            onBlur={() => updateUrl({ compare })}
          />
        </label>
        <button
          type="button"
          className="progressive-refresh"
          title="Revalidate active exact-symbol panel"
          onClick={() => void loadPanel(activePanel, true)}
        >
          <RefreshCw size={15} className={loading ? "spin" : ""} />
          Refresh panel
        </button>
      </div>

      <nav className="progressive-panel-tabs" aria-label="Symbol research panels">
        {PANEL_TABS.map(({ panel, label, icon: Icon }) => (
          <button
            type="button"
            key={panel}
            className={activePanel === panel ? "active" : ""}
            onClick={() => activate(panel)}
          >
            <Icon size={15} aria-hidden="true" /> {label}
          </button>
        ))}
      </nav>

      <div className="progressive-panel-status">
        <span><Activity size={14} /> {loading ? `Loading ${activePanel}` : `${activePanel} ready state`}</span>
        <span>Summary {Math.ceil(initialBytes / 1024)} KB</span>
        <span>Panel {panelBytes ? `${Math.ceil(panelBytes / 1024)} KB` : "not loaded"}</span>
        <span>{runtimeMode}</span>
      </div>

      {message ? <div className="progressive-panel-message" role="status">{message}</div> : null}
      {loading && !panelEnvelope ? <PanelLoading panel={activePanel} /> : null}
      {!loading || panelEnvelope ? (
        <>
          {activePanel === "chart-core" ? <ChartPanel workstation={loadedWorkstation} chart={chart} /> : null}
          {activePanel === "technicals" ? <TechnicalsPanel workstation={loadedWorkstation} charts={analysisCharts} /> : null}
          {activePanel === "financials" ? <FinancialPanel workstation={loadedWorkstation} /> : null}
          {activePanel === "catalysts" ? <CatalystPanel workstation={loadedWorkstation} /> : null}
          {activePanel === "news" ? <NewsPanel workstation={loadedWorkstation} /> : null}
          {activePanel === "comparison" ? <ComparisonPanel workstation={loadedWorkstation} /> : null}
          {activePanel === "sources" ? <SourcesPanel envelope={panelEnvelope ?? envelope} /> : null}
        </>
      ) : null}

      <footer className="progressive-workstation-footer">
        <span>Read-only research / not financial advice</span>
        <p>{text(quote.caveat, "Delayed public or cached observations. Inspect provider, source status, and timestamps.")}</p>
        {context.originView && context.originState ? (
          <Link href={`/?view=${encodeURIComponent(context.originView)}&${context.originState}`}>
            Return to {context.originView === "watchlist-desk" ? "Watchlist" : context.originView === "attention-desk" ? "Attention Desk" : "origin"}
          </Link>
        ) : null}
      </footer>
    </section>
  );
}

export function ChartPanel({ workstation: current, chart }: { workstation: Row; chart: Row }) {
  if (!Object.keys(chart).length) {
    return <Unavailable title="Chart cache unavailable" detail="No exact OHLCV panel was returned. No other symbol was substituted." />;
  }
  return (
    <section className="progressive-chart-panel" data-chart-rows={String(asRecordArray(chart.candles).length)}>
      <header>
        <div><span className="eyebrow">Verified OHLCV</span><h3>{text(chart.title)}</h3></div>
        <dl>
          <Metric label="Candles" value={text(asRecordArray(chart.candles).length)} />
          <Metric label="Provider" value={text(chart.provider)} />
          <Metric label="Status" value={text(chart.source_status)} />
          <Metric label="As of" value={shortTime(chart.fetched_at)} />
        </dl>
      </header>
      <FinanceChart chart={chart} />
      <p>{text(chart.data_gap || chart.caveat)}</p>
      <small>{text(record(current.summary).history_row_count, "0")} observations represented without duplicating raw history in the panel payload.</small>
    </section>
  );
}

export function TechnicalsPanel({ workstation: current, charts }: { workstation: Row; charts: Row[] }) {
  const technical = record(current.technical_analysis);
  const summary = record(technical.summary);
  if (!Object.keys(current).length) return <Unavailable title="Technicals unavailable" detail="Load the exact technical panel from the runtime API." />;
  return (
    <section className="progressive-detail-panel">
      <header><div><span className="eyebrow">Historical calculations</span><h3>Trend, momentum, and risk</h3></div><b>{text(technical.status)}</b></header>
      <dl className="progressive-metric-grid">
        <Metric label="SMA 20" value={formatNumber(summary.sma_20)} />
        <Metric label="EMA 20" value={formatNumber(summary.ema_20)} />
        <Metric label="RSI 14" value={formatNumber(summary.rsi_14)} />
        <Metric label="MACD" value={formatNumber(summary.macd_12_26_9)} />
        <Metric label="Realized vol" value={formatPercentFraction(summary.realized_volatility_20)} />
        <Metric label="Drawdown" value={formatPercentFraction(summary.drawdown)} />
      </dl>
      <div className="progressive-analysis-grid">
        {charts.map((item) => <FinanceChart key={text(item.chart_id)} chart={item} />)}
      </div>
      <p>{text(technical.data_gap || technical.caveat)}</p>
    </section>
  );
}

export function FinancialPanel({ workstation: current }: { workstation: Row }) {
  const financial = record(current.financial_context);
  const metrics = record(financial.metrics);
  if (!Object.keys(current).length || text(financial.availability) === "not-loaded") {
    return <Unavailable title="Financials unavailable" detail="The financial provider was not requested or returned no exact-symbol record." />;
  }
  return (
    <section className="progressive-detail-panel">
      <header><div><span className="eyebrow">On-demand fundamentals</span><h3>Financial context</h3></div><b>{text(financial.source_status)}</b></header>
      <dl className="progressive-metric-grid">
        <Metric label="Market cap" value={compact(metrics.market_cap)} />
        <Metric label="Trailing P/E" value={formatNumber(metrics.trailing_pe)} />
        <Metric label="Forward P/E" value={formatNumber(metrics.forward_pe)} />
        <Metric label="Price / book" value={formatNumber(metrics.price_to_book)} />
        <Metric label="Revenue" value={compact(metrics.total_revenue)} />
        <Metric label="Free cash flow" value={compact(metrics.free_cash_flow)} />
      </dl>
      <p>{text(financial.data_gap || financial.caveat)}</p>
    </section>
  );
}

export function CatalystPanel({ workstation: current }: { workstation: Row }) {
  const catalysts = record(current.catalyst_context);
  const earnings = asRecordArray(catalysts.earnings);
  const dividends = asRecordArray(catalysts.dividends);
  const news = asRecordArray(catalysts.news);
  const next = record(catalysts.next_event);
  if (!Object.keys(current).length || text(catalysts.availability) === "not-loaded") {
    return <Unavailable title="Catalysts unavailable" detail="Run the active-list Research Snapshot, then open this exact-symbol panel." />;
  }
  return (
    <section className="progressive-detail-panel watchlist-catalyst-panel" data-progressive-catalyst-count={String(earnings.length + dividends.length + news.length)}>
      <header><div><span className="eyebrow">Bounded Research Snapshot</span><h3>Exact catalyst monitor</h3></div><b className={statusTone(text(catalysts.source_status))}>{text(catalysts.source_status)}</b></header>
      <div className="watchlist-next-catalyst">
        <CalendarDays size={18} aria-hidden="true" />
        <div><span>Next event</span><strong>{catalystLabel(next)}</strong></div>
        <time>{catalystDate(next)}</time>
      </div>
      <div className="watchlist-catalyst-columns">
        <section>
          <h5>Calendar</h5>
          <div className="watchlist-catalyst-coverage">
            <span>Earnings {earnings.length || "unavailable"}</span>
            <span>Dividends {dividends.length || "unavailable"}</span>
          </div>
          {[...earnings, ...dividends].length ? [...earnings, ...dividends].slice(0, 5).map((row, index) => (
            <article key={`${text(row.event_type)}-${catalystDate(row)}-${index}`}>
              <div><strong>{catalystLabel(row)}</strong><time>{catalystDate(row)}</time></div>
              <small>{text(row.provider)} / {text(row.source_status)}</small>
              <p>{row.estimated_eps !== undefined ? `EPS est. ${formatNumber(row.estimated_eps)} / actual ${formatNumber(row.reported_eps)}` : `Dividend ${formatNumber(row.amount)}`}</p>
            </article>
          )) : <Unavailable title="No calendar event" detail="Missing events remain unavailable." />}
        </section>
        <section>
          <h5>Exact news</h5>
          <div className="watchlist-catalyst-coverage"><span>Strict matches {news.length || "unavailable"}</span></div>
          {news.length ? news.slice(0, 5).map((row, index) => (
            <article key={`${text(row.title)}-${index}`}>
              <div><strong>{safeHttp(row.source_url) ? <a href={text(row.source_url)} target="_blank" rel="noreferrer">{text(row.title)}</a> : text(row.title)}</strong><time>{shortTime(row.published_at)}</time></div>
              <small>{text(row.provider)} / exact {text(record(row.match_evidence).exact, "false")}</small>
              <p>{text(row.summary, "Verify at the linked publisher.")}</p>
            </article>
          )) : <Unavailable title="No exact headline" detail="Broad headlines are not substituted." />}
        </section>
      </div>
      <footer><span>Snapshot {shortTime(catalysts.fetched_at)}</span><p>{text(catalysts.data_gap || catalysts.caveat)}</p></footer>
    </section>
  );
}

export function NewsPanel({ workstation: current }: { workstation: Row }) {
  const exact = record(current.exact_news);
  const rows = asRecordArray(exact.rows);
  if (!Object.keys(current).length) return <Unavailable title="News unavailable" detail="No exact-symbol news panel was returned." />;
  return (
    <section className="progressive-detail-panel">
      <header><div><span className="eyebrow">Exact-symbol headlines</span><h3>News monitor</h3></div><b>{text(exact.source_status)}</b></header>
      <div className="progressive-news-list">
        {rows.length ? rows.slice(0, 12).map((row, index) => (
          <article key={`${text(row.title)}-${index}`}>
            <div><span>{text(row.provider)}</span><small>{shortTime(row.published_at)}</small></div>
            <strong>{safeHttp(row.source_url) ? <a href={text(row.source_url)} target="_blank" rel="noreferrer">{text(row.title)}</a> : text(row.title)}</strong>
            <p>{text(row.summary, "")}</p>
          </article>
        )) : <Unavailable title="No exact headline match" detail={text(exact.data_gap, "Broad headlines are not relabeled as company news.")} />}
      </div>
    </section>
  );
}

export function ComparisonPanel({ workstation: current }: { workstation: Row }) {
  const comparison = record(current.comparison);
  const points = asRecordArray(comparison.points);
  const chart: Row = {
    chart_id: `${text(comparison.primary_symbol)}-comparison`,
    chart_type: "indicator-line",
    title: `Normalized return vs ${text(comparison.comparison_symbol)}`,
    series: [
      { name: text(comparison.primary_symbol), points: points.map((row) => ({ x: row.x, y: row.primary_return_pct })) },
      { name: text(comparison.comparison_symbol), points: points.map((row) => ({ x: row.x, y: row.comparison_return_pct })) },
    ],
  };
  if (text(comparison.status) !== "available") {
    return <Unavailable title="Comparison unavailable" detail={text(comparison.data_gap, "Enter a verified comparison symbol and reload this panel.")} />;
  }
  return <section className="progressive-detail-panel"><header><div><span className="eyebrow">Normalized performance</span><h3>{text(chart.title)}</h3></div><b>{points.length} overlaps</b></header><FinanceChart chart={chart} /></section>;
}

export function SourcesPanel({ envelope }: { envelope: ContractEnvelope }) {
  const rows = asRecordArray(envelope.source_status);
  return (
    <section className="progressive-detail-panel">
      <header><div><span className="eyebrow">Provenance ledger</span><h3>Sources and freshness</h3></div><b>{rows.length}</b></header>
      <div className="progressive-source-list">
        {rows.map((row, index) => (
          <article key={`${text(row.provider)}-${index}`}>
            <strong>{text(row.provider)}</strong>
            <span className={statusTone(text(row.source_status))}>{text(row.source_status)}</span>
            <small>{shortTime(row.fetched_at)} / {text(row.row_count, "0")} rows</small>
            <p>{text(row.data_gap || row.caveat, "No declared gap")}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function PanelLoading({ panel }: { panel: string }) {
  return <div className="progressive-loading"><RefreshCw size={18} className="spin" /><strong>Loading exact {panel}</strong><span>Other providers are not queried.</span></div>;
}
export function Unavailable({ title, detail }: { title: string; detail: string }) {
  return <div className="progressive-unavailable"><strong>{title}</strong><span>{detail}</span></div>;
}
function Metric({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}
function workstation(envelope: ContractEnvelope | null): Row {
  if (!envelope || !isRecord(envelope.data)) return {};
  return asRecordArray(envelope.data.workstations)[0] ?? {};
}
function record(value: unknown): Row { return isRecord(value) ? value : {}; }
function text(value: unknown, fallback = "unavailable"): string {
  return value === null || value === undefined || value === "" || typeof value === "object" ? fallback : String(value);
}
function numeric(value: unknown): number | null {
  const result = Number(value);
  return value !== null && value !== "" && Number.isFinite(result) ? result : null;
}
function formatPrice(value: unknown): string {
  const current = numeric(value);
  return current === null ? "Unavailable" : new Intl.NumberFormat("en-US", { maximumFractionDigits: current < 10 ? 4 : 2 }).format(current);
}
function formatPercent(value: unknown): string {
  const current = numeric(value);
  return current === null ? "-" : `${current > 0 ? "+" : ""}${current.toFixed(2)}%`;
}
function formatPercentFraction(value: unknown): string {
  const current = numeric(value);
  return current === null ? "unavailable" : `${(current * 100).toFixed(2)}%`;
}
function formatNumber(value: unknown): string {
  const current = numeric(value);
  return current === null ? "unavailable" : new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(current);
}
function compact(value: unknown): string {
  const current = numeric(value);
  return current === null ? "unavailable" : new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(current);
}
function returnTone(value: unknown): string { const current = numeric(value) ?? 0; return current > 0 ? "gain" : current < 0 ? "loss" : "flat"; }
function statusTone(value: string): string {
  return ["fresh", "live/fresh", "cached", "available", "exact"].includes(value) ? "ok" : ["fixture", "stale", "partial"].includes(value) ? "warn" : "danger";
}
function shortTime(value: unknown): string {
  const date = new Date(text(value, ""));
  return Number.isNaN(date.getTime()) ? "unavailable" : new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "UTC" }).format(date);
}
function safeHttp(value: unknown): boolean {
  try {
    const url = new URL(text(value, ""));
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}
function catalystDate(row: Row): string {
  return text(row.event_date || row.ex_dividend_date || row.payment_date, "Date unavailable");
}
function catalystLabel(row: Row): string {
  const event = text(row.event_type, "No scheduled event");
  return event === "scheduled-earnings"
    ? "Earnings"
    : event === "reported-earnings"
      ? "Reported earnings"
      : event === "dividend"
        ? "Ex-dividend"
        : event;
}
function panelForSurface(surface: string): Panel {
  return surface === "financials" || surface === "catalysts" || surface === "news" || surface === "sources"
    ? surface
    : "chart-core";
}
function surfaceForPanel(panel: Panel): string {
  return panel === "chart-core" || panel === "technicals" || panel === "comparison" ? "chart" : panel;
}
