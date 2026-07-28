"use client";

import {
  ArrowDown,
  ArrowUp,
  BarChart3,
  Bell,
  Building2,
  CalendarDays,
  Check,
  Database,
  GitCompare,
  ListPlus,
  Newspaper,
  Plus,
  RefreshCw,
  Save,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { FinanceChart } from "@/components/FinanceChart";
import { TenantResearchDesk } from "@/components/TenantResearchDesk";
import { ContractEnvelope, RuntimeMode, asRecordArray, isRecord } from "@/lib/contracts";
import { canonicalAnalystWorkspaceHref, canonicalAssetHref } from "@/lib/product-routes";

type Row = Record<string, unknown>;
type DeskMode = "fixture" | "local";
type DeskPanel = "chart" | "financials" | "catalysts" | "news" | "sources";
type WatchlistViewMode = "price" | "performance" | "risk" | "financials" | "technicals" | "catalysts" | "changes";
type WatchlistGroup = "none" | "sector" | "exchange" | "asset_class";

const PANELS: { key: DeskPanel; label: string; icon: typeof BarChart3 }[] = [
  { key: "chart", label: "Chart", icon: BarChart3 },
  { key: "financials", label: "Financials", icon: Building2 },
  { key: "catalysts", label: "Catalysts", icon: CalendarDays },
  { key: "news", label: "News", icon: Newspaper },
  { key: "sources", label: "Sources", icon: Database },
];
const WATCHLIST_MODES: { key: WatchlistViewMode; label: string }[] = [
  { key: "price", label: "Price" },
  { key: "performance", label: "Performance" },
  { key: "risk", label: "Risk" },
  { key: "financials", label: "Financials" },
  { key: "technicals", label: "Technicals" },
  { key: "catalysts", label: "Catalysts" },
  { key: "changes", label: "Changes" },
];

export function WatchlistDesk({
  envelope,
  apiBaseUrl,
  deskMode,
  listId,
  runtimeMode,
  initialSelected,
  originView,
  originState,
  initialViewMode,
  initialSortMode,
  initialGroupMode,
  initialPanel,
  initialChangeType,
  initialChangeSeverity,
  initialChangeStatus,
  initialChangeId,
}: {
  envelope: ContractEnvelope;
  apiBaseUrl: string | null;
  deskMode: DeskMode;
  listId: string;
  runtimeMode: RuntimeMode;
  initialSelected?: string;
  originView?: string;
  originState?: string;
  initialViewMode?: string;
  initialSortMode?: string;
  initialGroupMode?: string;
  initialPanel?: string;
  initialChangeType?: string;
  initialChangeSeverity?: string;
  initialChangeStatus?: string;
  initialChangeId?: string;
}) {
  const [deskEnvelope, setDeskEnvelope] = useState(envelope);
  const initialData = record(envelope.data);
  const initialItems = asRecordArray(initialData.items);
  const firstSymbol = text(initialSelected || record(initialData.selected).symbol || initialItems[0]?.symbol, "");
  const firstAssetClass = assetClass(initialItems.find((row) => text(row.symbol, "") === firstSymbol) ?? {});
  const firstPanel = normalizeDeskPanel(initialPanel);
  const [selectedSymbol, setSelectedSymbol] = useState(firstSymbol);
  const [activePanel, setActivePanel] = useState<DeskPanel>(firstPanel);
  const [summaryEnvelope, setSummaryEnvelope] = useState<ContractEnvelope | null>(null);
  const [panelEnvelope, setPanelEnvelope] = useState<ContractEnvelope | null>(null);
  const [panelCache, setPanelCache] = useState<Record<string, ContractEnvelope>>({});
  const [loading, setLoading] = useState(false);
  const [jobRunning, setJobRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<WatchlistViewMode>(normalizeViewMode(initialViewMode));
  const [sortMode, setSortMode] = useState(normalizeSortMode(initialSortMode));
  const [groupMode, setGroupMode] = useState<WatchlistGroup>(normalizeGroupMode(initialGroupMode));
  const [changeType, setChangeType] = useState(normalizeChangeType(initialChangeType));
  const [changeSeverity, setChangeSeverity] = useState(normalizeChangeSeverity(initialChangeSeverity));
  const [changeStatus, setChangeStatus] = useState(normalizeChangeStatus(initialChangeStatus));
  const [selectedChangeId, setSelectedChangeId] = useState(text(initialChangeId, ""));
  const [alertActionRunning, setAlertActionRunning] = useState(false);

  const data = record(deskEnvelope.data);
  const collections = asRecordArray(data.collections);
  const items = asRecordArray(data.items);
  const activeList = record(data.active_list);
  const materialization = record(data.materialization);
  const latestJob = record(materialization.latest_job);
  const providerBudget = record(latestJob.provider_budget);
  const changeInbox = record(data.change_inbox);
  const changes = asRecordArray(changeInbox.changes);
  const refreshOperations = record(data.refresh_operations);
  const backgroundOperations = record(refreshOperations.background);
  const alertReadiness = record(data.alert_readiness);
  const alertCandidates = asRecordArray(alertReadiness.candidates);
  const filteredChanges = changes.filter((change) => {
    const typeMatch = changeType === "all" || text(change.change_type) === changeType;
    const severityMatch = changeSeverity === "all" || text(change.severity) === changeSeverity;
    const candidate = alertCandidates.find((row) => text(row.change_id) === text(change.change_id));
    const candidateStatus = text(candidate?.acknowledgement_status, "unacknowledged");
    const statusMatch = changeStatus === "all" || candidateStatus === changeStatus;
    return typeMatch && severityMatch && statusMatch;
  });
  const selectedChange = filteredChanges.find((row) => text(row.change_id) === selectedChangeId)
    ?? filteredChanges[0]
    ?? {};
  const changesBySymbol = changes.reduce<Record<string, Row[]>>((result, change) => {
    const symbol = text(change.symbol, "");
    if (symbol) result[symbol] = [...(result[symbol] ?? []), change];
    return result;
  }, {});
  const selectedItem = items.find((row) => text(row.symbol, "") === selectedSymbol) ?? items[0] ?? {};
  const selectedClass = assetClass(selectedItem);
  const selectedPanelWorkstation = workstation(panelEnvelope);
  const selectedSummaryWorkstation = workstation(summaryEnvelope);
  const activeWorkstation = Object.keys(selectedPanelWorkstation).length
    ? selectedPanelWorkstation
    : selectedSummaryWorkstation;
  const chart = record(record(selectedPanelWorkstation.chart_views).price);
  const chartReady = Object.keys(chart).length > 0;
  const panelBytes = panelEnvelope ? JSON.stringify(panelEnvelope).length : 0;
  const displayedItems = (() => {
    const rows: Row[] = items.map((row): Row => {
      const symbolChanges = changesBySymbol[text(row.symbol, "")] ?? [];
      return {
        ...row,
        _change_count: symbolChanges.length,
        _change_severity: symbolChanges.some((change) => text(change.severity) === "critical")
          ? "critical"
          : symbolChanges.some((change) => text(change.severity) === "material")
            ? "material"
            : symbolChanges.length
              ? "info"
              : "none",
      };
    });
    if (sortMode === "symbol") {
      rows.sort((left, right) => text(left.symbol).localeCompare(text(right.symbol)));
    } else if (sortMode === "metric-desc") {
      rows.sort((left, right) => watchlistSortValue(right, viewMode) - watchlistSortValue(left, viewMode));
    } else if (sortMode === "metric-asc") {
      rows.sort((left, right) => watchlistSortValue(left, viewMode) - watchlistSortValue(right, viewMode));
    }
    if (groupMode !== "none") {
      rows.sort((left, right) => {
        const grouped = text(left[groupMode], "Unclassified").localeCompare(text(right[groupMode], "Unclassified"));
        return grouped || Number(left.position ?? 0) - Number(right.position ?? 0);
      });
    }
    return rows;
  })();

  const panelKey = (symbol: string, panel: DeskPanel) => `${symbol}:${panel}:${runtimeMode}`;

  function persistDeskState(overrides: Partial<{
    selected: string;
    watchMode: WatchlistViewMode;
    sort: string;
    group: WatchlistGroup;
    panel: DeskPanel;
    changeType: string;
    changeSeverity: string;
    changeStatus: string;
    change: string;
  }> = {}) {
    const next = new URL(window.location.href);
    next.searchParams.set("list", listId);
    next.searchParams.set("selected", overrides.selected ?? selectedSymbol);
    next.searchParams.set("watchMode", overrides.watchMode ?? viewMode);
    next.searchParams.set("sort", overrides.sort ?? sortMode);
    next.searchParams.set("group", overrides.group ?? groupMode);
    next.searchParams.set("panel", overrides.panel ?? activePanel);
    next.searchParams.set("changeType", overrides.changeType ?? changeType);
    next.searchParams.set("changeSeverity", overrides.changeSeverity ?? changeSeverity);
    next.searchParams.set("changeStatus", overrides.changeStatus ?? changeStatus);
    const nextChange = overrides.change ?? selectedChangeId;
    if (nextChange) next.searchParams.set("change", nextChange);
    else next.searchParams.delete("change");
    next.searchParams.delete("private_reason");
    next.searchParams.delete("watch_reason");
    window.history.replaceState({}, "", next);
  }

  async function fetchEnvelope(path: string): Promise<ContractEnvelope> {
    if (!apiBaseUrl) throw new Error("runtime-api-offline");
    const response = await fetch(`${apiBaseUrl}${path}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`runtime-http-${response.status}`);
    return (await response.json()) as ContractEnvelope;
  }

  async function loadPanel(symbol: string, panel: DeskPanel, force = false) {
    if (!symbol) return;
    const key = panelKey(symbol, panel);
    if (!force && panelCache[key]) {
      setPanelEnvelope(panelCache[key]);
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const asset = items.find((row) => text(row.symbol, "") === symbol);
      const klass = assetClass(asset ?? {});
      const query = new URLSearchParams({
        asset_class: klass,
        interval: "1d",
        range: "3mo",
        runtime_mode: deskMode === "fixture" ? "fixture" : "cache",
        chart_type: "candlestick",
      });
      const loaded = await fetchEnvelope(
        `/api/symbol-workstation/${encodeURIComponent(symbol)}/panels/${panel}?${query.toString()}`,
      );
      setPanelCache((current) => ({ ...current, [key]: loaded }));
      setPanelEnvelope(loaded);
    } catch (error) {
      setPanelEnvelope(null);
      setMessage(panel === "catalysts"
        ? "The provider catalyst panel is unavailable or rate-limited. The saved Research Snapshot remains visible."
        : error instanceof Error && error.message === "runtime-api-offline"
        ? "Runtime API is offline. The local watchlist remains available, but exact panels cannot refresh."
        : "The exact panel is unavailable. No other symbol was substituted.");
    } finally {
      setLoading(false);
    }
  }

  async function selectSymbol(symbol: string) {
    if (!symbol) return;
    setSelectedSymbol(symbol);
    setPanelEnvelope(null);
    setSummaryEnvelope(null);
    setMessage(null);
    persistDeskState({ selected: symbol });
    if (!apiBaseUrl) return;
    const item = items.find((row) => text(row.symbol, "") === symbol);
    const query = new URLSearchParams({
      asset_class: assetClass(item ?? {}),
      interval: "1d",
      range: "3mo",
      runtime_mode: deskMode === "fixture" ? "fixture" : "cache",
    });
    try {
      const summary = await fetchEnvelope(
        `/api/symbol-workstation/${encodeURIComponent(symbol)}/summary?${query.toString()}`,
      );
      setSummaryEnvelope(summary);
    } catch {
      setMessage("The compact exact-symbol summary is unavailable.");
    }
    await loadPanel(symbol, activePanel);
  }

  useEffect(() => {
    if (!firstSymbol || !apiBaseUrl || normalizeViewMode(initialViewMode) === "changes") return;
    const controller = new AbortController();
    const query = new URLSearchParams({
      asset_class: firstAssetClass,
      interval: "1d",
      range: "3mo",
      runtime_mode: deskMode === "fixture" ? "fixture" : "cache",
      chart_type: "candlestick",
    });
    async function loadInitialSelection() {
      try {
        const [summaryResponse, panelResponse] = await Promise.all([
          fetch(`${apiBaseUrl}/api/symbol-workstation/${encodeURIComponent(firstSymbol)}/summary?${query.toString()}`, {
            cache: "no-store",
            headers: { Accept: "application/json" },
            signal: controller.signal,
          }),
          fetch(`${apiBaseUrl}/api/symbol-workstation/${encodeURIComponent(firstSymbol)}/panels/${encodeURIComponent(firstPanel)}?${query.toString()}`, {
            cache: "no-store",
            headers: { Accept: "application/json" },
            signal: controller.signal,
          }),
        ]);
        if (summaryResponse.ok) setSummaryEnvelope(await summaryResponse.json() as ContractEnvelope);
        if (panelResponse.ok) {
          const loaded = await panelResponse.json() as ContractEnvelope;
          setPanelEnvelope(loaded);
          setPanelCache((current) => ({ ...current, [`${firstSymbol}:${firstPanel}:${runtimeMode}`]: loaded }));
        } else if (firstPanel === "catalysts") {
          setMessage("The provider catalyst panel is unavailable or rate-limited. The saved Research Snapshot remains visible.");
        }
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setMessage(firstPanel === "catalysts"
            ? "The provider catalyst panel is offline. The saved Research Snapshot remains visible."
            : "The initial exact-symbol panel is unavailable. The watchlist remains usable.");
        }
      }
    }
    void loadInitialSelection();
    return () => controller.abort();
  }, [apiBaseUrl, deskMode, firstAssetClass, firstPanel, firstSymbol, initialViewMode, runtimeMode]);

  async function reloadDesk(nextListId = listId, nextSelected = selectedSymbol) {
    if (!apiBaseUrl || deskMode !== "local") return;
    const query = new URLSearchParams({
      mode: "local",
      list_id: nextListId,
      selected: nextSelected,
    });
    const loaded = await fetchEnvelope(`/api/watchlist-desk?${query.toString()}`);
    setDeskEnvelope(loaded);
  }

  async function addSymbol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiBaseUrl || deskMode !== "local") {
      setMessage("Switch to Local mode with the runtime API online to edit the watchlist.");
      return;
    }
    const form = event.currentTarget;
    const formData = new FormData(form);
    const symbol = text(formData.get("symbol"), "").toUpperCase();
    const privateReason = text(formData.get("private_reason"), "");
    const response = await fetch(`${apiBaseUrl}/api/watchlist-desk/lists/${encodeURIComponent(listId)}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, asset_class: "equity", private_reason: privateReason }),
    });
    form.reset();
    if (!response.ok) {
      setMessage(response.status === 409 ? `${symbol} is already in this watchlist.` : `${symbol || "Symbol"} could not be added.`);
      return;
    }
    await reloadDesk(listId, symbol);
    await selectSymbol(symbol);
    setMessage(`${symbol} added. Private note retained only in the local workspace.`);
  }

  async function createList(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiBaseUrl || deskMode !== "local") return;
    const form = event.currentTarget;
    const name = text(new FormData(form).get("name"), "");
    const listSlug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48);
    const response = await fetch(`${apiBaseUrl}/api/watchlist-desk/lists`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, list_id: listSlug }),
    });
    form.reset();
    if (!response.ok) {
      setMessage("The watchlist could not be created.");
      return;
    }
    window.location.href = `/?view=watchlist-desk&mode=local&list=${encodeURIComponent(listSlug)}`;
  }

  async function renameList(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiBaseUrl || deskMode !== "local") return;
    const form = event.currentTarget;
    const name = text(new FormData(form).get("name"), "");
    const response = await fetch(`${apiBaseUrl}/api/watchlist-desk/lists/${encodeURIComponent(listId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    form.reset();
    if (response.ok) {
      await reloadDesk();
      setMessage("Watchlist renamed.");
    } else {
      setMessage("The watchlist could not be renamed.");
    }
  }

  async function removeItem(itemId: string) {
    if (!apiBaseUrl || deskMode !== "local") return;
    const response = await fetch(
      `${apiBaseUrl}/api/watchlist-desk/lists/${encodeURIComponent(listId)}/items/${encodeURIComponent(itemId)}`,
      { method: "DELETE" },
    );
    if (response.ok) {
      await reloadDesk(listId, "");
      setMessage("Symbol removed from the local watchlist.");
    }
  }

  async function moveItem(index: number, delta: number) {
    if (!apiBaseUrl || deskMode !== "local") return;
    const target = index + delta;
    if (target < 0 || target >= items.length) return;
    const reordered = items.map((row) => text(row.item_id, ""));
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    const response = await fetch(`${apiBaseUrl}/api/watchlist-desk/lists/${encodeURIComponent(listId)}/order`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_ids: reordered }),
    });
    if (response.ok) await reloadDesk();
  }

  async function materialize() {
    if (!apiBaseUrl || deskMode !== "local") {
      setMessage("Materialization requires Local mode and the runtime API.");
      return;
    }
    setJobRunning(true);
    setMessage("Building a bounded price, fundamentals, earnings, dividend, and exact-news snapshot.");
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/watchlist-desk/lists/${encodeURIComponent(listId)}/materialize`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ interval: "1d", range: "3mo", max_symbols: 5 }),
        },
      );
      if (!response.ok) throw new Error("materialization-failed");
      await reloadDesk();
      setPanelCache({});
      await loadPanel(selectedSymbol, "chart", true);
      setMessage("Bounded Research Snapshot finished. Saved rows now drive every list mode.");
    } catch {
      setMessage("Materialization failed or another job is active. Existing cache remains available.");
    } finally {
      setJobRunning(false);
    }
  }

  async function configureChangeAlerts() {
    if (!apiBaseUrl || deskMode !== "local") {
      setMessage("Preview only: alert readiness is fictional in Fixture mode. No notification was sent.");
      return;
    }
    setAlertActionRunning(true);
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/watchlist-desk/lists/${encodeURIComponent(listId)}/change-alert-rule`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: true,
            minimum_severity: changeSeverity === "all" ? "material" : changeSeverity,
            cooldown_minutes: 60,
          }),
        },
      );
      if (!response.ok) throw new Error("alert-rule-failed");
      await reloadDesk();
      setMessage("Preview-only change alert rule enabled locally. No external delivery channel is configured.");
    } catch {
      setMessage("The local preview rule could not be saved. Existing change evidence remains available.");
    } finally {
      setAlertActionRunning(false);
    }
  }

  async function generateAlertPreviews() {
    if (!apiBaseUrl || deskMode !== "local") {
      setMessage("Preview only: fictional candidates are shown without persistence or delivery.");
      return;
    }
    setAlertActionRunning(true);
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/watchlist-desk/lists/${encodeURIComponent(listId)}/change-alert-previews`,
        { method: "POST", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error("alert-preview-failed");
      await reloadDesk();
      setMessage("Local alert previews generated. They remain inside this workstation and were not delivered.");
    } catch {
      setMessage("Preview generation is unavailable. Saved comparison rows were retained.");
    } finally {
      setAlertActionRunning(false);
    }
  }

  async function acknowledgeAlert(eventId: string) {
    if (!eventId || !apiBaseUrl || deskMode !== "local") {
      setMessage("Acknowledgement requires a persisted local preview event.");
      return;
    }
    setAlertActionRunning(true);
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/watchlist-desk/change-alert-events/${encodeURIComponent(eventId)}/acknowledge`,
        { method: "PATCH", headers: { Accept: "application/json" } },
      );
      if (!response.ok) throw new Error("alert-ack-failed");
      await reloadDesk();
      setMessage("Change preview acknowledged locally.");
    } catch {
      setMessage("The preview acknowledgement could not be saved.");
    } finally {
      setAlertActionRunning(false);
    }
  }

  const workstationMode: RuntimeMode = deskMode === "fixture" ? "cache" : runtimeMode;
  const analystMode: RuntimeMode = deskMode === "fixture" ? "fixture" : runtimeMode;
  const selectedChangePanel = panelForChange(selectedChange);
  const selectedChangeSymbol = text(selectedChange.symbol, selectedSymbol);
  const selectedChangeItem = items.find((row) => text(row.symbol) === selectedChangeSymbol) ?? selectedItem;
  const selectedChangeHref = selectedChangeSymbol
    ? canonicalAnalystWorkspaceHref(
        selectedChangeSymbol,
        assetClass(selectedChangeItem),
        analystMode,
        {
          interval: "1d",
          range: "3mo",
          panel: selectedChangePanel,
          layout: selectedChangePanel === "chart" ? "chart-focus" : "research",
          list: listId,
          changeType,
          changeSeverity,
          changeStatus,
          change: text(selectedChange.change_id, ""),
        },
      )
    : "/?view=watchlist-desk&watchMode=changes";
  const selectedHref = selectedSymbol
    ? canonicalAssetHref(selectedSymbol, selectedClass, "1d", workstationMode, activePanel === "chart" ? "overview" : activePanel, "3mo", {
        originView: "watchlist-desk",
        originState: new URLSearchParams({
          mode: deskMode,
          list: listId,
          selected: selectedSymbol,
          watchMode: viewMode,
          sort: sortMode,
          group: groupMode,
          panel: activePanel,
          changeType,
          changeSeverity,
          changeStatus,
          change: text(selectedChange.change_id, ""),
        }).toString(),
      })
    : "/?view=market-map";

  return (
    <section
      className="watchlist-desk"
      aria-labelledby="watchlist-desk-title"
      data-phase6d-watchlist-desk="true"
      data-watchlist-count={String(collections.length)}
      data-watchlist-item-count={String(items.length)}
      data-selected-symbol={selectedSymbol}
      data-panel-delivery={activePanel}
      data-panel-bytes={String(panelBytes)}
      data-private-note-visible="false"
      data-materialization-status={text(latestJob.status, "not-run")}
      data-watchlist-view-mode={viewMode}
      data-watchlist-sort={sortMode}
      data-watchlist-group={groupMode}
      data-watchlist-change-count={String(changes.length)}
      data-watchlist-selected-change={text(selectedChange.change_id, "none")}
      data-watchlist-change-type={changeType}
      data-watchlist-change-severity={changeSeverity}
      data-watchlist-change-status={changeStatus}
      data-provider-fanout="false"
    >
      <header className="watchlist-desk-header">
        <div>
          <span className="eyebrow">Local-private daily monitor</span>
          <h2 id="watchlist-desk-title">Watchlist Desk</h2>
          <p>One bounded refresh prepares research snapshots and a source-preserving daily change inbox.</p>
        </div>
        <div className="watchlist-desk-status">
          <span className={`source-chip ${statusTone(text(record(envelope.summary).source_status))}`}>{deskMode}</span>
          <strong>{text(activeList.name, "Daily Radar")}</strong>
          <small>{items.length} symbols / {text(latestJob.status, "not materialized")}</small>
        </div>
      </header>

      <TenantResearchDesk sourceListId={listId} />

      <div className="watchlist-desk-toolbar">
        <nav aria-label="Watchlist selection">
          {collections.map((row) => (
            <Link
              key={text(row.list_id)}
              className={text(row.list_id) === listId ? "active" : ""}
              href={`/?view=watchlist-desk&mode=${deskMode}&list=${encodeURIComponent(text(row.list_id))}`}
            >
              {text(row.name)} <span>{text(row.item_count, "0")}</span>
            </Link>
          ))}
        </nav>
        <button type="button" onClick={materialize} disabled={jobRunning || !items.length} title="Refresh bounded watchlist cache">
          <RefreshCw size={15} className={jobRunning ? "spin" : ""} aria-hidden="true" />
          {jobRunning ? "Refreshing" : "Refresh list"}
        </button>
        <Link className="watchlist-alert-manager-link" href="/?view=alert-manager&mode=cache&tab=rules" title="Open tenant-safe Watchlist Alert Manager">
          <Bell size={14} aria-hidden="true" /> Alert Manager
        </Link>
        {originView && originState ? <Link href={`/?view=${encodeURIComponent(originView)}&${originState}`}>Return to origin</Link> : null}
      </div>

      <div className="watchlist-advanced-toolbar" aria-label="Advanced watchlist controls">
        <div className="watchlist-view-modes" role="group" aria-label="Watchlist metric mode">
          {WATCHLIST_MODES.map(({ key, label }) => (
            <button
              type="button"
              key={key}
              className={viewMode === key ? "active" : ""}
              onClick={() => {
                setViewMode(key);
                if (key === "changes" && !selectedChangeId && changes[0]) {
                  setSelectedChangeId(text(changes[0].change_id, ""));
                }
                persistDeskState({ watchMode: key });
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <label>
          <span>Sort</span>
          <select value={sortMode} onChange={(event) => {
            const value = normalizeSortMode(event.target.value);
            setSortMode(value);
            persistDeskState({ sort: value });
          }}>
            <option value="manual">List order</option>
            <option value="symbol">Symbol A-Z</option>
            <option value="metric-desc">Primary metric high-low</option>
            <option value="metric-asc">Primary metric low-high</option>
          </select>
        </label>
        <label>
          <span>Group</span>
          <select value={groupMode} onChange={(event) => {
            const value = normalizeGroupMode(event.target.value);
            setGroupMode(value);
            persistDeskState({ group: value });
          }}>
            <option value="none">No group</option>
            <option value="sector">Sector</option>
            <option value="exchange">Exchange</option>
            <option value="asset_class">Asset class</option>
          </select>
        </label>
        <span className="watchlist-cache-only">Saved snapshot / 0 request-time provider calls</span>
      </div>

      <div className="watchlist-desk-layout">
        <aside className="watchlist-symbol-rail" aria-label="Tracked symbols">
          <div className="watchlist-rail-heading">
            <span>Symbol</span><span>{watchlistColumnLabel(viewMode, 0)}</span><span>{watchlistColumnLabel(viewMode, 1)}</span>
          </div>
          <div className="watchlist-symbol-rows">
            {displayedItems.map((row, displayedIndex) => {
              const symbol = text(row.symbol, "");
              const active = symbol === selectedSymbol;
              const index = items.findIndex((item) => text(item.item_id) === text(row.item_id));
              const previous = displayedItems[displayedIndex - 1];
              const group = groupMode === "none" ? "" : text(row[groupMode], "Unclassified");
              const previousGroup = groupMode === "none" || !previous ? "" : text(previous[groupMode], "Unclassified");
              const display = watchlistDisplay(row, viewMode);
              return (
                <div key={text(row.item_id)}>
                  {group && group !== previousGroup ? <div className="watchlist-group-heading">{group}<span>{groupMode.replace("_", " ")}</span></div> : null}
                  <div className={active ? "watchlist-symbol-row active" : "watchlist-symbol-row"} data-watchlist-symbol={symbol}>
                    <button type="button" className="watchlist-symbol-select" onClick={() => void selectSymbol(symbol)} aria-pressed={active}>
                      <span><strong>{symbol}</strong><small>{text(row.exchange)} / {text(row.sector, "Unclassified")}</small></span>
                      <span><strong className={display.primaryTone}>{display.primary}</strong><small>{display.primaryDetail}</small></span>
                      <span><b className={display.secondaryTone}>{display.secondary}</b><small>{display.secondaryDetail}</small></span>
                    </button>
                    {deskMode === "local" ? (
                      <span className="watchlist-row-actions">
                        <button type="button" onClick={() => void moveItem(index, -1)} disabled={sortMode !== "manual" || groupMode !== "none" || index === 0} title="Move up" aria-label={`Move ${symbol} up`}><ArrowUp size={13} /></button>
                        <button type="button" onClick={() => void moveItem(index, 1)} disabled={sortMode !== "manual" || groupMode !== "none" || index === items.length - 1} title="Move down" aria-label={`Move ${symbol} down`}><ArrowDown size={13} /></button>
                        <button type="button" onClick={() => void removeItem(text(row.item_id))} title="Remove symbol" aria-label={`Remove ${symbol}`}><Trash2 size={13} /></button>
                      </span>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
          {!items.length ? <div className="watchlist-empty"><strong>No tracked symbols</strong><span>Add an exact equity identity below.</span></div> : null}
          <form className="watchlist-add-form" onSubmit={addSymbol}>
            <label><span>Symbol</span><input name="symbol" maxLength={24} placeholder="TSLA" autoComplete="off" required /></label>
            <label><span>Private note</span><input name="private_reason" type="password" maxLength={1000} placeholder="Stored locally only" autoComplete="off" /></label>
            <button type="submit" title="Add exact symbol"><Plus size={15} /> Add</button>
          </form>
        </aside>

        <main className={viewMode === "changes" ? "watchlist-analysis-main change-inbox-main" : "watchlist-analysis-main"}>
          {viewMode === "changes" ? (
            <ChangeInbox
              inbox={changeInbox}
              changes={filteredChanges}
              selected={selectedChange}
              selectedHref={selectedChangeHref}
              changeType={changeType}
              changeSeverity={changeSeverity}
              changeStatus={changeStatus}
              candidates={alertCandidates}
              alertReadiness={alertReadiness}
              busy={alertActionRunning}
              onType={(value) => {
                setChangeType(value);
                setSelectedChangeId("");
                persistDeskState({ changeType: value, change: "" });
              }}
              onSeverity={(value) => {
                setChangeSeverity(value);
                setSelectedChangeId("");
                persistDeskState({ changeSeverity: value, change: "" });
              }}
              onStatus={(value) => {
                setChangeStatus(value);
                setSelectedChangeId("");
                persistDeskState({ changeStatus: value, change: "" });
              }}
              onSelect={(row) => {
                const id = text(row.change_id, "");
                setSelectedChangeId(id);
                setSelectedSymbol(text(row.symbol, selectedSymbol));
                persistDeskState({ selected: text(row.symbol, selectedSymbol), change: id });
              }}
              onConfigure={() => void configureChangeAlerts()}
              onPreview={() => void generateAlertPreviews()}
              onAcknowledge={(eventId) => void acknowledgeAlert(eventId)}
            />
          ) : (
            <>
          <header className="watchlist-symbol-header">
            <div>
              <span className="eyebrow">Exact identity / progressive delivery</span>
              <h3><code>{selectedSymbol || "No symbol"}</code> {text(record(activeWorkstation.identity).name, text(selectedItem.name, ""))}</h3>
              <p>{text(selectedItem.exchange)} / {text(selectedItem.sector, "Unclassified")} / {text(selectedItem.identity_origin, "identity unavailable")}</p>
            </div>
            <div>
              <strong>{formatPrice(record(activeWorkstation.quote).last_price ?? selectedItem.last_price)}</strong>
              <span className={returnTone(record(activeWorkstation.quote).change_pct ?? selectedItem.change_pct)}>{formatPercent(record(activeWorkstation.quote).change_pct ?? selectedItem.change_pct)}</span>
              <small>{text(record(activeWorkstation.market_clock).market_data_status, text(selectedItem.source_status))}</small>
            </div>
          </header>

          <nav className="watchlist-panel-tabs" aria-label="Selected symbol panels">
            {PANELS.map(({ key, label, icon: Icon }) => (
              <button
                type="button"
                key={key}
                className={activePanel === key ? "active" : ""}
                onClick={() => {
                  setActivePanel(key);
                  persistDeskState({ panel: key });
                  void loadPanel(selectedSymbol, key);
                }}
              >
                <Icon size={15} aria-hidden="true" /> {label}
              </button>
            ))}
            <Link href={selectedHref}>Full workstation</Link>
          </nav>

          {loading ? <div className="watchlist-panel-loading"><RefreshCw size={18} className="spin" /> Loading exact {activePanel} panel</div> : null}
          {!loading && activePanel === "chart" ? (
            <section className="watchlist-chart-panel" data-watchlist-chart-state={chartReady ? "ready" : "unavailable"}>
              <header><span>1D / 3M</span><strong>{text(record(activeWorkstation.summary).history_row_count, "0")} OHLCV rows</strong><small>{text(record(activeWorkstation.market_clock).market_data_as_of)}</small></header>
              {chartReady ? <FinanceChart key={`${selectedSymbol}-${panelBytes}`} chart={chart} /> : <PanelUnavailable title="Chart cache unavailable" detail="Run the bounded list refresh or open the full workstation in live-if-available mode." />}
            </section>
          ) : null}
          {!loading && activePanel === "financials" ? <FinancialPanel workstation={selectedPanelWorkstation} /> : null}
          {!loading && activePanel === "catalysts" ? <CatalystPanel workstation={selectedPanelWorkstation} fallback={record(selectedItem.catalysts)} /> : null}
          {!loading && activePanel === "news" ? <NewsPanel workstation={selectedPanelWorkstation} /> : null}
          {!loading && activePanel === "sources" ? <SourcesPanel envelope={panelEnvelope} /> : null}
            </>
          )}
          {message ? <div className="watchlist-message" role="status">{message}</div> : null}
        </main>

        <aside className="watchlist-ops-rail">
          <section>
            <span className="eyebrow">Materialization health</span>
            <dl>
              <Metric label="Status" value={text(latestJob.status, "not-run")} />
              <Metric label="Queue" value={text(latestJob.queue_depth, "0")} />
              <Metric label="Completed" value={text(latestJob.completed_count, "0")} />
              <Metric label="Failed" value={text(latestJob.failed_count, "0")} />
              <Metric label="Provider calls" value={`${text(latestJob.provider_call_count, "0")} / ${text(latestJob.provider_call_budget, "0")}`} />
              <Metric label="Cache hits" value={text(providerBudget.cache_hits, "0")} />
              <Metric label="Stale LKG" value={text(providerBudget.stale_hits, "0")} />
              <Metric label="Failed calls" value={text(providerBudget.failed_calls, "0")} />
              <Metric label="Duration" value={`${text(latestJob.duration_ms, "0")} ms`} />
              <Metric label="Next safe refresh" value={shortTime(providerBudget.next_safe_refresh_at)} />
            </dl>
            <p>Manual and bounded. No installed background service or broad-universe rebuild is claimed.</p>
          </section>
          <section>
            <span className="eyebrow">Refresh operations</span>
            <dl>
              <Metric label="Readiness" value={text(refreshOperations.readiness, "not-run")} />
              <Metric label="Last attempt" value={text(record(refreshOperations.last_attempt).status, "none")} />
              <Metric label="Last success" value={shortTime(record(refreshOperations.last_success).completed_at)} />
              <Metric label="Overlap" value={text(refreshOperations.overlap_status, "idle")} />
              <Metric label="Background" value={text(backgroundOperations.status, "disabled-by-default")} />
              <Metric label="Kill switch" value={text(backgroundOperations.kill_switch_engaged, "true")} />
            </dl>
            <p>{text(refreshOperations.caveat, "Refresh remains manual, bounded, and observable.")}</p>
          </section>
          <section>
            <span className="eyebrow">Change alert readiness</span>
            <dl>
              <Metric label="Delivery" value={text(alertReadiness.delivery, "preview-only")} />
              <Metric label="Status" value={text(alertReadiness.status, "not-configured")} />
              <Metric label="Eligible" value={text(alertReadiness.eligible_count, "0")} />
              <Metric label="Acknowledged" value={text(alertReadiness.acknowledged_count, "0")} />
            </dl>
            <p>Preview only. No email, push, webhook, SMS, trade, or hosted delivery is claimed.</p>
          </section>
          <section>
            <span className="eyebrow">Delivery boundary</span>
            <dl>
              <Metric label="Panel" value={activePanel} />
              <Metric label="Payload" value={panelBytes ? `${Math.round(panelBytes / 1024)} KB` : "not loaded"} />
              <Metric label="Identity" value={text(selectedItem.identity_status)} />
              <Metric label="Freshness" value={text(selectedItem.freshness)} />
            </dl>
            <p>Summary, chart, financials, news, and sources remain exact-symbol contracts with shared cache partitions.</p>
          </section>
          {deskMode === "local" ? (
            <section className="watchlist-admin">
              <span className="eyebrow">Local organization</span>
              <form onSubmit={createList}>
                <input name="name" maxLength={80} placeholder="New watchlist" required />
                <button type="submit" title="Create watchlist"><ListPlus size={14} /> Create</button>
              </form>
              <form onSubmit={renameList}>
                <input name="name" maxLength={80} placeholder="Rename active list" required />
                <button type="submit" title="Rename active watchlist"><Save size={14} /> Rename</button>
              </form>
            </section>
          ) : null}
        </aside>
      </div>
      <footer className="watchlist-desk-footer">
        <span>Read-only research</span>
        <p>Delayed/public data and local cache only. Private notes are excluded from URLs, payloads, fixtures, logs, AI context, and release archives.</p>
      </footer>
    </section>
  );
}

function ChangeInbox({
  inbox,
  changes,
  selected,
  selectedHref,
  changeType,
  changeSeverity,
  changeStatus,
  candidates,
  alertReadiness,
  busy,
  onType,
  onSeverity,
  onStatus,
  onSelect,
  onConfigure,
  onPreview,
  onAcknowledge,
}: {
  inbox: Row;
  changes: Row[];
  selected: Row;
  selectedHref: string;
  changeType: string;
  changeSeverity: string;
  changeStatus: string;
  candidates: Row[];
  alertReadiness: Row;
  busy: boolean;
  onType: (value: string) => void;
  onSeverity: (value: string) => void;
  onStatus: (value: string) => void;
  onSelect: (row: Row) => void;
  onConfigure: () => void;
  onPreview: () => void;
  onAcknowledge: (eventId: string) => void;
}) {
  const summary = record(inbox.summary);
  const evidence = record(selected.evidence);
  const beforeEvidence = record(evidence.before);
  const afterEvidence = record(evidence.after);
  const selectedCandidate = candidates.find((row) => text(row.change_id) === text(selected.change_id)) ?? {};
  const comparisonReady = text(inbox.comparison_status) === "ready";

  return (
    <section className="change-inbox" aria-labelledby="change-inbox-title">
      <header className="change-inbox-header">
        <div>
          <span className="eyebrow">Saved observation comparison / zero provider calls</span>
          <h3 id="change-inbox-title"><GitCompare size={19} aria-hidden="true" /> Watchlist Change Inbox</h3>
          <p>{shortTime(inbox.previous_snapshot_at)} to {shortTime(inbox.current_snapshot_at)}</p>
        </div>
        <div className="change-inbox-scoreboard">
          <span><strong>{text(summary.change_count, "0")}</strong> changes</span>
          <span><strong>{text(summary.symbol_count, "0")}</strong> symbols</span>
          <span className={comparisonReady ? "ok" : "warn"}>{text(inbox.comparison_status, "not-ready")}</span>
        </div>
      </header>

      <div className="change-inbox-controls" aria-label="Change inbox filters">
        <label>
          <span>Type</span>
          <select value={changeType} onChange={(event) => onType(normalizeChangeType(event.target.value))}>
            <option value="all">All changes</option>
            <option value="price">Price</option>
            <option value="performance">Performance</option>
            <option value="fundamental">Fundamental</option>
            <option value="event">Event</option>
            <option value="news">Exact news</option>
            <option value="source-status">Source status</option>
          </select>
        </label>
        <label>
          <span>Severity</span>
          <select value={changeSeverity} onChange={(event) => onSeverity(normalizeChangeSeverity(event.target.value))}>
            <option value="all">All severity</option>
            <option value="critical">Critical</option>
            <option value="material">Material</option>
            <option value="info">Information</option>
          </select>
        </label>
        <label>
          <span>Status</span>
          <select value={changeStatus} onChange={(event) => onStatus(normalizeChangeStatus(event.target.value))}>
            <option value="all">All status</option>
            <option value="unacknowledged">Unacknowledged</option>
            <option value="acknowledged">Acknowledged</option>
          </select>
        </label>
        <div className="change-alert-actions">
          <button type="button" onClick={onConfigure} disabled={busy} title="Enable local preview rule">
            <Bell size={14} aria-hidden="true" /> Preview rule
          </button>
          <button type="button" onClick={onPreview} disabled={busy} title="Generate local alert previews">
            <RefreshCw size={14} className={busy ? "spin" : ""} aria-hidden="true" /> Generate previews
          </button>
          <small>Preview only / {text(alertReadiness.hosted_delivery, "unavailable")}</small>
        </div>
      </div>

      {!comparisonReady ? (
        <PanelUnavailable
          title="Two successful snapshots required"
          detail={text(inbox.data_gap, "Run two bounded refreshes before comparing saved observations.")}
        />
      ) : (
        <div className="change-inbox-grid">
          <div className="change-inbox-list" role="list" aria-label="Filtered saved changes">
            {changes.map((change) => {
              const active = text(change.change_id) === text(selected.change_id);
              const candidate = candidates.find((row) => text(row.change_id) === text(change.change_id));
              return (
                <button
                  type="button"
                  key={text(change.change_id)}
                  className={active ? "change-inbox-row active" : "change-inbox-row"}
                  onClick={() => onSelect(change)}
                  aria-current={active ? "true" : undefined}
                >
                  <span className={`change-severity ${text(change.severity, "info")}`}>{text(change.severity, "info")}</span>
                  <span><strong>{text(change.symbol)}</strong><small>{text(change.change_type)} / {text(change.transition)}</small></span>
                  <p>{text(change.observation)}</p>
                  <span className={text(candidate?.acknowledgement_status) === "acknowledged" ? "ok" : "warn"}>
                    {text(candidate?.acknowledgement_status, "unacknowledged")}
                  </span>
                </button>
              );
            })}
            {!changes.length ? (
              <div className="change-inbox-empty">
                <Check size={22} aria-hidden="true" />
                <strong>No changes match these filters</strong>
                <span>The saved comparison remains ready; adjust the filters to inspect other observations.</span>
              </div>
            ) : null}
          </div>

          {Object.keys(selected).length ? (
            <article className="change-evidence-panel">
              <header>
                <div><span>{text(selected.change_type)}</span><h4>{text(selected.symbol)} / {text(selected.field)}</h4></div>
                <span className={`change-severity ${text(selected.severity, "info")}`}>{text(selected.severity)}</span>
              </header>
              <p className="change-observation">{text(selected.observation)}</p>
              <div className="change-before-after">
                <section>
                  <span>Previous</span>
                  <strong>{displayChangeValue(selected.before, selected.unit)}</strong>
                  <small>{text(beforeEvidence.source_status, "unavailable")} / {shortTime(beforeEvidence.fetched_at)}</small>
                </section>
                <section>
                  <span>Current</span>
                  <strong>{displayChangeValue(selected.after, selected.unit)}</strong>
                  <small>{text(afterEvidence.source_status, "unavailable")} / {shortTime(afterEvidence.fetched_at)}</small>
                </section>
              </div>
              <div className="change-evidence-ledger">
                <span>Evidence</span>
                {[beforeEvidence, afterEvidence].map((source, index) => (
                  <div key={`${text(source.provider)}-${index}`}>
                    <strong>{index === 0 ? "Previous" : "Current"} / {text(source.provider, "provider unavailable")}</strong>
                    <small>{text(source.source_status)} / {shortTime(source.fetched_at)}</small>
                    {safeHttp(source.source_url) ? <a href={text(source.source_url)} target="_blank" rel="noreferrer">Open source</a> : <span>No source URL</span>}
                    <p>{text(source.data_gap || source.caveat, "No additional caveat")}</p>
                  </div>
                ))}
              </div>
              <footer>
                <Link href={selectedHref}>Open exact {panelForChange(selected)} analysis</Link>
                {text(selectedCandidate.event_id, "") ? (
                  <button
                    type="button"
                    disabled={busy || text(selectedCandidate.acknowledgement_status) === "acknowledged"}
                    onClick={() => onAcknowledge(text(selectedCandidate.event_id, ""))}
                  >
                    <Check size={14} aria-hidden="true" /> Acknowledge
                  </button>
                ) : <span>Generate a preview to enable acknowledgement</span>}
              </footer>
              <p className="change-caveat">{text(inbox.caveat)}</p>
            </article>
          ) : null}
        </div>
      )}
    </section>
  );
}

function FinancialPanel({ workstation: current }: { workstation: Row }) {
  const financial = record(current.financial_context);
  const metrics = record(financial.metrics);
  const sec = record(financial.sec_facts);
  if (!Object.keys(current).length || text(financial.availability) === "not-loaded") {
    return <PanelUnavailable title="Financial panel unavailable" detail="Load the exact financial panel with the runtime API online." />;
  }
  return (
    <section className="watchlist-detail-panel" data-watchlist-financial-state={text(financial.availability)}>
      <header><span className="eyebrow">On-demand fundamentals</span><h4>{text(record(current.identity).symbol)} financial context</h4><b>{text(financial.source_status)}</b></header>
      <dl className="watchlist-metric-grid">
        <Metric label="Market cap" value={compact(metrics.market_cap)} />
        <Metric label="Trailing P/E" value={formatNumber(metrics.trailing_pe)} />
        <Metric label="Forward P/E" value={formatNumber(metrics.forward_pe)} />
        <Metric label="Price / book" value={formatNumber(metrics.price_to_book)} />
        <Metric label="SEC facts" value={text(sec.fact_count, String(asRecordArray(sec.facts).length))} />
        <Metric label="Coverage" value={text(financial.availability)} />
      </dl>
      <p>{text(financial.caveat)}</p>
    </section>
  );
}

function CatalystPanel({ workstation: current, fallback }: { workstation: Row; fallback: Row }) {
  const delivered = record(current.catalyst_context);
  const deliveredCount = asRecordArray(delivered.earnings).length + asRecordArray(delivered.dividends).length + asRecordArray(delivered.news).length;
  const catalysts = deliveredCount > 0 ? delivered : fallback;
  const earnings = asRecordArray(catalysts.earnings);
  const dividends = asRecordArray(catalysts.dividends);
  const news = asRecordArray(catalysts.news);
  const next = record(catalysts.next_event);
  const symbol = text(catalysts.symbol || record(current.identity).symbol, "");
  if (!Object.keys(catalysts).length) {
    return <PanelUnavailable title="Catalysts unavailable" detail="Run the bounded Research Snapshot for this exact symbol." />;
  }
  return (
    <section className="watchlist-detail-panel watchlist-catalyst-panel" data-watchlist-catalyst-count={String(earnings.length + dividends.length + news.length)}>
      <header>
        <span className="eyebrow">Saved exact-symbol catalyst monitor</span>
        <h4>{symbol} catalysts</h4>
        <b className={statusTone(text(catalysts.source_status))}>{text(catalysts.source_status)}</b>
      </header>
      <div className="watchlist-next-catalyst">
        <CalendarDays size={18} aria-hidden="true" />
        <div><span>Next event</span><strong>{catalystLabel(next)}</strong></div>
        <time>{catalystDate(next)}</time>
      </div>
      <div className="watchlist-catalyst-columns">
        <section>
          <h5>Earnings / dividends</h5>
          <div className="watchlist-catalyst-coverage">
            <span>Earnings {earnings.length || "unavailable"}</span>
            <span>Dividends {dividends.length || "unavailable"}</span>
          </div>
          {[...earnings, ...dividends].length ? [...earnings, ...dividends].slice(0, 5).map((row, index) => (
            <article key={`${text(row.event_type)}-${catalystDate(row)}-${index}`}>
              <div><strong>{catalystLabel(row)}</strong><time>{catalystDate(row)}</time></div>
              <small>{text(row.provider)} / {text(row.source_status)}</small>
              <p>{row.estimated_eps !== undefined ? `EPS est. ${formatNumber(row.estimated_eps)} / actual ${formatNumber(row.reported_eps)}` : `Amount ${formatNumber(row.amount)} / yield ${formatPercent(Number(row.yield) * 100)}`}</p>
            </article>
          )) : <PanelUnavailable title="No calendar event" detail="Missing events remain unavailable, not zero." />}
        </section>
        <section>
          <h5>Exact news</h5>
          <div className="watchlist-catalyst-coverage"><span>Strict matches {news.length || "unavailable"}</span></div>
          {news.length ? news.slice(0, 5).map((row, index) => (
            <article key={`${text(row.title)}-${index}`}>
              <div><strong>{safeHttp(row.source_url) ? <a href={text(row.source_url)} target="_blank" rel="noreferrer">{text(row.title)}</a> : text(row.title)}</strong><time>{shortTime(row.published_at)}</time></div>
              <small>{text(row.provider)} / exact {text(record(row.match_evidence).exact, "false")}</small>
              <p>{text(row.summary, "Open the linked publisher to verify this catalyst.")}</p>
            </article>
          )) : <PanelUnavailable title="No exact headline" detail="Broad market headlines are never substituted." />}
        </section>
      </div>
      <footer><span>Snapshot clock {shortTime(catalysts.fetched_at)}</span><p>{text(catalysts.data_gap || catalysts.caveat)}</p></footer>
    </section>
  );
}

function NewsPanel({ workstation: current }: { workstation: Row }) {
  const exact = record(current.exact_news);
  const rows = asRecordArray(exact.rows);
  if (!Object.keys(current).length) return <PanelUnavailable title="News panel unavailable" detail="No exact-symbol news panel was loaded." />;
  return (
    <section className="watchlist-detail-panel" data-watchlist-news-count={String(rows.length)}>
      <header><span className="eyebrow">Exact-symbol news</span><h4>{text(record(current.identity).symbol)} headlines</h4><b>{text(exact.source_status)}</b></header>
      <div className="watchlist-news-list">
        {rows.length ? rows.slice(0, 8).map((row, index) => (
          <article key={`${text(row.title)}-${index}`}>
            <div><span>{text(row.provider)}</span><small>{shortTime(row.published_at)}</small></div>
            <strong>{safeHttp(row.source_url) ? <a href={text(row.source_url)} target="_blank" rel="noreferrer">{text(row.title)}</a> : text(row.title)}</strong>
          </article>
        )) : <PanelUnavailable title="No exact headline match" detail={text(exact.data_gap, "Broad headlines are not relabeled as company news.")} />}
      </div>
    </section>
  );
}

function SourcesPanel({ envelope }: { envelope: ContractEnvelope | null }) {
  const rows = envelope ? asRecordArray(envelope.source_status) : [];
  return (
    <section className="watchlist-detail-panel" data-watchlist-source-count={String(rows.length)}>
      <header><span className="eyebrow">Exact provenance</span><h4>Source and freshness ledger</h4><b>{rows.length}</b></header>
      <div className="watchlist-source-list">
        {rows.map((row, index) => (
          <div key={`${text(row.provider)}-${index}`}>
            <strong>{text(row.provider)}</strong>
            <span className={statusTone(text(row.source_status))}>{text(row.source_status)}</span>
            <small>{shortTime(row.fetched_at)} / {text(row.row_count, "0")} rows</small>
            <p>{text(row.data_gap || row.caveat, "No declared gap")}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function PanelUnavailable({ title, detail }: { title: string; detail: string }) {
  return <div className="watchlist-panel-unavailable"><strong>{title}</strong><span>{detail}</span></div>;
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
function assetClass(row: Row): "equity" | "etf" | "crypto" {
  const current = text(row.asset_class, "equity");
  return current === "crypto" || current === "etf" ? current : "equity";
}
function formatPrice(value: unknown): string {
  const current = numeric(value);
  return current === null ? "Unavailable" : new Intl.NumberFormat("en-US", { maximumFractionDigits: current < 10 ? 4 : 2 }).format(current);
}
function formatPercent(value: unknown): string {
  const current = numeric(value);
  return current === null ? "-" : `${current > 0 ? "+" : ""}${current.toFixed(2)}%`;
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
  return ["fresh", "live/fresh", "cached", "available", "exact", "completed"].includes(value)
    ? "ok"
    : ["fixture", "stale", "not-materialized", "partial", "not-run"].includes(value)
      ? "warn"
      : "danger";
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

function normalizeViewMode(value: unknown): WatchlistViewMode {
  return ["price", "performance", "risk", "financials", "technicals", "catalysts", "changes"].includes(String(value))
    ? String(value) as WatchlistViewMode
    : "price";
}
function normalizeChangeType(value: unknown): string {
  return ["all", "price", "performance", "fundamental", "event", "news", "source-status"].includes(String(value))
    ? String(value)
    : "all";
}
function normalizeChangeSeverity(value: unknown): string {
  return ["all", "critical", "material", "info"].includes(String(value)) ? String(value) : "all";
}
function normalizeChangeStatus(value: unknown): string {
  return ["all", "unacknowledged", "acknowledged"].includes(String(value)) ? String(value) : "all";
}
function normalizeSortMode(value: unknown): string {
  return ["manual", "symbol", "metric-desc", "metric-asc"].includes(String(value)) ? String(value) : "manual";
}
function normalizeGroupMode(value: unknown): WatchlistGroup {
  return ["none", "sector", "exchange", "asset_class"].includes(String(value))
    ? String(value) as WatchlistGroup
    : "none";
}
function normalizeDeskPanel(value: unknown): DeskPanel {
  return ["chart", "financials", "catalysts", "news", "sources"].includes(String(value))
    ? String(value) as DeskPanel
    : "chart";
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
function panelForChange(change: Row): DeskPanel {
  const type = text(change.change_type, "");
  if (type === "fundamental") return "financials";
  if (type === "event") return "catalysts";
  if (type === "news") return "news";
  if (type === "source-status") return "sources";
  return "chart";
}
function displayChangeValue(value: unknown, unit: unknown): string {
  if (value === null || value === undefined || value === "") return "Not observed";
  if (typeof value === "number") {
    if (text(unit) === "percentage-points") return `${value.toFixed(2)} pp`;
    if (text(unit) === "percent") return `${value.toFixed(2)}%`;
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 }).format(value);
  }
  return text(value);
}

function watchlistColumnLabel(mode: WatchlistViewMode, column: number): string {
  const labels: Record<WatchlistViewMode, [string, string]> = {
    price: ["Last / change", "Status"],
    performance: ["1W / 1M", "3M / coverage"],
    risk: ["Volatility", "RSI / coverage"],
    financials: ["Market cap", "Fundamentals"],
    technicals: ["Trend", "RSI / coverage"],
    catalysts: ["Next catalyst", "Exact news"],
    changes: ["Change count", "Severity"],
  };
  return labels[mode][column];
}

function watchlistSortValue(row: Row, mode: WatchlistViewMode): number {
  const advanced = record(row.advanced);
  const value = mode === "price"
    ? row.change_pct
    : mode === "changes"
      ? row._change_count
    : mode === "performance"
      ? advanced.return_1m_pct
      : mode === "risk"
        ? advanced.realized_volatility_1m_pct
      : mode === "technicals"
          ? advanced.rsi_14
          : mode === "catalysts"
            ? Date.parse(catalystDate(record(record(row.catalysts).next_event)))
            : advanced.market_cap;
  return numeric(value) ?? Number.NEGATIVE_INFINITY;
}

function watchlistDisplay(row: Row, mode: WatchlistViewMode) {
  const advanced = record(row.advanced);
  if (mode === "changes") {
    const count = numeric(row._change_count) ?? 0;
    const severity = text(row._change_severity, "none");
    return {
      primary: `${count} saved`,
      primaryDetail: count ? "since prior success" : "no observed change",
      primaryTone: count ? "warn" : "ok",
      secondary: severity,
      secondaryDetail: "source-preserved",
      secondaryTone: severity === "critical" ? "danger" : severity === "material" ? "warn" : "ok",
    };
  }
  if (mode === "performance") {
    return {
      primary: formatPercent(advanced.return_1w_pct),
      primaryDetail: `1M ${formatPercent(advanced.return_1m_pct)}`,
      primaryTone: returnTone(advanced.return_1w_pct),
      secondary: formatPercent(advanced.return_3m_pct),
      secondaryDetail: text(advanced.status),
      secondaryTone: statusTone(text(advanced.status)),
    };
  }
  if (mode === "risk") {
    return {
      primary: formatPercent(advanced.realized_volatility_1m_pct),
      primaryDetail: "1M annualized",
      primaryTone: "flat",
      secondary: formatNumber(advanced.rsi_14),
      secondaryDetail: text(advanced.data_gap, "Cached history"),
      secondaryTone: statusTone(text(advanced.status)),
    };
  }
  if (mode === "financials") {
    return {
      primary: compact(advanced.market_cap),
      primaryDetail: `P/E ${formatNumber(advanced.pe_ratio)}`,
      primaryTone: "flat",
      secondary: `EPS ${formatNumber(advanced.eps)}`,
      secondaryDetail: text(advanced.financial_source_status, "unavailable"),
      secondaryTone: statusTone(text(advanced.financial_source_status)),
    };
  }
  if (mode === "technicals") {
    return {
      primary: text(advanced.trend_state, "Unavailable"),
      primaryDetail: `SMA20 ${formatNumber(advanced.sma_20)}`,
      primaryTone: text(advanced.trend_state) === "bullish" ? "gain" : text(advanced.trend_state) === "bearish" ? "loss" : "flat",
      secondary: `RSI ${formatNumber(advanced.rsi_14)}`,
      secondaryDetail: text(advanced.status),
      secondaryTone: statusTone(text(advanced.status)),
    };
  }
  if (mode === "catalysts") {
    const catalysts = record(row.catalysts);
    const next = record(catalysts.next_event);
    const headlines = asRecordArray(catalysts.news);
    return {
      primary: catalystLabel(next),
      primaryDetail: catalystDate(next),
      primaryTone: Object.keys(next).length ? "flat" : "danger",
      secondary: `${headlines.length} exact`,
      secondaryDetail: text(catalysts.source_status),
      secondaryTone: statusTone(text(catalysts.source_status)),
    };
  }
  return {
    primary: formatPrice(row.last_price),
    primaryDetail: formatPercent(row.change_pct),
    primaryTone: returnTone(row.change_pct),
    secondary: text(row.refresh_status),
    secondaryDetail: shortTime(row.refresh_fetched_at || row.market_fetched_at),
    secondaryTone: statusTone(text(row.refresh_status)),
  };
}
