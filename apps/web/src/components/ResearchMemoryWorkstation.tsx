"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

import type { ContractEnvelope } from "@/lib/contracts";
import { canonicalAssetHref, type ProductAssetClass } from "@/lib/product-routes";

type MemoryMode = "demo" | "local";
type MemorySurface = "inbox" | "watchlists" | "notes" | "reports" | "sources";
type Row = Record<string, unknown>;

const SURFACES: { key: MemorySurface; label: string; detail: string }[] = [
  { key: "inbox", label: "Inbox", detail: "Recent research" },
  { key: "watchlists", label: "Watchlists", detail: "Tracked context" },
  { key: "notes", label: "Notes", detail: "Linked observations" },
  { key: "reports", label: "Reports", detail: "Review archive" },
  { key: "sources", label: "Sources", detail: "Immutable history" },
];

export function ResearchMemoryWorkstation({
  envelope,
  memoryMode,
  collection,
  surface,
  apiBaseUrl,
  originId,
}: {
  envelope: ContractEnvelope;
  memoryMode: MemoryMode;
  collection: string;
  surface: MemorySurface;
  apiBaseUrl: string | null;
  originId: string | null;
}) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const [items, setItems] = useState<Row[]>(rows(data.items));
  const [watchlists, setWatchlists] = useState<Row[]>(rows(data.watchlists));
  const reports = rows(data.reports);
  const sources = rows(data.source_history);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const visibleItems = useMemo(() => {
    const filtered = surface === "notes" ? items.filter((item) => item.memory_type === "note") : items;
    if (!query.trim() || memoryMode === "local") return filtered;
    const needle = query.trim().toLowerCase();
    return filtered.filter((item) => JSON.stringify(item).toLowerCase().includes(needle));
  }, [items, memoryMode, query, surface]);

  const summary = isRecord(data.summary) ? data.summary : envelope.summary;
  const privacy = isRecord(data.privacy) ? data.privacy : {};
  const readiness = isRecord(data.readiness) ? data.readiness : {};

  async function runPrivateSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (memoryMode === "demo") {
      setMessage(query ? `Filtered fictional demo records locally.` : "Showing all fictional demo records.");
      return;
    }
    if (!apiBaseUrl) {
      setMessage("Local API is not configured. Start FastAPI or use demo mode.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/research-memory/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, collection_id: collection, limit: 50, include_private: false }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as { items?: Row[] };
      setItems(Array.isArray(payload.items) ? payload.items : []);
      setMessage(`Private local search returned ${payload.items?.length ?? 0} records. The query was not added to the URL.`);
    } catch {
      setMessage("Local search is unavailable. No query text was logged or added to the URL.");
    } finally {
      setBusy(false);
    }
  }

  async function createNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") || "Local research note");
    const privateBody = String(form.get("body") || "");
    const symbol = String(form.get("symbol") || "").toUpperCase();
    if (memoryMode === "demo") {
      setItems((current) => [{
        memory_id: `session_${Date.now()}`,
        memory_type: "note",
        title,
        sanitized_summary: "Session-only fictional demo note.",
        linked_symbols_json: symbol ? [symbol] : [],
        tags_json: ["session-demo"],
        status: "session-only",
        privacy_scope: "fictional-demo",
        updated_at: new Date().toISOString(),
      }, ...current]);
      setMessage("Demo note added to this browser session only. It was not written to SQLite.");
      event.currentTarget.reset();
      return;
    }
    if (!apiBaseUrl) {
      setMessage("Local API is not configured. The note was not saved.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/research-memory/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          collection_id: collection,
          memory_type: "note",
          title,
          private_body: privateBody,
          sanitized_summary: "Local-private note; body omitted from list and export boundaries.",
          linked_symbols: symbol ? [symbol] : [],
          tags: ["local-note"],
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as { item?: Row };
      if (payload.item) setItems((current) => [withoutPrivateBody(payload.item as Row), ...current]);
      setMessage("Saved to the local-private SQLite workspace. The note body is absent from the URL and list payload.");
      event.currentTarget.reset();
    } catch {
      setMessage("The local note could not be saved. Existing research was not changed.");
    } finally {
      setBusy(false);
    }
  }

  async function addWatchlist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const symbol = String(form.get("watchSymbol") || "").toUpperCase().replace(/[^A-Z0-9.=_-]/g, "").slice(0, 24);
    if (!symbol) return;
    if (memoryMode === "demo") {
      setWatchlists((current) => [{ item_id: `session_watch_${Date.now()}`, symbol, display_name: symbol, item_type: "asset", watch_reason: "Session-only demo watch", source: "fictional-demo", updated_at: new Date().toISOString() }, ...current]);
      setMessage("Demo watch added to this browser session only.");
      event.currentTarget.reset();
      return;
    }
    if (!apiBaseUrl) {
      setMessage("Local API is not configured. The watchlist was not changed.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/research-memory/watchlists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, display_name: symbol, item_type: "asset", watch_reason: "Research Memory monitoring", tags: ["local"] }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as { item?: Row };
      if (payload.item) setWatchlists((current) => [payload.item as Row, ...current]);
      setMessage(`${symbol} added to the local-private watchlist.`);
      event.currentTarget.reset();
    } catch {
      setMessage("The watchlist item could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function removeWatch(itemId: string) {
    if (memoryMode === "demo") {
      setWatchlists((current) => current.filter((item) => String(item.item_id) !== itemId));
      setMessage("Removed from this demo session only.");
      return;
    }
    if (!apiBaseUrl) return;
    const response = await fetch(`${apiBaseUrl}/api/research-memory/watchlists/${encodeURIComponent(itemId)}`, { method: "DELETE" });
    if (response.ok) {
      setWatchlists((current) => current.filter((item) => String(item.item_id) !== itemId));
      setMessage("Archived from the local watchlist.");
    }
  }

  async function previewExport() {
    if (memoryMode === "demo") {
      setMessage(`Sanitized demo export preview: ${items.length} item metadata rows, ${sources.length} source rows; note bodies and symbols excluded.`);
      return;
    }
    if (!apiBaseUrl) {
      setMessage("Local API is not configured. No export was created.");
      return;
    }
    const response = await fetch(`${apiBaseUrl}/api/research-memory/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection_id: collection }),
    });
    if (!response.ok) {
      setMessage("Sanitized export preview is unavailable.");
      return;
    }
    const payload = (await response.json()) as { items?: unknown[]; source_history?: unknown[] };
    setMessage(`Sanitized local export ready: ${payload.items?.length ?? 0} metadata rows and ${payload.source_history?.length ?? 0} source rows. Private text, symbols and paths are excluded.`);
  }

  async function saveOriginSnapshot() {
    if (!originId) return;
    const label = originId.replaceAll("-", " ");
    if (memoryMode === "demo") {
      setItems((current) => [{
        memory_id: `session_snapshot_${Date.now()}`,
        memory_type: "snapshot",
        title: `${label} snapshot`,
        sanitized_summary: "Session-only fictional origin snapshot.",
        origin_view: originId,
        origin_href: originHref(originId),
        compatibility_key: "snapshot:na:origin-workstation-v1",
        tags_json: ["session-demo", "origin-snapshot"],
        status: "session-only",
        privacy_scope: "fictional-demo",
        updated_at: new Date().toISOString(),
      }, ...current]);
      setMessage("Fictional origin snapshot added to this browser session. No local data was written.");
      return;
    }
    if (!apiBaseUrl) {
      setMessage("Local API is not configured. The origin snapshot was not saved.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/research-memory/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          collection_id: collection,
          memory_type: "snapshot",
          title: `${label} snapshot`,
          sanitized_summary: "Local source-bound workstation snapshot metadata.",
          origin_id: originId,
          compatibility_model: "origin-workstation-v1",
          tags: ["origin-snapshot"],
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as { item?: Row };
      if (!payload.item) throw new Error("Missing item");
      await fetch(`${apiBaseUrl}/api/research-memory/source-snapshots`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          memory_id: payload.item.memory_id,
          provider: "origin-workstation",
          freshness: "captured-at-save",
          source_status: "local-snapshot",
          confidence: 0.6,
          caveat: "Snapshot preserves a safe origin link; inspect the originating workstation for current provider rows.",
          data_gap: "Detailed private payload and provider rows are not copied into list or fixture boundaries.",
        }),
      });
      setItems((current) => [withoutPrivateBody(payload.item as Row), ...current]);
      setMessage("Origin snapshot and immutable source-history row saved to local-private SQLite.");
    } catch {
      setMessage("The origin snapshot could not be saved. Existing research was not changed.");
    } finally {
      setBusy(false);
    }
  }

  const compareRows = items.filter((item) => selectedIds.includes(String(item.memory_id)));
  const compatibilityKeys = new Set(compareRows.map((item) => String(item.compatibility_key || "")));
  const compatible = compareRows.length > 1 && compatibilityKeys.size === 1 && !compatibilityKeys.has("");

  return (
    <section className="research-memory-workstation" aria-labelledby="research-memory-title">
      <header className="memory-command-header">
        <div>
          <span className="eyebrow">Local-first research operating system</span>
          <h2 id="research-memory-title">Research Memory</h2>
          <p>Save evidence, revisit source history, and return to the originating workstation without turning private research into telemetry.</p>
        </div>
        <div className="memory-status-grid" aria-label="Research memory status">
          <MemoryMetric label="items" value={summary.item_count} />
          <MemoryMetric label="watching" value={summary.watchlist_count} />
          <MemoryMetric label="sources" value={summary.source_count} />
          <MemoryMetric label="store" value={readiness.store_status || "ready"} tone={readiness.store_status === "ready" ? "ok" : "warn"} />
        </div>
      </header>

      <div className="memory-control-row">
        <nav className="memory-tabs" aria-label="Research memory surfaces">
          {SURFACES.map((entry) => (
            <Link key={entry.key} className={surface === entry.key ? "active" : ""} href={`/?view=research-memory&collection=${encodeURIComponent(collection)}&surface=${entry.key}&mode=${memoryMode}`}>
              <strong>{entry.label}</strong><small>{entry.detail}</small>
            </Link>
          ))}
        </nav>
        <div className="memory-mode-switch" aria-label="Storage mode">
          <Link className={memoryMode === "demo" ? "active" : ""} href="/?view=research-memory&collection=demo-research&surface=inbox&mode=demo">Demo</Link>
          <Link className={memoryMode === "local" ? "active" : ""} href="/?view=research-memory&collection=local-research&surface=inbox&mode=local">Local</Link>
        </div>
      </div>

      <div className="memory-privacy-strip">
        <span className={`memory-dot ${memoryMode === "local" ? "ok" : "fixture"}`} />
        <strong>{memoryMode === "local" ? "Local-private SQLite" : "Fictional deterministic demo"}</strong>
        <span>Search: {String(privacy.search_transport || "POST body only")}</span>
        <span>External AI: disabled</span>
        <span>Cloud sync: unavailable</span>
      </div>

      {message ? <div className="memory-message" role="status">{message}</div> : null}
      {originId ? <div className="memory-origin-prompt"><div><span className="eyebrow">Incoming workstation</span><strong>{originId.replaceAll("-", " ")}</strong><small>Opaque origin ID only; no private payload is present in the URL.</small></div><button type="button" onClick={saveOriginSnapshot} disabled={busy}>Save origin snapshot</button></div> : null}

      <div className="memory-main-grid">
        <div className="memory-primary-column">
          <form className="memory-search" onSubmit={runPrivateSearch}>
            <label htmlFor="memory-search-input">Find saved research</label>
            <input id="memory-search-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search private notes locally" autoComplete="off" />
            <button type="submit" disabled={busy}>Search</button>
          </form>

          {surface === "watchlists" ? (
            <WatchlistSurface rows={watchlists} onRemove={removeWatch} />
          ) : surface === "reports" ? (
            <ReportSurface rows={reports} />
          ) : surface === "sources" ? (
            <SourceSurface rows={sources} />
          ) : (
            <InboxSurface rows={visibleItems} selectedIds={selectedIds} setSelectedIds={setSelectedIds} />
          )}
        </div>

        <aside className="memory-action-rail" aria-label="Research actions">
          <section>
            <span className="eyebrow">Create</span>
            <h3>Linked note</h3>
            <form onSubmit={createNote} className="memory-stack-form">
              <label>Title<input name="title" maxLength={160} required placeholder="Observation title" /></label>
              <label>Symbol<input name="symbol" maxLength={24} placeholder="AAPL" /></label>
              <label>Private note<textarea name="body" maxLength={50000} rows={4} placeholder="Stored locally; never placed in the URL" /></label>
              <button type="submit" disabled={busy}>{memoryMode === "local" ? "Save locally" : "Add demo note"}</button>
            </form>
          </section>
          <section>
            <span className="eyebrow">Watchlist</span>
            <form onSubmit={addWatchlist} className="memory-inline-form">
              <input name="watchSymbol" maxLength={24} placeholder="MSFT" aria-label="Watch symbol" required />
              <button type="submit" disabled={busy}>Add</button>
            </form>
            <div className="compact-watchlist">
              {watchlists.slice(0, 4).map((item) => <span key={String(item.item_id)}>{text(item.symbol || item.display_name)}</span>)}
            </div>
          </section>
          <section>
            <span className="eyebrow">Compare</span>
            <h3>{selectedIds.length}/2 selected</h3>
            <p>{selectedIds.length < 2 ? "Select two inbox records." : compatible ? "Period and model labels match." : "Incompatible period/model labels. No silent comparison."}</p>
            <span className={`memory-badge ${compatible ? "ok" : "warn"}`}>{compatible ? "compatible" : "guarded"}</span>
          </section>
          <section>
            <span className="eyebrow">Export</span>
            <h3>Sanitized metadata</h3>
            <p>Titles, note bodies, symbols, holdings, attachments, account data and local paths are excluded.</p>
            <button type="button" onClick={previewExport}>Preview export</button>
          </section>
        </aside>
      </div>
    </section>
  );
}

function InboxSurface({ rows, selectedIds, setSelectedIds }: { rows: Row[]; selectedIds: string[]; setSelectedIds: (ids: string[]) => void }) {
  return <section className="memory-surface" aria-labelledby="memory-inbox-heading">
    <header><div><span className="eyebrow">Recency queue</span><h3 id="memory-inbox-heading">Research inbox</h3></div><span>{rows.length} records</span></header>
    <div className="memory-item-list">
      {rows.length ? rows.map((item) => {
        const id = String(item.memory_id || "");
        const selected = selectedIds.includes(id);
        const tags = Array.isArray(item.tags_json) ? item.tags_json : [];
        return <article key={id} className={`memory-item ${selected ? "selected" : ""}`}>
          <button type="button" className="memory-select" aria-pressed={selected} onClick={() => setSelectedIds(selected ? selectedIds.filter((value) => value !== id) : [...selectedIds.slice(-1), id])}>{selected ? "Selected" : "Compare"}</button>
          <div className="memory-item-type">{text(item.memory_type)}</div>
          <div className="memory-item-copy"><h4>{text(item.title)}</h4><p>{text(item.sanitized_summary)}</p><div className="memory-tags">{tags.map((tag) => <span key={String(tag)}>{text(tag)}</span>)}</div></div>
          <div className="memory-item-meta"><span>{text(item.compatibility_period || "period n/a")}</span><span>{text(item.compatibility_model || "model n/a")}</span><span>{shortDate(item.updated_at)}</span>{item.origin_href ? <Link href={String(item.origin_href)}>Open origin</Link> : <span>Origin unavailable</span>}</div>
        </article>;
      }) : <EmptyState title="No saved research" detail="Create a linked note or save a source-bound snapshot from a workstation." />}
    </div>
  </section>;
}

function WatchlistSurface({ rows, onRemove }: { rows: Row[]; onRemove: (id: string) => void }) {
  return <section className="memory-surface"><header><div><span className="eyebrow">Active context</span><h3>Watchlists</h3></div><span>{rows.length} tracked</span></header><div className="memory-table-wrap"><table><thead><tr><th>Symbol / topic</th><th>Type</th><th>Reason</th><th>Source</th><th>Updated</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{rows.map((item) => { const symbol = String(item.symbol || "").toUpperCase(); const assetClass = watchAssetClass(item); return <tr key={String(item.item_id)}><td>{symbol && assetClass ? <Link href={canonicalAssetHref(symbol, assetClass, "1d", "cache", "overview", "3mo")}><strong>{symbol}</strong></Link> : <strong>{text(item.display_name)}</strong>}<small>{text(item.display_name)}</small></td><td>{text(item.item_type)}</td><td>{text(item.watch_reason)}</td><td>{text(item.source)}</td><td>{shortDate(item.updated_at)}</td><td><button type="button" className="memory-icon-button" title="Remove from watchlist" aria-label={`Remove ${text(item.symbol || item.display_name)}`} onClick={() => onRemove(String(item.item_id))}>x</button></td></tr>; })}</tbody></table></div></section>;
}

function ReportSurface({ rows }: { rows: Row[] }) {
  return <section className="memory-surface"><header><div><span className="eyebrow">Review archive</span><h3>Reports</h3></div><span>{rows.length} reports</span></header><div className="report-memory-grid">{rows.length ? rows.map((report) => <article key={String(report.report_id || report.memory_id)}><span className="memory-badge">{text(report.report_type || report.memory_type)}</span><h4>{text(report.title)}</h4><p>{text(report.summary || report.sanitized_summary)}</p><footer><span>{text(report.data_confidence || report.status || "unknown")}</span><span>{shortDate(report.generated_at || report.updated_at)}</span></footer></article>) : <EmptyState title="No reports" detail="Generate a source-bound report in local mode or inspect the fictional demo report." />}</div></section>;
}

function SourceSurface({ rows }: { rows: Row[] }) {
  return <section className="memory-surface"><header><div><span className="eyebrow">Append-only ledger</span><h3>Source history</h3></div><span>{rows.length} observations</span></header><div className="memory-table-wrap"><table><thead><tr><th>Provider</th><th>Status</th><th>Fetched</th><th>Confidence</th><th>Caveat / gap</th><th>Source</th></tr></thead><tbody>{rows.map((row) => <tr key={String(row.snapshot_id)}><td><strong>{text(row.provider)}</strong><small>{text(row.memory_id)}</small></td><td><span className={`memory-badge ${statusTone(row.source_status)}`}>{text(row.source_status)}</span><small>{text(row.freshness)}</small></td><td>{shortDate(row.fetched_at)}</td><td>{formatConfidence(row.confidence)}</td><td><span>{text(row.caveat)}</span><small>{text(row.data_gap)}</small></td><td>{safeHttpUrl(row.source_url) ? <a href={String(row.source_url)} target="_blank" rel="noreferrer">Open source</a> : "No URL"}</td></tr>)}</tbody></table></div></section>;
}

function MemoryMetric({ label, value, tone = "neutral" }: { label: string; value: unknown; tone?: "neutral" | "ok" | "warn" }) {
  return <div className={`memory-metric ${tone}`}><span>{label}</span><strong>{text(value)}</strong></div>;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="memory-empty"><strong>{title}</strong><p>{detail}</p></div>;
}

function rows(value: unknown): Row[] { return Array.isArray(value) ? value.filter(isRecord) : []; }
function isRecord(value: unknown): value is Row { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
function text(value: unknown): string { if (value === null || value === undefined || value === "") return "—"; return String(value); }
function shortDate(value: unknown): string { const date = new Date(String(value || "")); return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date); }
function formatConfidence(value: unknown): string { const number = Number(value); return Number.isFinite(number) ? `${Math.round(number * 100)}%` : "—"; }
function statusTone(value: unknown): string { const status = String(value || "").toLowerCase(); return status.includes("live") || status === "fresh" ? "ok" : status.includes("stale") || status.includes("fixture") ? "warn" : "neutral"; }
function safeHttpUrl(value: unknown): boolean { try { const url = new URL(String(value)); return url.protocol === "https:" || url.protocol === "http:"; } catch { return false; } }
function withoutPrivateBody(row: Row): Row { const safe = { ...row }; delete safe.private_body; return safe; }
function originHref(originId: string): string {
  const routes: Record<string, string> = {
    "aapl-equity": "/?view=asset&symbol=AAPL&assetClass=equity&timeframe=1D&surface=overview",
    "btcusdt-crypto": "/?view=asset&symbol=BTCUSDT&assetClass=crypto&timeframe=1D&surface=overview",
    "war-map": "/?view=war-room-map",
    "market-map": "/?view=market-map",
    "aapl-options": "/?view=options-quant&symbol=AAPL&surface=chain",
    "demo-portfolio": "/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY",
  };
  const dynamic = /^asset-(equity|etf|crypto)-([A-Z0-9._-]{1,24})$/.exec(originId);
  if (dynamic) return canonicalAssetHref(dynamic[2], dynamic[1] as ProductAssetClass, "1d", "cache", "overview", "3mo");
  return routes[originId] || "/?view=home";
}

function watchAssetClass(item: Row): ProductAssetClass | null {
  const symbol = String(item.symbol || "").toUpperCase();
  const itemType = String(item.item_type || "").toLowerCase();
  if (!symbol) return null;
  if (itemType === "crypto" || symbol.endsWith("USDT")) return "crypto";
  if (itemType === "etf") return "etf";
  if (["equity", "asset", "stock"].includes(itemType)) return "equity";
  return null;
}
