import Link from "next/link";

import { FinanceChart } from "@/components/FinanceChart";
import { type ContractEnvelope, type RuntimeMode, asRecordArray, isRecord } from "@/lib/contracts";
import { canonicalAssetHref, type AssetChartType, type AssetSurface, type ProductAssetContext } from "@/lib/product-routes";

type Row = Record<string, unknown>;
interface SourcePosture { available: number; fixture: number; gaps: number; }

const SURFACES: { key: AssetSurface; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "chart", label: "Chart" },
  { key: "financials", label: "Financials" },
  { key: "options", label: "Options" },
  { key: "news", label: "News" },
  { key: "sources", label: "Sources" },
];
const PANEL_LABELS: Record<string, string> = {
  trend: "Trend",
  momentum: "Momentum",
  risk: "Risk",
  comparison: "Compare",
  financials: "Financials",
  news: "News",
  asset: "Asset context",
  sources: "Sources",
};

export function SymbolWorkstation({
  envelope,
  context,
  runtimeMode,
  forceChartFallback,
}: {
  envelope: ContractEnvelope;
  context: ProductAssetContext;
  runtimeMode: RuntimeMode;
  forceChartFallback: boolean;
}) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const workstation = asRecordArray(data.workstations)[0];
  if (!workstation) return <UnknownState context={context} />;

  const identity = record(workstation.identity);
  const request = record(workstation.request);
  const quote = record(workstation.quote);
  const clock = record(workstation.market_clock);
  const technical = record(workstation.technical_analysis);
  const technicalSummary = record(technical.summary);
  const chartViews = record(workstation.chart_views);
  const priceChart = record(chartViews.price);
  const analysisCharts = asRecordArray(chartViews.analysis);
  const financial = record(workstation.financial_context);
  const marketMapContext = record(workstation.market_map_context);
  const capabilityPlan = record(workstation.capability_plan);
  const derivatives = record(workstation.crypto_derivatives);
  const derivativeMetrics = record(derivatives.metrics);
  const comparison = record(workstation.comparison);
  const exactNews = record(workstation.exact_news);
  const news = asRecordArray(exactNews.rows);
  const summary = record(workstation.summary);
  const history = asRecordArray(workstation.history);
  const sources = asRecordArray(workstation.source_register);
  const capabilities = asRecordArray(data.capabilities);
  const capability = capabilities.find((row) => text(row.asset_class) === context.assetClass) ?? {};
  const intervals = stringList(capability.intervals);
  const ranges = stringList(record(capability.ranges_by_interval)[context.interval]);
  const activeSurfaces = SURFACES.filter((item) => {
    if (item.key === "financials") return context.assetClass !== "crypto";
    if (item.key === "options") return context.assetClass === "equity";
    return true;
  });
  const status = text(summary.status, "unavailable");
  const sourceStatus = text(summary.source_status, "unavailable");
  const marketStatus = text(clock.market_data_status, "unavailable");
  const originId = `asset-${context.assetClass}-${context.symbol}`;
  const sourcePosture = buildSourcePosture(sources);
  const compareOverlap = Number(comparison.overlap_count || 0);
  const marketContextRows = context.assetClass === "crypto"
    ? [
        ["Mark", formatMetric(derivativeMetrics.mark_price)],
        ["Index", formatMetric(derivativeMetrics.index_price)],
        ["Basis", formatPercent(derivativeMetrics.basis_pct)],
        ["Funding", formatPercentRatio(derivativeMetrics.funding_rate)],
        ["Open interest", compactNumber(derivativeMetrics.open_interest_contracts)],
        ["Coverage", derivatives.availability],
      ] as [string, unknown][]
    : financialMetrics(financial, identity);

  return (
    <section
      className="symbol-workstation"
      aria-labelledby="symbol-workstation-title"
      data-phase5v-symbol-desk="true"
      data-symbol-workstation-state={status}
      data-symbol={context.symbol}
      data-chart-rows={String(history.length)}
      data-chart-type={context.chartType}
      data-market-data-status={marketStatus}
      data-comparison-overlap={text(comparison.overlap_count, "0")}
      data-exact-news-count={String(news.length)}
      data-identity-origin={text(identity.identity_origin, "reviewed-static")}
      data-market-map-sector={text(marketMapContext.sector, text(identity.sector))}
      data-market-map-conflict={String(Boolean(marketMapContext.classification_conflict))}
      data-provider-call-budget={text(capabilityPlan.maximum_provider_calls, "0")}
      data-broad-rebuild={String(Boolean(capabilityPlan.broad_universe_rebuild))}
    >
      <header className="symbol-identity-header">
        <div className="symbol-identity-copy">
          <div className="symbol-route-row">
            <Link href={`/?view=home&mode=${runtimeMode}`}>Market Home</Link>
            <span>{text(identity.exchange)}</span>
            <span>{text(identity.asset_class)}</span>
            <span>{text(identity.currency)}</span>
          </div>
          <h2 id="symbol-workstation-title"><code>{text(identity.symbol)}</code> {text(identity.name)}</h2>
          <p>{text(identity.sector, "Cross-asset")} / {text(identity.industry, "Source-scoped market instrument")}</p>
        </div>
        <div className="symbol-price-block">
          <span>{text(request.effective_interval, context.interval)} / {text(request.effective_range, context.range)}</span>
          <strong>{formatPrice(quote.last_price, text(identity.currency))}</strong>
          <b className={returnTone(quote.change_pct)}>{formatSignedPercent(quote.change_pct)}</b>
          <small>{marketStatus} / {text(quote.provider)}</small>
          <small>market {shortTimestamp(clock.market_data_as_of)} / retrieved {shortTimestamp(clock.retrieved_at)}</small>
        </div>
      </header>

      <SymbolDeskStrip
        context={context}
        sourceStatus={sourceStatus}
        marketStatus={marketStatus}
        historyRows={history.length}
        compareOverlap={compareOverlap}
        newsRows={news.length}
        sourcePosture={sourcePosture}
        financial={financial}
        derivatives={derivatives}
      />
      <IdentityEvidenceStrip
        identity={identity}
        marketMapContext={marketMapContext}
        capabilityPlan={capabilityPlan}
      />

      <div className="symbol-control-deck">
        <nav aria-label="Asset workstation surfaces">
          {activeSurfaces.map((surface) => (
            <Link key={surface.key} className={context.surface === surface.key ? "active" : ""} href={assetHref(context, runtimeMode, { surface: surface.key })}>
              {surface.label}
            </Link>
          ))}
        </nav>
        <div className="symbol-capability-controls">
          <ControlGroup label="Chart">
            {(["candlestick", "line"] as AssetChartType[]).map((chartType) => <Link key={chartType} className={context.chartType === chartType ? "active" : ""} href={assetHref(context, runtimeMode, { chartType })}>{chartType === "candlestick" ? "Candles" : "Line"}</Link>)}
          </ControlGroup>
          <ControlGroup label="Interval">
            {intervals.map((interval) => <Link key={interval} className={context.interval === interval ? "active" : ""} href={assetHref(context, runtimeMode, { interval, range: firstRange(capability, interval) })}>{interval}</Link>)}
          </ControlGroup>
          <ControlGroup label="Range">
            {ranges.map((range) => <Link key={range} className={context.range === range ? "active" : ""} href={assetHref(context, runtimeMode, { range })}>{range}</Link>)}
          </ControlGroup>
        </div>
      </div>

      <div className="symbol-secondary-controls">
        <div className="symbol-panel-toggles" aria-label="Visible analysis panels">
          {Object.entries(PANEL_LABELS).map(([panel, label]) => {
            const active = context.panels.includes(panel);
            const next = active ? context.panels.filter((item) => item !== panel) : [...context.panels, panel];
            return <Link key={panel} className={active ? "active" : ""} href={assetHref(context, runtimeMode, { panels: next })}>{label}</Link>;
          })}
        </div>
        <div className="symbol-compare-control" aria-label="Comparison symbol">
          <span>Compare</span>
          {comparisonOptions(context).map((symbol) => <Link key={symbol || "none"} className={context.compare === symbol ? "active" : ""} href={assetHref(context, runtimeMode, { compare: symbol })}>{symbol || "None"}</Link>)}
        </div>
      </div>

      <div className={`symbol-runtime-strip ${sourceTone(sourceStatus)}`}>
        <span><b>{sourceStatus}</b> {status}</span>
        <span>{marketStatus}</span>
        <span>market {shortTimestamp(clock.market_data_as_of)}</span>
        <span>retrieved {shortTimestamp(clock.retrieved_at)}</span>
        <span>{history.length} OHLCV rows</span>
        <small>{text(clock.caveat)}</small>
      </div>

      {context.surface === "sources" ? (
        <SourceSurface rows={sources} />
      ) : context.surface === "news" ? (
        <NewsSurface rows={news} symbol={context.symbol} exactNews={exactNews} />
      ) : context.surface === "financials" ? (
        <FinancialSurface row={financial} identity={identity} />
      ) : context.surface === "options" && context.assetClass === "equity" ? (
        <OptionsBridgeSurface identity={identity} context={context} financial={financial} sources={sources} runtimeMode={runtimeMode} />
      ) : (
        <>
          <div className="symbol-primary-grid">
            <section className="symbol-chart-panel" aria-labelledby="symbol-chart-title">
              <header>
                <div><span className="eyebrow">Verified OHLCV / {context.chartType}</span><h3 id="symbol-chart-title">{context.symbol} Price + Volume</h3></div>
                <span>{history.length} rows / {text(technical.formula_version)}</span>
              </header>
              {forceChartFallback || !Object.keys(priceChart).length ? (
                <div className="finance-chart-shell fallback" data-chart-state="fallback" data-chart-points="0"><div className="finance-chart-status">Chart fallback requested or no plottable rows</div></div>
              ) : <FinanceChart key={`${context.symbol}-${context.interval}-${context.range}-${context.chartType}-${runtimeMode}`} chart={priceChart} />}
            </section>
            <aside className="symbol-market-context">
              <span className="eyebrow">{context.assetClass === "crypto" ? "Futures context" : "Source-backed snapshot"}</span>
              <MetricList rows={marketContextRows} />
              <p>{text(context.assetClass === "crypto" ? derivatives.caveat : financial.caveat)}</p>
              <small>{text(context.assetClass === "crypto" ? derivatives.data_gap : financial.data_gap, "No declared panel gap")}</small>
              <SourceMiniLedger rows={sources} posture={sourcePosture} />
              <div className="symbol-action-stack">
                <Link href={`/?view=research-memory&collection=demo-research&surface=inbox&mode=demo&originId=${encodeURIComponent(originId)}`}>Save research snapshot</Link>
                {context.originView === "war-room-map" && context.originState ? (
                  <Link href={`/?view=war-room-map&${context.originState}`}>Return to selected map event</Link>
                ) : context.assetClass !== "crypto" ? (
                  <Link href={context.originView === "market-map" && context.originState
                    ? `/?view=market-map&${context.originState}`
                    : `/?view=market-map&selected=${encodeURIComponent(context.symbol)}&mode=${runtimeMode}`}>
                    {context.originView === "market-map" ? "Return to saved screen state" : "Open in Market Map"}
                  </Link>
                ) : null}
                {context.assetClass === "equity" ? <Link href={`/?view=options-quant&symbol=${encodeURIComponent(context.symbol)}&surface=chain&mode=${runtimeMode}`}>Options Quant</Link> : null}
              </div>
            </aside>
          </div>

          <section className="symbol-technical-tape" aria-label="Current historical indicators">
            <TapeMetric label="SMA 20" value={formatMetric(technicalSummary.sma_20)} />
            <TapeMetric label="EMA 20" value={formatMetric(technicalSummary.ema_20)} />
            <TapeMetric label="RSI 14" value={formatMetric(technicalSummary.rsi_14)} />
            <TapeMetric label="MACD" value={formatMetric(technicalSummary.macd_12_26_9)} />
            <TapeMetric label="Realized vol" value={formatPercentRatio(technicalSummary.realized_volatility_20)} />
            <TapeMetric label="Drawdown" value={formatPercentRatio(technicalSummary.drawdown)} tone={returnTone(technicalSummary.drawdown)} />
          </section>

          <AnalysisGrid charts={analysisCharts} panels={context.panels} comparison={comparison} />

          {context.surface === "overview" ? (
            <div className="symbol-intelligence-grid phase5v-context-grid" data-phase5v-context-cards="true">
              <CompactContextCard marker={context.assetClass === "crypto" ? "crypto-derivatives" : "financials"} title={context.assetClass === "crypto" ? "Derivatives boundary" : "Financial availability"} status={text(context.assetClass === "crypto" ? derivatives.availability : financial.availability)} rows={context.assetClass === "crypto" ? [["Funding", formatPercentRatio(derivativeMetrics.funding_rate)], ["Basis", formatPercent(derivativeMetrics.basis_pct)], ["OI", compactNumber(derivativeMetrics.open_interest_contracts)]] : financialMetrics(financial, identity).slice(0, 4)} caveat={text(context.assetClass === "crypto" ? derivatives.data_gap : financial.data_gap, "No declared gap")} />
              <CompactNewsCard rows={news} exactNews={exactNews} symbol={context.symbol} />
              <CompactContextCard marker="comparison" title="Comparison" status={text(comparison.status)} rows={[["Against", comparison.comparison_symbol], ["Overlap", comparison.overlap_count], ["Method", comparison.alignment_method]]} caveat={text(comparison.data_gap, text(comparison.caveat))} />
              <EventContextCard context={context} runtimeMode={runtimeMode} rows={news} exactNews={exactNews} originId={originId} />
              {context.assetClass === "equity" ? (
                <OptionsBridgeCard context={context} runtimeMode={runtimeMode} financial={financial} />
              ) : context.assetClass === "crypto" ? (
                <CryptoDerivativesCard derivatives={derivatives} metrics={derivativeMetrics} />
              ) : (
                <FundProfileCard context={context} runtimeMode={runtimeMode} financial={financial} />
              )}
              <SourcePostureCard posture={sourcePosture} rows={sources} />
            </div>
          ) : null}
        </>
      )}

      <footer className="symbol-disclosure"><span>Read-only research</span><p>{text(quote.caveat)} {text(quote.data_gap, "")} {text(clock.caveat)}</p></footer>
    </section>
  );
}

function AnalysisGrid({ charts, panels, comparison }: { charts: Row[]; panels: string[]; comparison: Row }) {
  const visible = charts.filter((chart) => {
    const id = text(chart.chart_id);
    if (id.endsWith(".rsi") || id.endsWith(".macd")) return panels.includes("momentum");
    if (id.endsWith(".risk")) return panels.includes("risk");
    if (id.endsWith(".comparison")) return panels.includes("comparison") || Boolean(comparison.comparison_symbol);
    return true;
  });
  if (!visible.length) return null;
  return <section className="symbol-analysis-grid" aria-label="Technical analysis panes">{visible.map((chart) => <article className="symbol-analysis-card" key={text(chart.chart_id)}><header><h3>{text(chart.title)}</h3><span>{text(chart.formula)}</span></header><FinanceChart chart={chart} /></article>)}</section>;
}

function SymbolDeskStrip({
  context,
  sourceStatus,
  marketStatus,
  historyRows,
  compareOverlap,
  newsRows,
  sourcePosture,
  financial,
  derivatives,
}: {
  context: ProductAssetContext;
  sourceStatus: string;
  marketStatus: string;
  historyRows: number;
  compareOverlap: number;
  newsRows: number;
  sourcePosture: SourcePosture;
  financial: Row;
  derivatives: Row;
}) {
  const deskMode = context.assetClass === "crypto" ? "Crypto desk" : context.assetClass === "etf" ? "ETF desk" : "Equity desk";
  const contextStatus: string = context.assetClass === "crypto" ? text(derivatives.availability) : text(financial.availability);
  const contextLabel = context.assetClass === "crypto" ? "Derivatives" : context.assetClass === "equity" ? "Options / financials" : "Fund profile";
  return (
    <section className="symbol-desk-strip" aria-label="Symbol intelligence desk summary" data-phase5v-desk-strip="true">
      <div><span>Desk</span><strong>{deskMode}</strong><small>{context.symbol} / {context.interval} / {context.range}</small></div>
      <div><span>Source</span><strong className={sourceTone(sourceStatus)}>{sourceStatus}</strong><small>{marketStatus}</small></div>
      <div><span>Chart rows</span><strong>{historyRows}</strong><small>OHLCV observations</small></div>
      <div><span>Compare</span><strong>{compareOverlap}</strong><small>{context.compare || "none"}</small></div>
      <div><span>News</span><strong>{newsRows}</strong><small>exact-symbol rows</small></div>
      <div><span>{contextLabel}</span><strong>{contextStatus}</strong><small>{sourcePosture.available} live / {sourcePosture.fixture} fixture / {sourcePosture.gaps} gaps</small></div>
    </section>
  );
}

function IdentityEvidenceStrip({
  identity,
  marketMapContext,
  capabilityPlan,
}: {
  identity: Row;
  marketMapContext: Row;
  capabilityPlan: Row;
}) {
  const conflict = Boolean(marketMapContext.classification_conflict);
  return (
    <section className="symbol-identity-evidence" aria-label="Exact identity and capability evidence" data-phase6c-identity-evidence="true">
      <div><span>Identity</span><strong>{text(identity.identity_origin, "reviewed-static")}</strong><small>{text(identity.listing_status)} / {text(identity.security_type)}</small></div>
      <div><span>Venue</span><strong>{text(identity.mic, "MIC unavailable")}</strong><small>{text(identity.exchange)}</small></div>
      <div><span>SEC CIK</span><strong>{text(identity.cik, "unavailable")}</strong><small>{text(identity.sec_source_status)}</small></div>
      <div><span>Classification</span><strong>{text(marketMapContext.sector, text(identity.sector))}</strong><small>{text(marketMapContext.classification_source_status, text(identity.source_status))}</small></div>
      <div><span>Conflict</span><strong className={conflict ? "warn" : "positive"}>{conflict ? "preserved" : "none"}</strong><small>{text(marketMapContext.provider_sector, "no provider label")}</small></div>
      <div><span>Fetch plan</span><strong>{text(capabilityPlan.maximum_provider_calls, "0")} max</strong><small>{capabilityPlan.broad_universe_rebuild === false ? "selected symbol only" : "inspect plan"}</small></div>
    </section>
  );
}

function CompactNewsCard({ rows, exactNews, symbol }: { rows: Row[]; exactNews: Row; symbol: string }) {
  return <section className="symbol-intelligence-card" data-phase5v-context-card="news"><header><div><span className="eyebrow">Exact-match news</span><h3>{symbol} headlines</h3></div><span>{rows.length} / {text(exactNews.source_status)}</span></header>{rows.length ? rows.slice(0, 3).map((row) => <a className="symbol-news-compact-row" href={safeHttp(row.source_url) ? text(row.source_url) : undefined} target="_blank" rel="noreferrer" key={text(row.title)}><strong>{text(row.title)}</strong><small>{text(row.provider)} / {shortTimestamp(row.published_at)}</small></a>) : <p>{text(exactNews.data_gap, "No exact symbol/name match returned.")}</p>}</section>;
}

function CompactContextCard({ title, status, rows, caveat, marker = "context" }: { title: string; status: string; rows: [string, unknown][]; caveat: string; marker?: string }) {
  return <section className="symbol-intelligence-card" data-phase5v-context-card={marker}><header><div><span className="eyebrow">Source-aware panel</span><h3>{title}</h3></div><span>{status}</span></header><MetricList rows={rows} /><p>{caveat}</p></section>;
}

function EventContextCard({ context, runtimeMode, rows, exactNews, originId }: { context: ProductAssetContext; runtimeMode: RuntimeMode; rows: Row[]; exactNews: Row; originId: string }) {
  const eventHref = `/?view=war-room-map&mode=${runtimeMode}&selected=${encodeURIComponent(context.symbol)}`;
  const newsHref = `/?view=news&mode=${runtimeMode}&topic=${encodeURIComponent(context.symbol)}&originId=${encodeURIComponent(originId)}`;
  return (
    <section className="symbol-intelligence-card symbol-link-card" data-phase5v-context-card="events-news">
      <header><div><span className="eyebrow">News / event context</span><h3>Intelligence links</h3></div><span>{rows.length} rows</span></header>
      <p>{rows.length ? `Exact symbol news is available from ${text(exactNews.provider, "public feeds")}.` : text(exactNews.data_gap, "No exact headline match; broad market news is not relabeled.")}</p>
      <div className="symbol-card-links">
        <Link href={newsHref}>Open News desk</Link>
        <Link href={eventHref}>Open War Map</Link>
      </div>
    </section>
  );
}

function OptionsBridgeCard({ context, runtimeMode, financial }: { context: ProductAssetContext; runtimeMode: RuntimeMode; financial: Row }) {
  return (
    <section className="symbol-intelligence-card symbol-link-card" data-phase5v-context-card="equity-options" data-phase5v-equity-options="true">
      <header><div><span className="eyebrow">Options boundary</span><h3>Options Quant bridge</h3></div><span>{text(financial.availability)}</span></header>
      <p>Open the source-bounded options workspace for chain quality, IV, Greeks and scenario views. No OPRA-grade completeness or trade action is implied.</p>
      <div className="symbol-card-links"><Link href={`/?view=options-quant&symbol=${encodeURIComponent(context.symbol)}&surface=chain&mode=${runtimeMode}`}>Open Options Quant</Link></div>
    </section>
  );
}

function CryptoDerivativesCard({ derivatives, metrics }: { derivatives: Row; metrics: Row }) {
  return (
    <section className="symbol-intelligence-card" data-phase5v-context-card="crypto-derivatives" data-phase5v-crypto-derivatives="true">
      <header><div><span className="eyebrow">Crypto derivatives</span><h3>Funding and basis</h3></div><span>{text(derivatives.availability)}</span></header>
      <MetricList rows={[["Funding", formatPercentRatio(metrics.funding_rate)], ["Basis", formatPercent(metrics.basis_pct)], ["Open interest", compactNumber(metrics.open_interest_contracts)]]} />
      <p>{text(derivatives.caveat)} {text(derivatives.data_gap, "")}</p>
    </section>
  );
}

function FundProfileCard({ context, runtimeMode, financial }: { context: ProductAssetContext; runtimeMode: RuntimeMode; financial: Row }) {
  return (
    <section className="symbol-intelligence-card symbol-link-card" data-phase5v-context-card="fund-profile">
      <header><div><span className="eyebrow">ETF / fund boundary</span><h3>Fund profile context</h3></div><span>{text(financial.availability)}</span></header>
      <p>ETF rows use fund/profile availability and market-map peer context. Company financial statements and crypto derivatives are not applied to ETFs.</p>
      <div className="symbol-card-links">
        <Link href={`/?view=market-map&selected=${encodeURIComponent(context.symbol)}&mode=${runtimeMode}`}>Open Market Map</Link>
      </div>
    </section>
  );
}

function SourcePostureCard({ posture, rows }: { posture: SourcePosture; rows: Row[] }) {
  return (
    <section className="symbol-intelligence-card" data-phase5v-context-card="sources">
      <header><div><span className="eyebrow">Source ledger</span><h3>Provider posture</h3></div><span>{posture.available} live / {posture.fixture} fixture</span></header>
      <MetricList rows={[["Live/cached/available", posture.available], ["Fixture/static", posture.fixture], ["Gaps", posture.gaps], ["Providers", rows.length]]} />
      <p>Use the Sources tab for full provenance, source URLs, fetch times, caveats and unavailable rows.</p>
    </section>
  );
}

function SourceMiniLedger({ rows, posture }: { rows: Row[]; posture: SourcePosture }) {
  return (
    <section className="symbol-source-mini-ledger" aria-label="Compact source ledger" data-phase5v-source-ledger="true">
      <header><span>Source ledger</span><b>{posture.available} live / {posture.fixture} fixture</b></header>
      {rows.slice(0, 4).map((row, index) => (
        <div key={`${text(row.provider)}-${index}`}>
          <span>{text(row.provider)}</span>
          <b className={sourceTone(text(row.source_status))}>{text(row.source_status)}</b>
          <small>{text(row.row_count, "0")} rows</small>
        </div>
      ))}
    </section>
  );
}

function OptionsBridgeSurface({ identity, context, financial, sources, runtimeMode }: { identity: Row; context: ProductAssetContext; financial: Row; sources: Row[]; runtimeMode: RuntimeMode }) {
  const optionsSources = sources.filter((row) => text(row.provider).toLowerCase().includes("option") || text(row.source).toLowerCase().includes("option"));
  return (
    <section className="symbol-options-surface" data-phase5v-equity-options="true">
      <header>
        <span className="eyebrow">Options intelligence boundary</span>
        <h3>{text(identity.symbol)} options bridge</h3>
        <p>Chain, IV, Greeks and scenarios live in the Options Quant workspace. This bridge is source-aware and does not claim full OPRA coverage, execution, order routing or recommendations.</p>
      </header>
      <div className="symbol-options-grid">
        <CompactContextCard marker="options-availability" title="Availability" status={optionsSources.length ? "linked-provider" : "provider-required"} rows={[["Financial context", financial.availability], ["Linked source rows", optionsSources.length], ["Underlying", context.symbol], ["Mode", runtimeMode]]} caveat={optionsSources.length ? "Options rows are represented in the source register." : "No verified options chain is embedded in this symbol fixture; open Options Quant for the bounded chain workflow."} />
        <section className="symbol-intelligence-card symbol-link-card">
          <header><div><span className="eyebrow">Workspace jump</span><h3>Options Quant</h3></div><span>read-only</span></header>
          <p>Open IV smile, term structure, Greeks, gamma exposure proxy and scenario panes with quality flags.</p>
          <div className="symbol-card-links"><Link href={`/?view=options-quant&symbol=${encodeURIComponent(context.symbol)}&surface=overview&mode=${runtimeMode}`}>Open analytics overview</Link><Link href={`/?view=options-quant&symbol=${encodeURIComponent(context.symbol)}&surface=chain&mode=${runtimeMode}`}>Open chain</Link></div>
        </section>
      </div>
    </section>
  );
}

function SourceSurface({ rows }: { rows: Row[] }) {
  return <section className="symbol-tabular-surface"><header><span className="eyebrow">Truth register</span><h3>Sources and availability</h3></header><div><table><thead><tr><th>Provider</th><th>Status</th><th>Rows</th><th>Fetched</th><th>Caveat / gap</th><th>Source</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${text(row.provider)}-${index}`}><td><strong>{text(row.provider)}</strong><small>{text(row.source)}</small></td><td><span className={`source-chip ${sourceTone(text(row.source_status))}`}>{text(row.source_status)}</span></td><td>{text(row.row_count, "0")}</td><td>{shortTimestamp(row.fetched_at)}</td><td><span>{text(row.caveat)}</span><small>{text(row.data_gap)}</small></td><td>{safeHttp(row.source_url) ? <a href={text(row.source_url)} target="_blank" rel="noreferrer">Open</a> : "No public URL"}</td></tr>)}</tbody></table></div></section>;
}

function NewsSurface({ rows, symbol, exactNews }: { rows: Row[]; symbol: string; exactNews: Row }) {
  if (!rows.length) return <section className="symbol-empty-surface"><span className="eyebrow">Symbol-scoped news</span><h3>No verified {symbol} headline match</h3><p>Broad market headlines are not relabeled as company or asset news.</p><small>{text(exactNews.data_gap)}</small></section>;
  return <section className="symbol-news-grid">{rows.map((row, index) => <article key={`${text(row.title)}-${index}`}><div><span>{text(row.source_status, text(exactNews.source_status))}</span><small>{text(row.provider)} / {shortTimestamp(row.published_at)}</small></div><h3>{safeHttp(row.source_url) ? <a href={text(row.source_url)} target="_blank" rel="noreferrer">{text(row.title)}</a> : text(row.title)}</h3><p>{text(row.summary)}</p><small>matched {stringList(row.match_terms).join(", ")}</small></article>)}</section>;
}

function FinancialSurface({ row, identity }: { row: Row; identity: Row }) {
  const statements = record(row.statements);
  const statementRows: Row[] = Object.entries(statements).flatMap(([kind, value]) => asRecordArray(value).map((item) => ({ kind, ...item })));
  const breadth = record(row.provider_breadth);
  const providerRows = asRecordArray(breadth.provider_rows);
  const breadthMetrics = record(breadth.metrics);
  const breadthProfile = record(breadth.profile);
  const sec = record(row.sec_facts);
  const secFacts = latestSecFacts(asRecordArray(sec.facts));
  const earnings = record(row.earnings_calendar);
  const earningsRows = asRecordArray(earnings.rows).slice(0, 8);
  return (
    <section className="symbol-financial-surface">
      <header><span className="eyebrow">Source-bounded fundamentals</span><h3>{text(identity.symbol)} {text(row.context_type)}</h3><p>Company statements are not applied to ETFs or crypto. Missing values remain empty.</p></header>
      <div className="symbol-financial-top-grid">
        <MetricList rows={financialMetrics(row, identity)} />
        {providerRows.length ? (
          <section className="symbol-provider-breadth" data-phase5x-equity-provider-breadth="true" aria-label="Free provider equity breadth">
            <header>
              <div><span className="eyebrow">Free provider breadth</span><h4>Alpha Vantage / Finnhub context</h4></div>
              <span className={`source-chip ${sourceTone(text(breadth.source_status))}`}>{text(breadth.source_status)}</span>
            </header>
            <MetricList rows={[
              ["Alpha PE", formatMetric(breadthMetrics.alpha_pe_ratio)],
              ["Alpha revenue TTM", compactNumber(breadthMetrics.alpha_revenue_ttm)],
              ["Alpha ROE", formatPercentRatio(breadthMetrics.alpha_return_on_equity)],
              ["Finnhub mkt cap", compactNumber(Number(breadthMetrics.finnhub_market_cap_musd || 0) * 1_000_000 || null)],
              ["Industry", breadthProfile.finnhub_industry || breadthProfile.alpha_industry],
              ["Provider coverage", breadth.availability],
            ]} />
            <div className="symbol-provider-row-grid">
              {providerRows.map((provider, index) => (
                <article key={`${text(provider.provider)}-${index}`}>
                  <strong>{text(provider.provider)}</strong>
                  <span className={sourceTone(text(provider.source_status))}>{text(provider.source_status)}</span>
                  <small>{text(provider.source)} / {text(provider.row_count, "0")} rows / {shortTimestamp(provider.fetched_at)}</small>
                  <p>{text(provider.data_gap || provider.caveat, "No declared provider gap")}</p>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </div>
      <div className="symbol-financial-evidence-grid">
        <section
          className="symbol-sec-facts"
          data-phase6a-sec-facts="true"
          data-sec-fact-count={String(asRecordArray(sec.facts).length)}
          data-sec-fact-status={text(sec.source_status)}
        >
          <header>
            <div><span className="eyebrow">Official filing facts</span><h4>SEC company facts</h4></div>
            <span className={`source-chip ${sourceTone(text(sec.source_status))}`}>{text(sec.source_status)}</span>
          </header>
          {secFacts.length ? (
            <div className="symbol-evidence-table-wrap">
              <table>
                <thead><tr><th>Fact</th><th>Period</th><th>Value / unit</th><th>Filing</th></tr></thead>
                <tbody>{secFacts.map((fact) => (
                  <tr key={`${text(fact.concept)}-${text(fact.accession)}-${text(fact.end)}`}>
                    <td><strong>{text(fact.contract_label, text(fact.label))}</strong><small>{text(fact.concept)}</small></td>
                    <td><span>{text(fact.fiscal_year)} {text(fact.fiscal_period, "")}</span><small>{text(fact.start, "instant")} to {text(fact.end)}</small></td>
                    <td><strong>{compactNumber(fact.value)}</strong><small>{text(fact.unit)}</small></td>
                    <td><span>{text(fact.form)}</span><small>filed {text(fact.filed)}</small></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : <div className="symbol-financial-gap">No reviewed SEC filing facts are available. {text(sec.data_gap, "")}</div>}
          <p>{text(sec.caveat)}</p>
        </section>
        <section
          className="symbol-earnings-calendar"
          data-phase6a-earnings-calendar="true"
          data-earnings-row-count={String(earningsRows.length)}
          data-earnings-status={text(earnings.source_status)}
        >
          <header>
            <div><span className="eyebrow">Reported / scheduled</span><h4>Earnings calendar</h4></div>
            <span className={`source-chip ${sourceTone(text(earnings.source_status))}`}>{text(earnings.source_status)}</span>
          </header>
          {earningsRows.length ? (
            <div className="symbol-earnings-list">
              {earningsRows.map((event, index) => (
                <article key={`${text(event.provider)}-${text(event.event_date)}-${index}`}>
                  <div><strong>{text(event.event_date)}</strong><span>{text(event.event_type)}</span></div>
                  <dl>
                    <div><dt>Reported EPS</dt><dd>{formatMetric(event.reported_eps)}</dd></div>
                    <div><dt>Estimate</dt><dd>{formatMetric(event.estimated_eps)}</dd></div>
                    <div><dt>Quarter</dt><dd>{text(event.fiscal_quarter, text(event.fiscal_period_end))}</dd></div>
                  </dl>
                  <small>{text(event.provider)} / {text(event.event_time_code, "time unspecified")} / {text(event.source_status)}</small>
                </article>
              ))}
            </div>
          ) : <div className="symbol-financial-gap">No verified earnings or calendar rows. {text(earnings.data_gap, "")}</div>}
          <p>{text(earnings.caveat)}</p>
        </section>
      </div>
      {statementRows.length ? <div className="symbol-statement-grid">{statementRows.map((item, index) => <article key={`${text(item.kind)}-${text(item.period)}-${index}`}><span>{text(item.kind)} / {shortTimestamp(item.period)}</span>{Object.entries(item).filter(([key]) => !["kind", "period"].includes(key)).map(([key, value]) => <div key={key}><small>{label(key)}</small><strong>{compactNumber(value)}</strong></div>)}</article>)}</div> : <div className="symbol-financial-gap">No provider statement periods returned.</div>}
      <footer><p>{text(row.caveat)}</p><small>{text(row.data_gap, "No declared panel gap")}</small></footer>
    </section>
  );
}

function ControlGroup({ label: title, children }: { label: string; children: React.ReactNode }) { return <label><span>{title}</span><span className="segmented-control">{children}</span></label>; }
function MetricList({ rows }: { rows: [string, unknown][] }) { return <dl className="symbol-metric-list">{rows.map(([title, value]) => <div key={title}><dt>{title}</dt><dd>{text(value)}</dd></div>)}</dl>; }
function TapeMetric({ label: title, value, tone = "flat" }: { label: string; value: string; tone?: string }) { return <div><span>{title}</span><strong className={tone}>{value}</strong></div>; }
function UnknownState({ context }: { context: ProductAssetContext }) { return <section className="symbol-empty-surface" data-symbol-workstation-state="unknown-symbol"><span className="eyebrow danger-text">Unavailable / unknown-symbol</span><h2>No verified workspace for {context.symbol}</h2><p>The bounded registry did not resolve this symbol and no AAPL/BTC fixture was substituted.</p></section>; }

function assetHref(context: ProductAssetContext, mode: RuntimeMode, override: Partial<ProductAssetContext>): string {
  const next = { ...context, ...override };
  return canonicalAssetHref(next.symbol, next.assetClass, next.interval, mode, next.surface, next.range, {
    chartType: next.chartType,
    panels: next.panels,
    compare: next.compare,
    originView: next.originView,
    originState: next.originState,
  });
}
function comparisonOptions(context: ProductAssetContext): string[] { const rows = context.assetClass === "crypto" ? ["", "BTCUSDT", "ETHUSDT"] : ["", "SPY", "QQQ"]; return rows.filter((row) => !row || row !== context.symbol); }
function financialMetrics(row: Row, identity: Row): [string, unknown][] { const metrics = record(row.metrics); return [["Context", row.context_type], ["Name", identity.name], ["Market cap / AUM", compactNumber(metrics.market_cap ?? metrics.total_assets)], ["Trailing P/E", formatMetric(metrics.trailing_pe)], ["Forward P/E", formatMetric(metrics.forward_pe)], ["Revenue growth", formatPercentRatio(metrics.revenue_growth)], ["Profit margin", formatPercentRatio(metrics.profit_margin)], ["Coverage", row.availability]]; }
function latestSecFacts(rows: Row[]): Row[] {
  const seen = new Set<string>();
  return rows.filter((row) => {
    const concept = text(row.concept, "");
    if (!concept || seen.has(concept)) return false;
    seen.add(concept);
    return true;
  }).slice(0, 10);
}
function record(value: unknown): Row { return isRecord(value) ? value : {}; }
function stringList(value: unknown): string[] { return Array.isArray(value) ? value.map((item) => text(item)).filter(Boolean) : []; }
function text(value: unknown, fallback = "unavailable") { return value === null || value === undefined || value === "" || typeof value === "object" ? fallback : String(value); }
function numeric(value: unknown): number | null { const result = Number(value); return value !== null && value !== "" && Number.isFinite(result) ? result : null; }
function returnTone(value: unknown) { const current = numeric(value) ?? 0; return current > 0 ? "gain" : current < 0 ? "loss" : "flat"; }
function sourceTone(value: string) { return value === "live/fresh" || value === "cached" || value === "available" ? "ok" : value === "fixture" || value === "stale" || value === "static/proxy" || value === "partial" ? "warn" : "danger"; }
function formatSignedPercent(value: unknown) { const current = numeric(value); return current === null ? "-" : `${current > 0 ? "+" : ""}${current.toFixed(2)}%`; }
function formatPrice(value: unknown, currency: string) { const current = numeric(value); return current === null ? "Unavailable" : `${new Intl.NumberFormat("en-US", { maximumFractionDigits: current < 10 ? 4 : 2 }).format(current)} ${currency}`; }
function formatMetric(value: unknown) { const current = numeric(value); return current === null ? "unavailable" : new Intl.NumberFormat("en-US", { maximumFractionDigits: Math.abs(current) < 10 ? 3 : 2 }).format(current); }
function formatPercent(value: unknown) { const current = numeric(value); return current === null ? "unavailable" : `${current.toFixed(3)}%`; }
function formatPercentRatio(value: unknown) { const current = numeric(value); return current === null ? "unavailable" : `${(current * 100).toFixed(2)}%`; }
function compactNumber(value: unknown) { const current = numeric(value); return current === null ? "unavailable" : new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(current); }
function shortTimestamp(value: unknown) { const date = new Date(text(value, "")); return Number.isNaN(date.getTime()) ? "unavailable" : new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "UTC", timeZoneName: "short" }).format(date); }
function safeHttp(value: unknown) { try { const url = new URL(text(value, "")); return url.protocol === "https:" || url.protocol === "http:"; } catch { return false; } }
function firstRange(capability: Row, interval: string) { return stringList(record(capability.ranges_by_interval)[interval])[0] || "3mo"; }
function label(value: string) { return value.replaceAll("_", " "); }

function buildSourcePosture(rows: Row[]): SourcePosture {
  return rows.reduce<SourcePosture>(
    (acc, row) => {
      const status = text(row.source_status);
      if (status === "live/fresh" || status === "cached" || status === "available") acc.available += 1;
      else if (status === "fixture" || status === "static/proxy" || status === "stale") acc.fixture += 1;
      else acc.gaps += 1;
      return acc;
    },
    { available: 0, fixture: 0, gaps: 0 },
  );
}
