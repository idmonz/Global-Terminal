"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import type { ContractEnvelope, RuntimeMode } from "@/lib/contracts";
import { asRecordArray, isRecord } from "@/lib/contracts";
import { canonicalAssetHref, type ProductAssetClass } from "@/lib/product-routes";

type Row = Record<string, unknown>;
type ActionState = "idle" | "loading" | "captured" | "reviewed" | "error";

const PERIODS = ["morning", "midday", "close", "weekly"] as const;
const SECTIONS = ["overview", "cross_asset", "global_risk", "news_flow", "watchlist", "data_quality"] as const;

export function DailyBriefWorkspace({
  envelope,
  runtimeMode,
  apiBaseUrl,
  period,
  initialSection,
  runtimeWarning,
}: {
  envelope: ContractEnvelope;
  runtimeMode: RuntimeMode;
  apiBaseUrl: string | null;
  period: string;
  initialSection: string;
  runtimeWarning?: string | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [briefEnvelope, setBriefEnvelope] = useState(envelope);
  const [actionState, setActionState] = useState<ActionState>("idle");
  const [actionMessage, setActionMessage] = useState("");
  const [capture, setCapture] = useState<Row | null>(null);
  const [selectedClaimId, setSelectedClaimId] = useState("");
  const data = isRecord(briefEnvelope.data) ? briefEnvelope.data : {};
  const claims = asRecordArray(data.claims);
  const sections = asRecordArray(data.sections);
  const sources = asRecordArray(data.source_register);
  const chartPanels = asRecordArray(data.chart_panels);
  const researchPerspectives = asRecordArray(data.research_perspectives);
  const coverage = isRecord(data.coverage) ? data.coverage : {};
  const comparison = isRecord(data.comparison) ? data.comparison : null;
  const comparisonSummary = comparison && isRecord(comparison.summary) ? comparison.summary : {};
  const headline = isRecord(data.headline) ? data.headline : {};
  const section = normalizeSection(initialSection);
  const visibleClaims = section === "overview" ? claims : claims.filter((row) => row.section_id === section);
  const selectedClaim = claims.find((row) => row.claim_id === selectedClaimId) ?? null;
  const sourceMap = useMemo(() => new Map(sources.map((row) => [String(row.source_id || ""), row])), [sources]);
  const selectedSources = selectedClaim ? (Array.isArray(selectedClaim.source_ids) ? selectedClaim.source_ids : []).map((id) => sourceMap.get(String(id))).filter(isRecord) : [];
  const displayState = runtimeMode === "fixture" ? "fixture" : runtimeWarning ? "fallback" : actionState === "error" ? "error" : actionState === "reviewed" ? "reviewed" : actionState === "captured" ? "captured" : "ready";
  const canPersist = runtimeMode !== "fixture" && Boolean(apiBaseUrl);
  const returnTarget = workspaceReturnTarget(searchParams);

  function setBoundedParam(key: "period" | "section", value: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", "daily-brief");
    params.set("mode", runtimeMode);
    params.set(key, value);
    router.replace(`/?${params.toString()}`, { scroll: false });
  }

  async function refreshBrief() {
    if (!apiBaseUrl || runtimeMode === "fixture") return;
    setActionState("loading");
    setActionMessage("Refreshing source-bound brief...");
    try {
      const response = await fetch(`${apiBaseUrl}/api/daily-brief?mode=${encodeURIComponent(runtimeMode)}&period=${encodeURIComponent(period)}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const next = await response.json() as ContractEnvelope;
      setBriefEnvelope(next);
      setSelectedClaimId("");
      setActionState("idle");
      setActionMessage("Current source contracts refreshed.");
    } catch (error) {
      setActionState("error");
      setActionMessage(`Refresh unavailable: ${error instanceof Error ? error.message : String(error)}. Current fallback remains visible.`);
    }
  }

  async function captureBrief() {
    if (!canPersist || !apiBaseUrl) return;
    setActionState("loading");
    setActionMessage("Capturing normalized claims locally...");
    try {
      const response = await fetch(`${apiBaseUrl}/api/daily-brief/captures`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: runtimeMode, period }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json() as Row;
      const nextCapture = isRecord(result.capture) ? result.capture : null;
      const nextBrief = isRecord(result.brief) ? result.brief as unknown as ContractEnvelope : null;
      setCapture(nextCapture);
      if (nextBrief) setBriefEnvelope(nextBrief);
      setActionState("captured");
      setActionMessage(nextCapture?.deduplicated ? "Identical normalized inputs matched the existing local capture." : "Brief captured in local-private Research Memory storage.");
    } catch (error) {
      setActionState("error");
      setActionMessage(`Capture unavailable: ${error instanceof Error ? error.message : String(error)}.`);
    }
  }

  async function markReviewed() {
    const briefId = String(capture?.brief_id || "");
    if (!apiBaseUrl || !/^brief_[a-f0-9]{20}$/.test(briefId)) return;
    setActionState("loading");
    setActionMessage("Saving local review state...");
    try {
      const response = await fetch(`${apiBaseUrl}/api/daily-brief/captures/${encodeURIComponent(briefId)}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "reviewed" }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setActionState("reviewed");
      setActionMessage("Reviewed state saved locally. No private note entered the URL or fixture.");
    } catch (error) {
      setActionState("error");
      setActionMessage(`Review update unavailable: ${error instanceof Error ? error.message : String(error)}.`);
    }
  }

  return (
    <section
      className="daily-brief-workstation"
      aria-labelledby="daily-brief-title"
      data-daily-brief-state={displayState}
      data-claim-count={claims.length}
      data-source-count={sources.length}
      data-comparison-active={Boolean(comparison)}
    >
      {returnTarget ? <div className="attention-return-bar"><Link prefetch={false} href={returnTarget.href}>{returnTarget.label}</Link><span>{returnTarget.detail}</span></div> : null}
      <header className="daily-brief-header">
        <div>
          <span className="eyebrow">Source-bound morning workflow</span>
          <h2 id="daily-brief-title">Daily Brief</h2>
          <p>{text(headline.text)}</p>
        </div>
        <div className="daily-brief-actions">
          <label>
            <span>Period</span>
            <select value={period} onChange={(event) => setBoundedParam("period", normalizePeriod(event.target.value))}>
              {PERIODS.map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}
            </select>
          </label>
          <button type="button" onClick={refreshBrief} disabled={!canPersist || actionState === "loading"} title="Refresh current source contracts">Refresh</button>
          <button type="button" className="primary" onClick={captureBrief} disabled={!canPersist || actionState === "loading"} title="Capture this source-bound brief locally">Capture brief</button>
          <button type="button" onClick={markReviewed} disabled={!capture || actionState === "loading" || actionState === "reviewed"} title="Mark the local capture reviewed">Mark reviewed</button>
        </div>
      </header>

      <div className="daily-brief-truth-strip" aria-label="Brief source status">
        <Metric label="Source state" value={coverage.source_status} tone={statusTone(coverage.source_status)} />
        <Metric label="Claims" value={claims.length} />
        <Metric label="Sources" value={sources.length} />
        <Metric label="Explicit gaps" value={coverage.gap_count} tone={Number(coverage.gap_count || 0) > 0 ? "warn" : "ok"} />
        <Metric label="Mode" value={runtimeMode} tone={runtimeMode === "fixture" ? "warn" : "neutral"} />
      </div>

      {runtimeWarning ? <div className="daily-brief-notice warn" role="status"><strong>Runtime fallback</strong><span>{runtimeWarning}</span></div> : null}
      {runtimeMode === "fixture" ? <div className="daily-brief-notice fixture" role="status"><strong>Fictional demo</strong><span>This comparison is deterministic product evidence, not observed history. Local capture is disabled in demo mode.</span></div> : null}
      {actionMessage ? <div className={`daily-brief-notice ${actionState}`} role="status"><strong>{titleCase(actionState)}</strong><span>{actionMessage}</span></div> : null}

      <section className="daily-brief-change-strip" aria-labelledby="brief-change-title">
        <div>
          <span className="eyebrow">Captured-prior comparison</span>
          <h3 id="brief-change-title">Changed since prior brief</h3>
        </div>
        {comparison ? (
          <div className="daily-change-metrics">
            <Metric label="Added" value={comparisonSummary.added ?? 0} tone="ok" />
            <Metric label="Changed" value={comparisonSummary.changed ?? 0} tone="warn" />
            <Metric label="Removed" value={comparisonSummary.removed ?? 0} />
            <Metric label="Fetch refresh" value={comparisonSummary.refreshed ?? 0} />
          </div>
        ) : <p>No prior captured brief exists. The product does not invent historical comparison.</p>}
      </section>

      <section className="daily-brief-analysis-grid" aria-label="Daily brief chart and perspective analysis">
        <div className="daily-chart-panel-stack">
          <div className="section-heading">
            <div><span className="eyebrow">Chart drilldowns</span><h3>Source-Bound Charts</h3></div>
            <span>{chartPanels.length} panels</span>
          </div>
          {chartPanels.length ? chartPanels.slice(0, 4).map((panel) => (
            <DailyChartPanel key={String(panel.chart_panel_id || panel.chart_id)} panel={panel} runtimeMode={runtimeMode} />
          )) : <div className="daily-empty"><strong>No chart panels</strong><p>Chart panels appear only when source-bound chart specs are attached.</p></div>}
        </div>

        <div className="daily-perspective-stack">
          <div className="section-heading">
            <div><span className="eyebrow">Clean-room analyst lenses</span><h3>Research Perspectives</h3></div>
            <span>{researchPerspectives.length} lenses</span>
          </div>
          {researchPerspectives.length ? researchPerspectives.map((perspective) => (
            <article className={`daily-perspective-card ${statusTone(perspective.stance)}`} key={String(perspective.perspective_id)}>
              <header>
                <span>{text(perspective.role)}</span>
                <span className={`daily-status-chip ${statusTone(perspective.source_status_counts ? "cached" : perspective.stance)}`}>{text(perspective.stance)}</span>
              </header>
              <strong>{text(perspective.title)}</strong>
              <p>{text(perspective.summary)}</p>
              <div className="daily-perspective-meta">
                <span>{array(perspective.claim_ids).length} claims</span>
                <span>{array(perspective.source_ids).length} sources</span>
                <span>{formatConfidence(perspective.confidence)}</span>
              </div>
              <small>{text(perspective.caveat)}</small>
            </article>
          )) : <div className="daily-empty"><strong>No research perspectives</strong><p>Perspectives are withheld until source-bound claims exist.</p></div>}
        </div>
      </section>

      <nav className="daily-section-tabs" aria-label="Daily brief sections">
        {SECTIONS.map((value) => (
          <button key={value} type="button" className={section === value ? "active" : ""} onClick={() => setBoundedParam("section", value)}>
            {sectionLabel(value, sections)}
          </button>
        ))}
      </nav>

      <div className="daily-brief-body">
        <main className="daily-claim-ledger" aria-label="Claim ledger">
          <div className="section-heading">
            <div><span className="eyebrow">Claim ledger first</span><h3>{titleCase(section.replaceAll("_", " "))}</h3></div>
            <span>{visibleClaims.length} claims</span>
          </div>
          {visibleClaims.length ? visibleClaims.map((claim) => (
            <article className={`daily-claim-card ${statusTone(claim.source_status)}`} key={String(claim.claim_id)} data-claim-kind={String(claim.claim_kind || "unknown")}>
              <header>
                <span className={`daily-status-chip ${statusTone(claim.source_status)}`}>{text(claim.source_status)}</span>
                <span>{titleCase(text(claim.claim_kind).replaceAll("_", " "))}</span>
                <time>{shortDate(claim.observed_at || claim.fetched_at)}</time>
              </header>
              <strong>{text(claim.statement)}</strong>
              <div className="daily-claim-links">
                {array(claim.linked_symbols).slice(0, 4).map((symbol) => <Link key={symbol} href={assetHref(symbol, runtimeMode)}>{symbol}</Link>)}
                {array(claim.linked_regions).slice(0, 3).map((region) => <Link key={region} href={`/?view=war-room-map&mode=${runtimeMode}&region=${encodeURIComponent(region)}`}>{region}</Link>)}
              </div>
              <footer>
                <span>{text(claim.provider)}</span>
                <span>{formatConfidence(claim.confidence)}</span>
                <button type="button" onClick={() => setSelectedClaimId(String(claim.claim_id || ""))} aria-label={`Inspect evidence for ${text(claim.statement)}`}>Inspect evidence</button>
              </footer>
              {claim.claim_kind === "gap" ? <p className="daily-gap-row">{text(claim.data_gap)}</p> : null}
            </article>
          )) : <div className="daily-empty"><strong>No source-bound claims</strong><p>This section remains empty instead of receiving invented analysis.</p></div>}
        </main>

        <aside className="daily-source-drawer" aria-label="Selected claim evidence" data-source-drawer={selectedClaim ? "open" : "closed"}>
          {selectedClaim ? (
            <>
              <header><div><span className="eyebrow">Evidence inspector</span><h3>Claim sources</h3></div><button type="button" onClick={() => setSelectedClaimId("")} aria-label="Close evidence inspector">Close</button></header>
              <p className="daily-selected-statement">{text(selectedClaim.statement)}</p>
              {selectedSources.map((source) => <SourceCard key={String(source.source_id)} source={source} />)}
              <section className="daily-caveat-block"><span>Caveat</span><p>{text(selectedClaim.caveat)}</p><span>Data gap</span><p>{text(selectedClaim.data_gap)}</p></section>
            </>
          ) : (
            <div className="daily-source-placeholder"><span className="eyebrow">Evidence inspector</span><h3>Select a claim</h3><p>Provider, source time, observation time, confidence, caveat and data gap will appear here.</p></div>
          )}
          <div className="daily-memory-return">
            <span className="eyebrow">Research Memory</span>
            <p>Captured review state remains local-private and is stored beside the research archive.</p>
            <Link href="/?view=research-memory&collection=local-research&surface=reports&mode=local">Open Research Memory</Link>
          </div>
        </aside>
      </div>
      <footer className="daily-brief-footer">Research information only. No recommendation, target price, trade approval, broker route or autonomous action.</footer>
    </section>
  );
}

function workspaceReturnTarget(searchParams: Pick<URLSearchParams, "get">): { href: string; label: string; detail: string } | null {
  if ([searchParams.get("origin"), searchParams.get("originView")].includes("alert-manager")) {
    const origin = new URLSearchParams(searchParams.get("originState") ?? "");
    const output = new URLSearchParams({ view: "alert-manager" });
    const mode = origin.get("mode");
    if (["fixture", "cache"].includes(mode ?? "")) output.set("mode", mode as string);
    const tab = origin.get("tab");
    if (["rules", "history", "runs"].includes(tab ?? "")) output.set("tab", tab as string);
    const selectedTrigger = origin.get("selectedTrigger");
    if (/^[A-Za-z0-9_-]{3,80}$/.test(selectedTrigger ?? "")) output.set("selectedTrigger", selectedTrigger as string);
    return { href: `/?${output}`, label: "Return to Alert Manager", detail: "Trigger history and evidence selection preserved" };
  }
  if (![searchParams.get("origin"), searchParams.get("originView")].includes("attention-desk")) return null;
  const origin = new URLSearchParams(searchParams.get("originState") ?? "");
  const output = new URLSearchParams({ view: "attention-desk" });
  const mode = origin.get("mode");
  if (["fixture", "cache"].includes(mode ?? "")) output.set("mode", mode as string);
  const review = origin.get("review");
  if (["needs-review", "all", "reviewed", "acknowledged"].includes(review ?? "")) output.set("review", review as string);
  return { href: `/?${output}`, label: "Return to Attention Desk", detail: "Review filters and queue state preserved" };
}

function DailyChartPanel({ panel, runtimeMode }: { panel: Row; runtimeMode: RuntimeMode }) {
  const chartSpec = isRecord(panel.chart_spec) ? panel.chart_spec : {};
  const seriesRows = asRecordArray(chartSpec.series);
  const points = seriesRows.flatMap((series) => asRecordArray(series.points)).slice(0, 14);
  const values = points.map((point) => Number(point.y)).filter(Number.isFinite);
  const maxAbs = Math.max(1, ...values.map((value) => Math.abs(value)));
  const drilldowns = asRecordArray(panel.primary_drilldowns);

  return (
    <article className="daily-chart-panel" data-chart-type={text(panel.chart_type)}>
      <header>
        <div>
          <strong>{text(panel.title)}</strong>
          <span>{text(panel.provider)} / {text(panel.source_status)} / {text(panel.point_count)} points</span>
        </div>
        <span className={`daily-status-chip ${statusTone(panel.source_status)}`}>{text(panel.source_status)}</span>
      </header>
      <div className="daily-mini-chart" role="img" aria-label={`${text(panel.title)} chart preview`}>
        {points.map((point, index) => {
          const value = Number(point.y);
          const height = Math.max(8, Math.round((Math.abs(value) / maxAbs) * 72));
          return (
            <div className="daily-mini-bar-slot" key={`${text(point.x)}-${index}`}>
              <span
                className={`daily-mini-bar ${value >= 0 ? "positive" : "negative"}`}
                style={{ height: `${height}px` }}
                title={`${text(point.x)} ${Number.isFinite(value) ? value.toFixed(2) : "n/a"}`}
              />
              <small>{text(point.x).slice(0, 8)}</small>
            </div>
          );
        })}
      </div>
      <p>{text(panel.data_gap || panel.caveat)}</p>
      <div className="daily-chart-drilldowns">
        {drilldowns.slice(0, 5).map((link, index) => {
          const href = safeInternalHref(link.href, runtimeMode);
          return href ? <Link key={`${text(link.label)}-${index}`} href={href}>{text(link.label)}</Link> : null;
        })}
      </div>
    </article>
  );
}

function SourceCard({ source }: { source: Row }) {
  const href = safeHttpUrl(source.source_url);
  return <article className="daily-source-card"><header><strong>{text(source.provider)}</strong><span className={`daily-status-chip ${statusTone(source.source_status)}`}>{text(source.source_status)}</span></header><p>{text(source.source)}</p><dl><div><dt>Observed</dt><dd>{shortDate(source.observed_at)}</dd></div><div><dt>Fetched</dt><dd>{shortDate(source.fetched_at)}</dd></div><div><dt>Confidence</dt><dd>{formatConfidence(source.confidence)}</dd></div><div><dt>Freshness</dt><dd>{text(source.freshness)}</dd></div></dl>{href ? <a href={href} target="_blank" rel="noreferrer">Open primary/source record</a> : <span className="daily-no-source">No public URL supplied</span>}</article>;
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: unknown; tone?: string }) {
  return <div className={`daily-metric ${tone}`}><span>{label}</span><strong>{text(value)}</strong></div>;
}

function sectionLabel(value: string, sections: Row[]): string {
  if (value === "overview") return "Overview";
  return text(sections.find((row) => row.section_id === value)?.title || titleCase(value.replaceAll("_", " ")));
}

function normalizePeriod(value: string): string { return PERIODS.includes(value as (typeof PERIODS)[number]) ? value : "morning"; }
function normalizeSection(value: string): string { return SECTIONS.includes(value as (typeof SECTIONS)[number]) ? value : "overview"; }
function text(value: unknown): string { return value === null || value === undefined || value === "" ? "n/a" : String(value); }
function array(value: unknown): string[] { return Array.isArray(value) ? value.map(String).filter(Boolean) : []; }
function shortDate(value: unknown): string { const date = new Date(String(value || "")); return Number.isNaN(date.getTime()) ? "n/a" : new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date); }
function formatConfidence(value: unknown): string { const number = Number(value); return Number.isFinite(number) ? `${Math.round(number * 100)}% confidence` : "confidence n/a"; }
function titleCase(value: string): string { return value.replace(/\b\w/g, (match) => match.toUpperCase()); }
function statusTone(value: unknown): "ok" | "warn" | "danger" | "neutral" { const status = String(value || "").toLowerCase(); if (status.includes("live") || status === "fresh") return "ok"; if (status.includes("unavailable") || status.includes("missing") || status.includes("forbidden")) return "danger"; if (status.includes("stale") || status.includes("fixture") || status.includes("proxy") || status.includes("cached")) return "warn"; return "neutral"; }
function safeHttpUrl(value: unknown): string | null { try { const url = new URL(String(value || "")); return ["http:", "https:"].includes(url.protocol) ? url.toString() : null; } catch { return null; } }
function safeInternalHref(value: unknown, runtimeMode: RuntimeMode): string | null {
  const textValue = String(value || "");
  if (!textValue.startsWith("/?")) return null;
  const url = new URL(textValue, "http://127.0.0.1");
  if (!url.searchParams.get("mode")) url.searchParams.set("mode", runtimeMode);
  return `${url.pathname}${url.search}`;
}
function assetHref(symbol: string, mode: RuntimeMode): string { const upper = symbol.toUpperCase(); const assetClass: ProductAssetClass = upper.endsWith("USDT") || ["BTC", "ETH", "SOL"].includes(upper) ? "crypto" : ["SPY", "QQQ", "IWM", "TLT", "GLD"].includes(upper) ? "etf" : "equity"; const normalized = assetClass === "crypto" && !upper.endsWith("USDT") ? `${upper}USDT` : upper; return canonicalAssetHref(normalized, assetClass, "1d", mode); }
