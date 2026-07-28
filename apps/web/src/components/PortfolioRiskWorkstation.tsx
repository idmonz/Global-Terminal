"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";

import {
  type ContractEnvelope,
  type RuntimeMode,
  asRecordArray,
  isRecord,
} from "@/lib/contracts";

type Surface = "overview" | "performance" | "risk" | "correlation" | "factors" | "attribution" | "stress";

const SURFACES: { key: Surface; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "performance", label: "Performance" },
  { key: "risk", label: "Risk" },
  { key: "correlation", label: "Correlation" },
  { key: "factors", label: "Factors" },
  { key: "attribution", label: "Attribution" },
  { key: "stress", label: "Stress" },
];

export function PortfolioRiskWorkstation({
  envelope,
  runtimeMode,
}: {
  envelope: ContractEnvelope;
  runtimeMode: RuntimeMode;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const data = isRecord(envelope.data) ? envelope.data : {};
  const summary = record(data.summary);
  const portfolio = record(data.portfolio);
  const performance = record(data.performance);
  const risk = record(data.risk);
  const correlation = record(data.correlation);
  const factors = record(data.factors);
  const attribution = record(data.attribution);
  const allocation = record(data.allocation);
  const privacy = record(data.privacy);
  const holdings = asRecordArray(data.holdings);
  const stressRows = asRecordArray(data.stress_tests);
  const sourceRows = asRecordArray(data.source_register);
  const gaps = stringArray(data.data_gaps);
  const requestedSurface = searchParams.get("surface") as Surface | null;
  const surface = SURFACES.some((item) => item.key === requestedSurface) ? requestedSurface! : "overview";
  const period = searchParams.get("period") || String(portfolio.period || "1y");
  const benchmark = searchParams.get("benchmark") || String(portfolio.benchmark || "SPY");
  const performanceRows = asRecordArray(performance.series);
  const drawdownRows = asRecordArray(performance.drawdown_series);
  const metrics = record(risk.metrics);
  const sourceStatus = String(summary.source_status || "unavailable");
  const isReady = holdings.length > 0 && Number(summary.total_market_value || 0) > 0;

  function updateState(next: Partial<{ surface: Surface; period: string; benchmark: string }>) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", "portfolio-risk");
    params.set("portfolio", String(portfolio.portfolio_id || "demo-core"));
    params.set("mode", runtimeMode);
    params.set("surface", next.surface || surface);
    params.set("period", next.period || period);
    params.set("benchmark", next.benchmark || benchmark);
    router.replace("/?" + params.toString(), { scroll: false });
  }

  if (!isReady) {
    return (
      <section className="portfolio-product portfolio-unavailable" data-portfolio-state="unavailable">
        <header className="portfolio-product-header">
          <div>
            <span className="eyebrow">Privacy-safe research portfolio</span>
            <h2>Portfolio And Risk</h2>
            <p>Valuation is unavailable because the selected source returned no usable prices.</p>
          </div>
          <SourceBadge status={sourceStatus} />
        </header>
        <div className="portfolio-empty-state">
          <strong>No fabricated performance</strong>
          <p>{gaps[0] || "Switch to deterministic demo mode or retry the local runtime provider."}</p>
          <Link href="/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY&mode=fixture">
            Open fictional demo
          </Link>
        </div>
      </section>
    );
  }

  const simpleMethod = record(record(performance.methods).simple);
  return (
    <section
      className="portfolio-product"
      data-portfolio-state="ready"
      data-holdings-count={holdings.length}
      data-performance-points={performanceRows.length}
      data-correlation-cells={asNestedArray(correlation.matrix).flat().length}
    >
      <header className="portfolio-product-header">
        <div>
          <span className="eyebrow">Research portfolio / {String(portfolio.base_currency || "USD")}</span>
          <h2>{String(portfolio.display_name || "Portfolio And Risk")}</h2>
          <p>Valuation, performance and model evidence with explicit coverage. Private position values never enter the URL.</p>
        </div>
        <div className="portfolio-header-status">
          <SourceBadge status={sourceStatus} />
          <span>{formatTimestamp(summary.as_of)}</span>
          <small>{String(privacy.classification || "unknown")}</small>
        </div>
      </header>

      <div className="portfolio-kpi-strip">
        <Metric label="Known value" value={formatCurrency(summary.total_market_value)} detail={String(summary.base_currency || "USD")} />
        <Metric label="Valuation coverage" value={formatPercentPoint(summary.valuation_coverage_pct)} detail={String(summary.priced_holding_count || 0) + "/" + String(summary.holding_count || 0) + " holdings"} />
        <Metric label="Period return" value={formatPercent(simpleMethod.value)} detail={String(performance.sample_count || 0) + " sessions"} tone={toneForNumber(simpleMethod.value)} />
        <Metric label="Annualized vol" value={formatMagnitudePercent(metrics.annualized_volatility)} detail={String(risk.annualization || 252) + "x"} />
        <Metric label="Max drawdown" value={formatPercent(metrics.max_drawdown)} detail="historical" tone="negative" />
        <Metric label="History coverage" value={formatPercentPoint(summary.history_coverage_pct)} detail={benchmark} />
      </div>

      <div className="portfolio-command-row">
        <label>
          Window
          <select value={period} onChange={(event) => updateState({ period: event.target.value })}>
            <option value="6mo">6 months</option>
            <option value="1y">1 year</option>
            <option value="3y">3 years</option>
            <option value="5y">5 years</option>
          </select>
        </label>
        <label>
          Benchmark
          <select value={benchmark} onChange={(event) => updateState({ benchmark: event.target.value })}>
            <option value="SPY">SPY</option>
            <option value="QQQ">QQQ</option>
            <option value="ACWI">ACWI</option>
          </select>
        </label>
        <span className="portfolio-method-note">Complete overlap · no missing-return zero fill · 252-day annualization</span>
      </div>

      <nav className="portfolio-surface-tabs" aria-label="Portfolio analysis surface">
        {SURFACES.map((item) => (
          <button
            key={item.key}
            type="button"
            className={surface === item.key ? "active" : ""}
            onClick={() => updateState({ surface: item.key })}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {surface === "overview" ? (
        <OverviewSurface allocation={allocation} performanceRows={performanceRows} drawdownRows={drawdownRows} performance={performance} risk={risk} holdings={holdings} runtimeMode={runtimeMode} />
      ) : null}
      {surface === "performance" ? <PerformanceSurface performance={performance} rows={performanceRows} drawdownRows={drawdownRows} /> : null}
      {surface === "risk" ? <RiskSurface risk={risk} attribution={attribution} /> : null}
      {surface === "correlation" ? <CorrelationSurface correlation={correlation} /> : null}
      {surface === "factors" ? <FactorSurface factors={factors} /> : null}
      {surface === "attribution" ? <AttributionSurface attribution={attribution} /> : null}
      {surface === "stress" ? <StressSurface rows={stressRows} /> : null}

      <section className="portfolio-truth-strip">
        <div>
          <strong>Coverage & privacy</strong>
          <span>{sourceRows.length} source register · {gaps.length} declared gap{gaps.length === 1 ? "" : "s"}</span>
        </div>
        <div className="portfolio-truth-items">
          <span>Symbols-only provider requests</span>
          <span>No external AI transmission</span>
          <span>No rebalance or execution path</span>
        </div>
      </section>
    </section>
  );
}

function OverviewSurface({
  allocation,
  performanceRows,
  drawdownRows,
  performance,
  risk,
  holdings,
  runtimeMode,
}: {
  allocation: Record<string, unknown>;
  performanceRows: Record<string, unknown>[];
  drawdownRows: Record<string, unknown>[];
  performance: Record<string, unknown>;
  risk: Record<string, unknown>;
  holdings: Record<string, unknown>[];
  runtimeMode: RuntimeMode;
}) {
  const assetAllocation = asRecordArray(allocation.by_asset_class);
  const metrics = record(risk.metrics);
  return (
    <div className="portfolio-overview">
      <div className="portfolio-overview-grid">
        <article className="portfolio-panel portfolio-performance-panel">
          <PanelHeading eyebrow="Performance" title="Portfolio vs benchmark" meta={String(performance.benchmark || "SPY")} />
          <PerformanceChart rows={performanceRows} />
          <DrawdownBand rows={drawdownRows} />
        </article>
        <article className="portfolio-panel portfolio-allocation-panel">
          <PanelHeading eyebrow="Allocation" title="Known value mix" meta={String(assetAllocation.length) + " sleeves"} />
          <AllocationDonut rows={assetAllocation} />
        </article>
        <article className="portfolio-panel portfolio-risk-panel">
          <PanelHeading eyebrow="Risk" title="Current sample" meta={String(risk.sample_count || 0) + " obs"} />
          <div className="portfolio-risk-metrics">
            <Metric label="VaR 95%" value={formatMagnitudePercent(metrics.historical_var_95_daily)} detail="daily historical" />
            <Metric label="CVaR 95%" value={formatMagnitudePercent(metrics.historical_cvar_95_daily)} detail="daily historical" />
            <Metric label="Beta" value={formatNumber(metrics.beta_vs_benchmark, 2)} detail="vs benchmark" />
            <Metric label="Largest weight" value={formatMagnitudePercent(metrics.largest_position_weight)} detail="known value" />
          </div>
        </article>
      </div>
      <HoldingsTable rows={holdings} runtimeMode={runtimeMode} compact />
    </div>
  );
}

function PerformanceSurface({
  performance,
  rows,
  drawdownRows,
}: {
  performance: Record<string, unknown>;
  rows: Record<string, unknown>[];
  drawdownRows: Record<string, unknown>[];
}) {
  const metrics = record(performance.metrics);
  const methods = record(performance.methods);
  return (
    <div className="portfolio-analysis-grid">
      <article className="portfolio-panel portfolio-wide-panel">
        <PanelHeading eyebrow="Linked daily returns" title="Growth of 100" meta={String(rows.length) + " points"} />
        <PerformanceChart rows={rows} />
      </article>
      <article className="portfolio-panel">
        <PanelHeading eyebrow="Drawdown" title="Peak-to-trough path" meta="decimal return" />
        <DrawdownBand rows={drawdownRows} large />
      </article>
      <article className="portfolio-panel">
        <PanelHeading eyebrow="Methodology" title="Return methods" meta="cash-flow aware" />
        <dl className="portfolio-definition-list">
          <Definition label="Simple" value={formatPercent(record(methods.simple).value)} />
          <Definition label="Time weighted" value={formatPercent(record(methods.time_weighted).value)} />
          <Definition label="Money weighted" value="Unavailable" />
          <Definition label="CAGR" value={formatPercent(metrics.cagr)} />
          <Definition label="Tracking error" value={formatPercent(metrics.tracking_error)} />
        </dl>
        <p className="portfolio-caveat">{String(performance.missing_data_policy || "")}</p>
      </article>
    </div>
  );
}

function RiskSurface({ risk, attribution }: { risk: Record<string, unknown>; attribution: Record<string, unknown> }) {
  const metrics = record(risk.metrics);
  return (
    <div className="portfolio-analysis-grid">
      <article className="portfolio-panel portfolio-wide-panel">
        <PanelHeading eyebrow="Historical risk" title="Risk metric board" meta={String(risk.sample_count || 0) + " observations"} />
        <div className="portfolio-metric-board">
          {Object.entries(metrics).map(([key, value]) => (
            <Metric
              key={key}
              label={humanize(key)}
              value={
                key.includes("beta") || key.includes("sharpe") || key.includes("sortino")
                  ? formatNumber(value, 2)
                  : key.includes("max_drawdown")
                    ? formatPercent(value)
                    : formatMagnitudePercent(value)
              }
              detail={key.includes("var") || key.includes("cvar") ? "daily" : key.includes("volatility") ? "annualized" : "historical"}
            />
          ))}
        </div>
      </article>
      <article className="portfolio-panel portfolio-wide-panel">
        <PanelHeading eyebrow="Contribution" title="Share of portfolio volatility" meta="complete covariance" />
        <ContributionBars rows={asRecordArray(attribution.risk_contribution)} valueKey="risk_contribution" />
      </article>
    </div>
  );
}

function CorrelationSurface({ correlation }: { correlation: Record<string, unknown> }) {
  const assets = stringArray(correlation.assets);
  const matrix = asNestedArray(correlation.matrix);
  const counts = asNestedArray(correlation.pairwise_sample_counts);
  if (!correlation.available) {
    return <UnavailablePanel title="Correlation unavailable" detail={String(correlation.data_gap || "Insufficient overlapping history.")} />;
  }
  return (
    <article className="portfolio-panel portfolio-correlation-panel">
      <PanelHeading eyebrow="Pearson / pairwise complete" title="Correlation matrix" meta={"min " + String(correlation.minimum_observed_samples || 0) + " samples"} />
      <div className="portfolio-correlation-scroll">
        <div className="portfolio-correlation-grid" style={{ gridTemplateColumns: "88px repeat(" + assets.length + ", minmax(62px, 1fr))" }}>
          <span />
          {assets.map((asset) => <strong key={"head-" + asset}>{asset}</strong>)}
          {assets.map((asset, rowIndex) => [
            <strong key={"row-" + asset}>{asset}</strong>,
            ...assets.map((column, columnIndex) => {
              const value = numberOrNull(matrix[rowIndex]?.[columnIndex]);
              const sample = Number(counts[rowIndex]?.[columnIndex] || 0);
              return (
                <span
                  key={asset + "-" + column}
                  className="portfolio-correlation-cell"
                  style={{ backgroundColor: correlationColor(value) }}
                  title={asset + " / " + column + ": " + (value === null ? "n/a" : value.toFixed(3)) + ", n=" + sample}
                >
                  {value === null ? "—" : value.toFixed(2)}
                  <small>{sample}</small>
                </span>
              );
            }),
          ])}
        </div>
      </div>
      <p className="portfolio-caveat">{String(correlation.caveat || "")}</p>
    </article>
  );
}

function FactorSurface({ factors }: { factors: Record<string, unknown> }) {
  const rows = asRecordArray(factors.exposures);
  if (!factors.available) {
    return <UnavailablePanel title="Factor model unavailable" detail={String(factors.data_gap || "Insufficient proxy history.")} />;
  }
  return (
    <div className="portfolio-analysis-grid">
      <article className="portfolio-panel portfolio-wide-panel">
        <PanelHeading eyebrow="Public proxy OLS" title="Factor exposure" meta={"R² " + formatNumber(factors.r_squared, 2)} />
        <div className="portfolio-factor-bars">
          {rows.map((row) => {
            const beta = Number(row.beta || 0);
            return (
              <div className="portfolio-factor-row" key={String(row.factor)}>
                <span>{String(row.factor)}</span>
                <div><i style={{ width: String(Math.min(100, Math.abs(beta) * 55)) + "%" }} className={beta >= 0 ? "positive" : "negative"} /></div>
                <strong>{beta.toFixed(2)}</strong>
                <small>{String(row.proxy_symbol)}</small>
              </div>
            );
          })}
        </div>
      </article>
      <article className="portfolio-panel">
        <PanelHeading eyebrow="Model fit" title="Explained vs residual" meta={String(factors.sample_count || 0) + " obs"} />
        <dl className="portfolio-definition-list">
          <Definition label="Annualized alpha" value={formatPercent(factors.alpha_annualized)} />
          <Definition label="Residual" value={formatPercent(factors.residual_annualized)} />
          <Definition label="Unexplained share" value={formatPercentPoint(factors.unexplained_share_pct)} />
          <Definition label="Model" value={String(factors.model || "unavailable")} />
        </dl>
      </article>
      <article className="portfolio-panel">
        <PanelHeading eyebrow="Boundary" title="Interpretation" meta="non-causal" />
        <p className="portfolio-caveat">{String(factors.caveat || "")}</p>
        <p className="portfolio-caveat">Public ETF and asset proxies are not licensed institutional factor series.</p>
      </article>
    </div>
  );
}

function AttributionSurface({ attribution }: { attribution: Record<string, unknown> }) {
  if (!attribution.available) {
    return <UnavailablePanel title="Attribution unavailable" detail={String(attribution.data_gap || "Insufficient history.")} />;
  }
  return (
    <div className="portfolio-analysis-grid">
      <article className="portfolio-panel portfolio-wide-panel">
        <PanelHeading eyebrow="Arithmetic contribution" title="Return contribution by holding" meta={String(attribution.sample_count || 0) + " obs"} />
        <ContributionBars rows={asRecordArray(attribution.return_contribution)} valueKey="return_contribution" />
      </article>
      <article className="portfolio-panel">
        <PanelHeading eyebrow="Reconciliation" title="Geometric residual" meta={attribution.reconciled ? "reconciled" : "review"} />
        <dl className="portfolio-definition-list">
          <Definition label="Portfolio return" value={formatPercent(attribution.portfolio_total_return)} />
          <Definition label="Arithmetic total" value={formatPercent(attribution.arithmetic_contribution_total)} />
          <Definition label="Compounding residual" value={formatPercent(attribution.residual)} />
          <Definition label="Unexplained share" value={formatPercentPoint(attribution.unexplained_share_pct)} />
        </dl>
      </article>
      <article className="portfolio-panel">
        <PanelHeading eyebrow="Risk" title="Volatility contribution" meta="share" />
        <ContributionBars rows={asRecordArray(attribution.risk_contribution)} valueKey="risk_contribution" />
      </article>
    </div>
  );
}

function StressSurface({ rows }: { rows: Record<string, unknown>[] }) {
  return (
    <article className="portfolio-panel portfolio-stress-panel">
      <PanelHeading eyebrow="Bounded research scenarios" title="Historical replay and hypothetical shocks" meta={String(rows.length) + " scenarios"} />
      <div className="portfolio-table-scroll">
        <table className="portfolio-table">
          <thead>
            <tr><th>Scenario</th><th>Type</th><th>Impact</th><th>Window / assumptions</th><th>Boundary</th></tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row.scenario)}>
                <td><strong>{String(row.scenario)}</strong></td>
                <td><StatusToken value={String(row.scenario_type || "unknown")} /></td>
                <td className={Number(row.estimated_portfolio_impact || 0) < 0 ? "negative-text" : "positive-text"}>{formatPercent(row.estimated_portfolio_impact)}</td>
                <td>{stressAssumption(row)}</td>
                <td>{String(row.caveat || "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function HoldingsTable({ rows, runtimeMode, compact = false }: { rows: Record<string, unknown>[]; runtimeMode: RuntimeMode; compact?: boolean }) {
  return (
    <article className="portfolio-panel portfolio-holdings-panel">
      <PanelHeading eyebrow="Valuation" title="Holdings" meta={String(rows.length) + " rows"} />
      <div className="portfolio-table-scroll">
        <table className="portfolio-table">
          <thead>
            <tr><th>Holding</th><th>Class</th><th>Qty</th><th>Price</th><th>Market value</th><th>Weight</th><th>Change vs cost</th><th>Source</th></tr>
          </thead>
          <tbody>
            {rows.slice(0, compact ? 8 : rows.length).map((row) => {
              const href = holdingHref(String(row.symbol), runtimeMode);
              return (
                <tr key={String(row.holding_id || row.symbol)} className={row.price_available ? "" : "missing-row"}>
                  <td>
                    {href ? <Link href={href}><strong>{String(row.symbol)}</strong></Link> : <strong>{String(row.symbol)}</strong>}
                    <small>{String(row.name || "")}</small>
                  </td>
                  <td>{String(row.asset_class || "")}</td>
                  <td>{formatNumber(row.quantity, 4)}</td>
                  <td>{formatCurrency(row.price)}</td>
                  <td>{formatCurrency(row.market_value)}</td>
                  <td>{formatMagnitudePercent(row.weight)}</td>
                  <td className={toneForNumber(row.unrealized_change) === "negative" ? "negative-text" : "positive-text"}>{formatCurrency(row.unrealized_change)}</td>
                  <td><StatusToken value={String(row.source_status || "unavailable")} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function PerformanceChart({ rows }: { rows: Record<string, unknown>[] }) {
  const geometry = useMemo(() => chartGeometry(rows, "portfolio_index"), [rows]);
  const benchmark = useMemo(() => chartGeometry(rows, "benchmark_index", geometry.bounds), [rows, geometry.bounds]);
  if (rows.length < 2) return <div className="portfolio-chart-empty">Insufficient performance history.</div>;
  return (
    <div className="portfolio-performance-chart" data-chart-ready={geometry.points ? "true" : "false"}>
      <svg viewBox="0 0 900 260" role="img" aria-label="Portfolio and benchmark performance chart">
        <line x1="28" x2="882" y1="230" y2="230" className="chart-axis" />
        <line x1="28" x2="28" y1="18" y2="230" className="chart-axis" />
        <path d={geometry.area} className="portfolio-area" />
        <polyline points={geometry.points} className="portfolio-line" />
        {benchmark.points ? <polyline points={benchmark.points} className="benchmark-line" /> : null}
      </svg>
      <div className="portfolio-chart-legend"><span className="portfolio-legend-line" /> Portfolio <span className="benchmark-legend-line" /> Benchmark</div>
    </div>
  );
}

function DrawdownBand({ rows, large = false }: { rows: Record<string, unknown>[]; large?: boolean }) {
  const geometry = useMemo(() => chartGeometry(rows, "drawdown", { min: -0.25, max: 0 }), [rows]);
  return (
    <div className={"portfolio-drawdown-band" + (large ? " large" : "")}>
      <svg viewBox="0 0 900 120" role="img" aria-label="Portfolio drawdown chart">
        <line x1="28" x2="882" y1="18" y2="18" className="chart-axis" />
        <path d={geometry.area} className="drawdown-area" />
        <polyline points={geometry.points} className="drawdown-line" />
      </svg>
    </div>
  );
}

function AllocationDonut({ rows }: { rows: Record<string, unknown>[] }) {
  const colors = ["#2dd4bf", "#60a5fa", "#fbbf24", "#f472b6", "#a78bfa", "#94a3b8"];
  return (
    <div className="portfolio-allocation-viz">
      <svg viewBox="0 0 180 180" role="img" aria-label="Portfolio allocation donut">
        <circle cx="90" cy="90" r="58" className="donut-track" />
        {rows.map((row, index) => {
          const weight = Math.max(0, Number(row.weight || 0));
          const dash = weight * 364.42;
          const offset = rows
            .slice(0, index)
            .reduce((total, prior) => total + Math.max(0, Number(prior.weight || 0)) * 364.42, 0);
          const element = (
            <circle
              key={String(row.label)}
              cx="90"
              cy="90"
              r="58"
              className="donut-segment"
              stroke={colors[index % colors.length]}
              strokeDasharray={String(dash) + " " + String(364.42 - dash)}
              strokeDashoffset={-offset}
            />
          );
          return element;
        })}
        <text x="90" y="86" textAnchor="middle">ALLOC</text>
        <text x="90" y="106" textAnchor="middle">{rows.length} sleeves</text>
      </svg>
      <div className="portfolio-allocation-legend">
        {rows.map((row, index) => (
          <div key={String(row.label)}>
            <i style={{ backgroundColor: colors[index % colors.length] }} />
            <span>{String(row.label)}</span>
            <strong>{formatMagnitudePercent(row.weight)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function ContributionBars({ rows, valueKey }: { rows: Record<string, unknown>[]; valueKey: string }) {
  const max = Math.max(...rows.map((row) => Math.abs(Number(row[valueKey] || 0))), 0.0001);
  return (
    <div className="portfolio-contribution-bars">
      {rows.map((row) => {
        const value = Number(row[valueKey] || 0);
        return (
          <div key={String(row.symbol)}>
            <span>{String(row.symbol)}</span>
            <div><i className={value >= 0 ? "positive" : "negative"} style={{ width: String(Math.abs(value) / max * 100) + "%" }} /></div>
            <strong>{formatPercent(value)}</strong>
          </div>
        );
      })}
    </div>
  );
}

function PanelHeading({ eyebrow, title, meta }: { eyebrow: string; title: string; meta: string }) {
  return <header className="portfolio-panel-heading"><div><span>{eyebrow}</span><h3>{title}</h3></div><small>{meta}</small></header>;
}

function Metric({ label, value, detail, tone = "neutral" }: { label: string; value: string; detail: string; tone?: string }) {
  return <div className={"portfolio-metric " + tone}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

function Definition({ label, value }: { label: string; value: string }) {
  return <><dt>{label}</dt><dd>{value}</dd></>;
}

function SourceBadge({ status }: { status: string }) {
  return <span className={"portfolio-source-badge " + status.replace(/[^a-z]+/gi, "-").toLowerCase()}>{status}</span>;
}

function StatusToken({ value }: { value: string }) {
  return <span className={"portfolio-status-token " + value.replace(/[^a-z]+/gi, "-").toLowerCase()}>{value}</span>;
}

function UnavailablePanel({ title, detail }: { title: string; detail: string }) {
  return <article className="portfolio-panel portfolio-unavailable-panel"><span className="eyebrow">Data gate</span><h3>{title}</h3><p>{detail}</p></article>;
}

function chartGeometry(rows: Record<string, unknown>[], key: string, fixedBounds?: { min: number; max: number }) {
  const values = rows.map((row) => numberOrNull(row[key]));
  const valid = values.filter((value): value is number => value !== null);
  const bounds = fixedBounds || {
    min: valid.length ? Math.min(...valid) : 0,
    max: valid.length ? Math.max(...valid) : 1,
  };
  const span = bounds.max - bounds.min || 1;
  const pointList = values.map((value, index) => {
    if (value === null) return null;
    const x = 28 + index / Math.max(1, rows.length - 1) * 854;
    const y = 230 - (value - bounds.min) / span * 212;
    return x.toFixed(2) + "," + y.toFixed(2);
  }).filter((value): value is string => Boolean(value));
  const points = pointList.join(" ");
  const first = pointList[0] || "28,230";
  const last = pointList.at(-1) || "882,230";
  const area = points ? "M " + first + " L " + pointList.slice(1).join(" L ") + " L " + last.split(",")[0] + ",230 L " + first.split(",")[0] + ",230 Z" : "";
  return { points, area, bounds };
}

function correlationColor(value: number | null): string {
  if (value === null) return "rgba(100,116,139,.16)";
  const strength = Math.min(0.82, 0.16 + Math.abs(value) * 0.66);
  return value >= 0 ? "rgba(20,184,166," + strength + ")" : "rgba(244,63,94," + strength + ")";
}

function holdingHref(symbol: string, mode: RuntimeMode): string | null {
  if (symbol === "AAPL") return "/?view=asset&symbol=AAPL&assetClass=equity&timeframe=1D&mode=" + mode;
  if (symbol === "BTC-USD") return "/?view=asset&symbol=BTCUSDT&assetClass=crypto&timeframe=1D&mode=" + mode;
  return null;
}

function stressAssumption(row: Record<string, unknown>): string {
  const window = record(row.window);
  if (window.start && window.end) return String(window.start) + " → " + String(window.end) + " · " + String(window.sessions) + " sessions";
  const shocks = record(row.assumed_shocks);
  const parts = Object.entries(shocks).slice(0, 4).map(([key, value]) => key + " " + formatPercent(value));
  return parts.join(" · ") || "Explicit deterministic shock table";
}

function record(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function asNestedArray(value: unknown): unknown[][] {
  return Array.isArray(value) ? value.map((row) => Array.isArray(row) ? row : []) : [];
}

function numberOrNull(value: unknown): number | null {
  const number = Number(value);
  return value === null || value === undefined || value === "" || !Number.isFinite(number) ? null : number;
}

function formatCurrency(value: unknown): string {
  const number = numberOrNull(value);
  if (number === null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: Math.abs(number) < 100 ? 2 : 0 }).format(number);
}

function formatPercent(value: unknown): string {
  const number = numberOrNull(value);
  return number === null ? "—" : (number > 0 ? "+" : "") + (number * 100).toFixed(2) + "%";
}

function formatMagnitudePercent(value: unknown): string {
  const number = numberOrNull(value);
  return number === null ? "—" : (Math.abs(number) * 100).toFixed(2) + "%";
}

function formatPercentPoint(value: unknown): string {
  const number = numberOrNull(value);
  return number === null ? "—" : number.toFixed(1) + "%";
}

function formatNumber(value: unknown, digits = 2): string {
  const number = numberOrNull(value);
  return number === null ? "—" : number.toLocaleString("en-US", { maximumFractionDigits: digits });
}

function formatTimestamp(value: unknown): string {
  if (!value) return "No valuation timestamp";
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.valueOf()) ? String(value) : "As of " + parsed.toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

function toneForNumber(value: unknown): "positive" | "negative" | "neutral" {
  const number = numberOrNull(value);
  return number === null || number === 0 ? "neutral" : number > 0 ? "positive" : "negative";
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
