"use client";

import {
  Bell,
  BellRing,
  CalendarClock,
  Check,
  CirclePause,
  CirclePlay,
  Clock3,
  ExternalLink,
  History,
  ListFilter,
  Pause,
  Play,
  Plus,
  Power,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { ContractEnvelope, RuntimeMode, asRecordArray, isRecord } from "@/lib/contracts";

type Row = Record<string, unknown>;
type AlertTab = "rules" | "history" | "runs" | "schedule";
type AccountState = "fixture" | "loading" | "ready" | "signed-out" | "offline";

const RULE_TYPES = [
  ["price_above", "Price above"],
  ["price_below", "Price below"],
  ["absolute_percent_move", "Absolute % move"],
  ["material_saved_change", "Material saved change"],
  ["source_degradation", "Source degradation"],
] as const;

const EVIDENCE_LABELS: Record<string, "Analyst" | "News" | "Brief" | "Map"> = {
  analyst: "Analyst",
  news: "News",
  brief: "Brief",
  map: "Map",
};

export function WatchlistAlertManager({
  envelope,
  schedulerEnvelope,
  runtimeMode,
  initialTab,
  initialSelectedTrigger,
}: {
  envelope: ContractEnvelope;
  schedulerEnvelope?: ContractEnvelope;
  runtimeMode: RuntimeMode;
  initialTab?: string;
  initialSelectedTrigger?: string;
}) {
  const [managerEnvelope, setManagerEnvelope] = useState(envelope);
  const [hostedSchedulerEnvelope, setHostedSchedulerEnvelope] = useState(schedulerEnvelope ?? envelope);
  const [accountState, setAccountState] = useState<AccountState>(runtimeMode === "fixture" ? "fixture" : "loading");
  const [tab, setTab] = useState<AlertTab>(normalizeTab(initialTab));
  const [selectedTrigger, setSelectedTrigger] = useState(initialSelectedTrigger ?? "");
  const [statusMessage, setStatusMessage] = useState("Alert Manager is ready. Page views do not start monitoring.");
  const [busy, setBusy] = useState(false);
  const [watchlistId, setWatchlistId] = useState("");
  const [symbol, setSymbol] = useState("");
  const [ruleType, setRuleType] = useState("price_above");
  const [threshold, setThreshold] = useState("200");
  const [frequency, setFrequency] = useState("15m");
  const [sessionPolicy, setSessionPolicy] = useState("market-aware");
  const [cooldown, setCooldown] = useState("60");
  const [severity, setSeverity] = useState("high");
  const [expiresAt, setExpiresAt] = useState(defaultExpiry());
  const [scheduleCadence, setScheduleCadence] = useState("60");
  const [scheduleTimezone, setScheduleTimezone] = useState("Asia/Seoul");
  const [scheduleConsent, setScheduleConsent] = useState(false);

  const data = record(managerEnvelope.data);
  const summary = record(data.summary);
  const rules = asRecordArray(data.rules);
  const triggers = asRecordArray(data.triggers);
  const evaluations = asRecordArray(data.evaluations);
  const watchlists = asRecordArray(data.watchlists);
  const worker = record(data.worker);
  const schedulerData = record(hostedSchedulerEnvelope.data);
  const hosted = record(schedulerData.readiness);
  const schedules = asRecordArray(schedulerData.schedules);
  const schedulerRuns = asRecordArray(schedulerData.runs);
  const schedulerSummary = record(schedulerData.summary);
  const effectiveWatchlistId = watchlists.some((row) => text(row.watchlist_id) === watchlistId)
    ? watchlistId
    : text(watchlists[0]?.watchlist_id);
  const selectedWatchlist = watchlists.find((row) => text(row.watchlist_id) === effectiveWatchlistId) ?? watchlists[0];
  const symbols = asRecordArray(selectedWatchlist?.items);
  const effectiveSymbol = symbols.some((row) => text(row.symbol) === symbol) ? symbol : text(symbols[0]?.symbol);
  const selected = triggers.find((row) => text(row.trigger_id) === selectedTrigger) ?? triggers[0];
  const effectiveSelectedTrigger = text(selected?.trigger_id);
  const newTriggers = triggers.filter((row) => text(row.review_state) === "new");
  const activeRules = rules.filter((row) => text(row.state) === "active");

  const returnState = new URLSearchParams({
    view: "alert-manager",
    mode: runtimeMode === "fixture" ? "fixture" : "cache",
    tab,
    ...(effectiveSelectedTrigger ? { selectedTrigger: effectiveSelectedTrigger } : {}),
  }).toString();

  async function loadScheduler(announce = true) {
    try {
      const response = await fetch("/api/account/alert-manager/scheduler", { cache: "no-store", credentials: "same-origin" });
      if (!response.ok) return false;
      const payload = await response.json();
      if (!isRecord(payload) || !isRecord(payload.data)) return false;
      setHostedSchedulerEnvelope(payload as unknown as ContractEnvelope);
      if (announce) setStatusMessage("Hosted schedule state loaded. This read made zero market-provider calls.");
      return true;
    } catch {
      if (announce) setStatusMessage("Hosted schedule state is unavailable. Existing local alert evidence remains intact.");
      return false;
    }
  }

  async function loadManager(announce = true) {
    setAccountState("loading");
    try {
      const response = await fetch("/api/account/alert-manager", { cache: "no-store", credentials: "same-origin" });
      if (response.status === 401) {
        setAccountState("signed-out");
        setStatusMessage("Sign in from Account Research to manage tenant-owned alerts. The fixture remains visible.");
        return;
      }
      if (!response.ok) throw new Error("Account Alert Manager is unavailable.");
      const payload = await response.json();
      if (!isRecord(payload) || !isRecord(payload.data)) throw new Error("Alert Manager returned an invalid contract.");
      setManagerEnvelope(payload as unknown as ContractEnvelope);
      await loadScheduler(false);
      setAccountState("ready");
      if (announce) setStatusMessage("Account rules and trigger history loaded with zero market-provider calls.");
    } catch {
      setAccountState("offline");
      setStatusMessage("Account runtime is offline. Fictional fixture evidence remains visible and no monitoring job was started.");
    }
  }

  useEffect(() => {
    const timer = runtimeMode !== "fixture" ? window.setTimeout(() => void loadManager(), 0) : null;
    // Runtime mode is immutable for this page instance.
    return () => { if (timer !== null) window.clearTimeout(timer); };
  }, [runtimeMode]); // eslint-disable-line react-hooks/exhaustive-deps

  async function mutate(path: string, method: "POST" | "PATCH" | "DELETE", body?: Row) {
    const response = await fetch(path, {
      method,
      cache: "no-store",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfCookie(),
        "X-Alert-Origin-State": returnState,
      },
      ...(method !== "DELETE" ? { body: JSON.stringify(body ?? {}) } : {}),
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 409) throw new Error("This item changed in another session. Reloaded the latest version.");
    if (!response.ok) throw new Error(text(record(payload).detail, "Alert action did not complete."));
    return payload;
  }

  async function createRule(event: FormEvent) {
    event.preventDefault();
    if (accountState !== "ready") {
      setStatusMessage("Account sign-in is required before a rule can be persisted.");
      return;
    }
    setBusy(true);
    try {
      const normalizedThreshold = ruleType === "material_saved_change"
        ? threshold || "material"
        : ruleType === "source_degradation"
          ? threshold || "stale"
          : Number(threshold);
      await mutate("/api/account/alert-manager/rules", "POST", {
        watchlist_id: effectiveWatchlistId,
        symbol: effectiveSymbol,
        rule_type: ruleType,
        threshold: normalizedThreshold,
        threshold_unit: ruleType.includes("price") ? "USD" : ruleType === "absolute_percent_move" ? "%" : ruleType === "source_degradation" ? "status" : "severity",
        frequency,
        session_policy: sessionPolicy,
        cooldown_minutes: Number(cooldown),
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        severity,
        expected_version: 0,
      });
      setStatusMessage(`${effectiveSymbol} rule created. It will evaluate only when due against a validated saved observation.`);
      await loadManager(false);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Rule creation failed.");
      await loadManager(false);
    } finally {
      setBusy(false);
    }
  }

  async function runDueChecks() {
    if (accountState !== "ready") {
      setStatusMessage("Account sign-in is required before due checks can run.");
      return;
    }
    setBusy(true);
    try {
      await mutate("/api/account/alert-manager/evaluations", "POST", { idempotency_key: `alert-ui-${window.crypto.randomUUID()}`, mode: "manual" });
      setTab("history");
      setStatusMessage("Due rules evaluated from saved Phase 6N observations. No page-view polling or market-provider request was made.");
      await loadManager(false);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Due evaluation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function changeRule(row: Row, action: "pause" | "resume" | "cancel" | "delete") {
    setBusy(true);
    try {
      const resourceId = encodeURIComponent(text(row.resource_id));
      const version = number(row.version, 1);
      if (action === "delete") {
        await mutate(`/api/account/alert-manager/rules/${resourceId}?expected_version=${version}`, "DELETE");
      } else {
        await mutate(`/api/account/alert-manager/rules/${resourceId}`, "PATCH", { action, expected_version: version });
      }
      setStatusMessage(`Rule ${action} completed without a market-provider request.`);
      await loadManager(false);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Rule update failed.");
      await loadManager(false);
    } finally {
      setBusy(false);
    }
  }

  async function reviewTrigger(row: Row) {
    setBusy(true);
    try {
      await mutate(`/api/account/alert-manager/triggers/${encodeURIComponent(text(row.trigger_id))}`, "PATCH", {
        action: "acknowledge",
        expected_version: number(row.version, 1),
      });
      setStatusMessage("Trigger acknowledged. Observation and retrieval clocks were not changed.");
      await loadManager(false);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Trigger acknowledgement failed.");
      await loadManager(false);
    } finally {
      setBusy(false);
    }
  }

  async function createHostedSchedule() {
    const selectedRule = rules.find((row) => text(row.watchlist_id) === effectiveWatchlistId && text(row.state) !== "deleted") ?? rules[0];
    if (accountState !== "ready" || !selectedRule || !scheduleConsent) {
      setStatusMessage(!selectedRule ? "Create an alert rule before adding a hosted schedule." : "Explicit schedule consent is required.");
      return;
    }
    setBusy(true);
    try {
      const payload = await mutate("/api/account/alert-manager/scheduler/schedules", "POST", {
        watchlist_id: effectiveWatchlistId,
        alert_rule_id: text(selectedRule.resource_id),
        timezone: scheduleTimezone,
        cadence_minutes: Number(scheduleCadence),
        max_symbols: 1,
        max_provider_calls: 4,
        max_attempts: 2,
        timeout_seconds: 90,
      });
      if (isRecord(payload) && isRecord(payload.data)) setHostedSchedulerEnvelope(payload as unknown as ContractEnvelope);
      setScheduleConsent(false);
      setTab("schedule");
      setStatusMessage("A disabled bounded schedule was created. Enable remains a separate explicit action.");
      await loadScheduler(false);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Hosted schedule creation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function changeHostedSchedule(row: Row, action: "enable" | "pause" | "resume" | "kill" | "recover" | "retry" | "delete") {
    if (accountState !== "ready") {
      setStatusMessage("Account sign-in is required before schedule controls can change.");
      return;
    }
    if ((action === "enable" || action === "recover") && !scheduleConsent) {
      setStatusMessage("Check explicit consent before enabling or recovering hosted monitoring.");
      return;
    }
    if (["kill", "delete"].includes(action) && !window.confirm(action === "kill" ? "Kill this schedule and force any active run to stop at commit?" : "Remove this stopped schedule? Retained audit evidence will remain.")) return;
    setBusy(true);
    try {
      const payload = await mutate(`/api/account/alert-manager/scheduler/schedules/${encodeURIComponent(text(row.schedule_id))}`, "PATCH", {
        action,
        expected_version: number(row.version, 1),
        ...(["enable", "recover"].includes(action) ? { consent: true } : {}),
      });
      if (isRecord(payload) && isRecord(payload.data)) setHostedSchedulerEnvelope(payload as unknown as ContractEnvelope);
      if (["enable", "recover"].includes(action)) setScheduleConsent(false);
      setStatusMessage(`Hosted schedule ${action} completed. No market-provider call was made by this control action.`);
      await loadScheduler(false);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Hosted schedule action failed.");
      await loadScheduler(false);
    } finally {
      setBusy(false);
    }
  }

  function chooseRuleType(next: string) {
    setRuleType(next);
    if (next === "source_degradation") setThreshold("stale");
    else if (next === "material_saved_change") setThreshold("material");
    else if (next === "absolute_percent_move") setThreshold("3");
    else setThreshold("200");
  }

  return (
    <section
      className="alert-manager"
      data-phase6o-alert-manager="true"
      data-account-state={accountState}
      data-worker-state={text(worker.state, "stopped")}
      data-active-tab={tab}
      aria-labelledby="alert-manager-title"
    >
      <header className="alert-manager-header">
        <div>
          <span className="eyebrow">Stored-observation monitoring</span>
          <h2 id="alert-manager-title">Watchlist Alert Manager</h2>
          <p>Explainable rules, due-state truth and in-app evidence history for saved symbols.</p>
        </div>
        <div className="alert-manager-actions">
          <button type="button" onClick={() => void loadManager()} disabled={busy || runtimeMode === "fixture"} title="Reload account alert state">
            <RefreshCw size={15} aria-hidden="true" /> Reload
          </button>
          <button type="button" className="primary" onClick={() => void runDueChecks()} disabled={busy || accountState !== "ready"} title="Evaluate only due rules from stored observations">
            <Play size={15} aria-hidden="true" /> Run due checks
          </button>
        </div>
      </header>

      <div className="alert-manager-truth-strip">
        <span className={`status-dot ${accountState === "ready" ? "ok" : "warn"}`} aria-hidden="true" />
        <strong>{accountState === "ready" ? "Account isolated" : accountState === "fixture" ? "Fictional fixture" : accountState === "signed-out" ? "Sign-in required" : "Account unavailable"}</strong>
        <span><Clock3 size={13} aria-hidden="true" /> {text(worker.state) === "stopped" ? "Worker stopped" : `Worker ${text(worker.state, "offline")}`}</span>
        <span><ShieldAlert size={13} aria-hidden="true" /> Scheduler {text(hosted.status, "unavailable").replaceAll("-", " ")}</span>
        <span>In-app only</span>
        <Link prefetch={false} href="/?view=watchlist-desk&mode=local">Open Watchlist</Link>
      </div>

      <div className="alert-manager-summary" aria-label="Alert summary">
        <Metric label="Rules" value={number(summary.rule_count, rules.length)} detail={`${activeRules.length} active`} />
        <Metric label="Due now" value={number(summary.due_count)} detail="stored checks" />
        <Metric label="New triggers" value={number(summary.new_trigger_count, newTriggers.length)} detail={`${triggers.length} retained`} tone={newTriggers.length ? "high" : "neutral"} />
        <Metric label="Provider calls" value={number(summary.provider_call_count)} detail="manager reads" />
      </div>

      <div className="alert-manager-layout">
        <aside className="alert-rule-builder" aria-labelledby="alert-rule-builder-title">
          <div className="section-heading">
            <div><span className="eyebrow">Exact saved symbol</span><h3 id="alert-rule-builder-title">Create rule</h3></div>
            <Plus size={16} aria-hidden="true" />
          </div>
          <form onSubmit={(event) => void createRule(event)}>
            <label>Watchlist<select value={effectiveWatchlistId} onChange={(event) => { setWatchlistId(event.target.value); setSymbol(""); }}>{watchlists.map((row) => <option key={text(row.watchlist_id)} value={text(row.watchlist_id)}>{text(row.name, "Saved Watchlist")}</option>)}</select></label>
            <label>Symbol<select value={effectiveSymbol} onChange={(event) => setSymbol(event.target.value)}>{symbols.map((row) => <option key={text(row.symbol)} value={text(row.symbol)}>{text(row.symbol)} · {text(row.display_name, text(row.asset_class))}</option>)}</select></label>
            <label>Condition<select value={ruleType} onChange={(event) => chooseRuleType(event.target.value)}>{RULE_TYPES.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label>{ruleType === "source_degradation" ? "Status threshold" : ruleType === "material_saved_change" ? "Materiality" : "Threshold"}
              {ruleType === "source_degradation" ? <select value={threshold} onChange={(event) => setThreshold(event.target.value)}><option value="cached">Cached</option><option value="aging">Aging</option><option value="stale">Stale</option><option value="rate-limited">Rate limited</option><option value="unavailable">Unavailable</option></select>
                : ruleType === "material_saved_change" ? <select value={threshold} onChange={(event) => setThreshold(event.target.value)}><option value="info">Any saved change</option><option value="material">Material</option><option value="high">High</option><option value="critical">Critical</option></select>
                  : <input type="number" min="0" step="any" value={threshold} onChange={(event) => setThreshold(event.target.value)} required />}
            </label>
            <div className="alert-builder-pair">
              <label>Frequency<select value={frequency} onChange={(event) => setFrequency(event.target.value)}><option value="5m">5 min</option><option value="15m">15 min</option><option value="1h">1 hour</option><option value="4h">4 hours</option><option value="1d">1 day</option></select></label>
              <label>Cooldown<select value={cooldown} onChange={(event) => setCooldown(event.target.value)}><option value="0">None</option><option value="15">15 min</option><option value="60">1 hour</option><option value="240">4 hours</option><option value="1440">1 day</option></select></label>
            </div>
            <label>Session<select value={sessionPolicy} onChange={(event) => setSessionPolicy(event.target.value)}><option value="market-aware">Market aware</option><option value="regular-only">Regular only</option><option value="extended">Extended</option><option value="continuous">Continuous</option></select></label>
            <div className="alert-builder-pair">
              <label>Severity<select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="watch">Watch</option><option value="material">Material</option><option value="high">High</option><option value="critical">Critical</option></select></label>
              <label>Expires<input type="datetime-local" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} /></label>
            </div>
            <button type="submit" className="primary alert-create-button" disabled={busy || accountState !== "ready"}><Bell size={15} aria-hidden="true" /> Create rule</button>
          </form>
          <p className="alert-builder-caveat">Page views never start jobs. Market conditions require fresh or cached validated evidence; stale rows become gaps.</p>
        </aside>

        <main className="alert-manager-main">
          <div className="alert-manager-tabs" role="tablist" aria-label="Alert Manager views">
            <TabButton active={tab === "rules"} onClick={() => setTab("rules")} icon={ListFilter}>Rules <span>{rules.length}</span></TabButton>
            <TabButton active={tab === "history"} onClick={() => setTab("history")} icon={BellRing}>Trigger history <span>{triggers.length}</span></TabButton>
            <TabButton active={tab === "runs"} onClick={() => setTab("runs")} icon={History}>Runs <span>{evaluations.length}</span></TabButton>
            <TabButton active={tab === "schedule"} onClick={() => setTab("schedule")} icon={CalendarClock}>Hosted schedule <span>{schedules.length}</span></TabButton>
          </div>

          {tab === "rules" ? <RuleTable rows={rules} busy={busy} onAction={changeRule} /> : null}
          {tab === "history" ? <TriggerTable rows={triggers} selectedId={effectiveSelectedTrigger} onSelect={(row) => setSelectedTrigger(text(row.trigger_id))} onReview={reviewTrigger} busy={busy} /> : null}
          {tab === "runs" ? <RunTable rows={evaluations} /> : null}
          {tab === "schedule" ? (
            <HostedSchedulePanel
              schedules={schedules}
              runs={schedulerRuns}
              summary={schedulerSummary}
              readiness={hosted}
              accountState={accountState}
              busy={busy}
              cadence={scheduleCadence}
              timezoneName={scheduleTimezone}
              consent={scheduleConsent}
              hasRule={rules.length > 0}
              onCadence={setScheduleCadence}
              onTimezone={setScheduleTimezone}
              onConsent={setScheduleConsent}
              onCreate={() => void createHostedSchedule()}
              onAction={(row, action) => void changeHostedSchedule(row, action)}
            />
          ) : null}
        </main>

        <aside className="alert-evidence-inspector" aria-labelledby="alert-evidence-title">
          <div className="section-heading"><div><span className="eyebrow">Exact trigger</span><h3 id="alert-evidence-title">Source & clocks</h3></div><ExternalLink size={16} aria-hidden="true" /></div>
          {selected ? <TriggerInspector row={selected} runtimeMode={runtimeMode} /> : <div className="alert-empty"><Bell size={18} aria-hidden="true" /><strong>No trigger selected</strong><span>Run a due check after a validated observation is saved.</span></div>}
        </aside>
      </div>

      {rules.length === 0 ? <div className="alert-empty wide"><Bell size={18} aria-hidden="true" /><strong>No rules yet</strong><span>Create one bounded explainable rule from a saved symbol.</span></div> : null}
      <p className="alert-manager-live" aria-live="polite" role="status">{statusMessage}</p>
    </section>
  );
}

function Metric({ label, value, detail, tone = "neutral" }: { label: string; value: number; detail: string; tone?: string }) {
  return <div className={`alert-metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

function TabButton({ active, onClick, icon: Icon, children }: { active: boolean; onClick: () => void; icon: typeof Bell; children: React.ReactNode }) {
  return <button type="button" role="tab" aria-selected={active} className={active ? "active" : ""} onClick={onClick}><Icon size={14} aria-hidden="true" />{children}</button>;
}

function RuleTable({ rows, busy, onAction }: { rows: Row[]; busy: boolean; onAction: (row: Row, action: "pause" | "resume" | "cancel" | "delete") => void }) {
  if (!rows.length) return <div className="alert-empty"><Bell size={18} aria-hidden="true" /><strong>No rules yet</strong><span>The rule builder is ready when an account Watchlist is available.</span></div>;
  return <div className="alert-table-wrap"><table className="alert-rule-table"><thead><tr><th>Symbol / condition</th><th>State</th><th>Schedule</th><th>Last evidence</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{rows.map((row) => {
    const schedule = record(row.schedule); const state = text(row.state, "paused");
    return <tr key={text(row.resource_id)} data-rule-state={state}><td><strong>{text(row.symbol)}</strong><span>{ruleLabel(text(row.rule_type))} {formatValue(row.threshold)} {text(row.threshold_unit)}</span></td><td><span className={`alert-state ${state}`}>{state}</span><small>{text(row.state_reason)}</small></td><td><strong>{text(schedule.frequency)}</strong><span>{text(schedule.session_policy)}</span><small>Due {formatTime(schedule.next_due_at)}</small></td><td><strong>{text(row.last_snapshot_id, "No snapshot")}</strong><span>{formatTime(row.last_evaluated_at)}</span></td><td><div className="alert-row-actions">{state === "active" ? <button type="button" title="Pause rule" disabled={busy} onClick={() => onAction(row, "pause")}><Pause size={14} aria-hidden="true" /></button> : state === "paused" ? <button type="button" title="Resume rule" disabled={busy} onClick={() => onAction(row, "resume")}><CirclePlay size={14} aria-hidden="true" /></button> : null}<button type="button" title="Cancel rule" disabled={busy || ["cancelled", "deleted"].includes(state)} onClick={() => onAction(row, "cancel")}><CirclePause size={14} aria-hidden="true" /></button><button type="button" title="Delete rule" disabled={busy || state === "deleted"} onClick={() => onAction(row, "delete")}><Trash2 size={14} aria-hidden="true" /></button></div></td></tr>;
  })}</tbody></table></div>;
}

function TriggerTable({ rows, selectedId, onSelect, onReview, busy }: { rows: Row[]; selectedId: string; onSelect: (row: Row) => void; onReview: (row: Row) => void; busy: boolean }) {
  if (!rows.length) return <div className="alert-empty"><BellRing size={18} aria-hidden="true" /><strong>No trigger history</strong><span>Due checks store only deduplicated matches.</span></div>;
  return <div className="alert-trigger-list">{rows.map((row) => <article key={text(row.trigger_id)} className={text(row.trigger_id) === selectedId ? "selected" : ""} data-review-state={text(row.review_state)}><button type="button" className="alert-trigger-select" onClick={() => onSelect(row)}><span className={`alert-severity ${text(row.severity)}`}>{text(row.severity)}</span><strong>{text(row.symbol)} · {formatValue(row.observed_value)}</strong><small>{text(row.message)}</small><time>{formatTime(record(row.clocks).triggered_at)}</time></button>{text(row.review_state) !== "acknowledged" ? <button type="button" className="alert-ack" title="Acknowledge trigger" disabled={busy} onClick={() => onReview(row)}><Check size={14} aria-hidden="true" /> Acknowledge</button> : <span className="alert-acknowledged"><Check size={13} aria-hidden="true" /> Acknowledged</span>}</article>)}</div>;
}

function RunTable({ rows }: { rows: Row[] }) {
  if (!rows.length) return <div className="alert-empty"><History size={18} aria-hidden="true" /><strong>No evaluation runs</strong><span>Manual checks and explicit worker runs appear here.</span></div>;
  return <div className="alert-table-wrap"><table><thead><tr><th>Status</th><th>Mode</th><th>Due / evaluated</th><th>Triggered / deduped</th><th>Gaps</th><th>Completed</th></tr></thead><tbody>{rows.map((row) => <tr key={text(row.run_id)}><td><span className={`alert-state ${text(row.status)}`}>{text(row.status)}</span></td><td>{text(row.mode)}</td><td>{number(row.due_count)} / {number(row.evaluated_count)}</td><td>{number(row.triggered_count)} / {number(row.deduped_count)}</td><td>{number(row.data_gap_count)}</td><td>{formatTime(row.completed_at)}</td></tr>)}</tbody></table></div>;
}

type HostedScheduleAction = "enable" | "pause" | "resume" | "kill" | "recover" | "retry" | "delete";

function HostedSchedulePanel({
  schedules,
  runs,
  summary,
  readiness,
  accountState,
  busy,
  cadence,
  timezoneName,
  consent,
  hasRule,
  onCadence,
  onTimezone,
  onConsent,
  onCreate,
  onAction,
}: {
  schedules: Row[];
  runs: Row[];
  summary: Row;
  readiness: Row;
  accountState: AccountState;
  busy: boolean;
  cadence: string;
  timezoneName: string;
  consent: boolean;
  hasRule: boolean;
  onCadence: (value: string) => void;
  onTimezone: (value: string) => void;
  onConsent: (value: boolean) => void;
  onCreate: () => void;
  onAction: (row: Row, action: HostedScheduleAction) => void;
}) {
  const status = text(readiness.status, "hosted-unverified");
  const verified = readiness.hosted_scheduler_verified === true;
  const globalKill = readiness.global_kill_switch !== false;
  const latest = runs[0];
  const latestSource = record(latest?.source);
  const latestQuota = record(latest?.quota);
  const latestResult = record(latest?.result);

  return (
    <section className="hosted-schedule-panel" data-hosted-status={status} aria-labelledby="hosted-schedule-title">
      <header className="hosted-schedule-heading">
        <div>
          <span className="eyebrow">Bounded recurring observation</span>
          <h3 id="hosted-schedule-title">Hosted schedule</h3>
          <p>One saved Watchlist, one alert policy and one quota-bounded due window.</p>
        </div>
        <span className={`hosted-verification ${verified ? "verified" : "unverified"}`}>
          <ShieldAlert size={14} aria-hidden="true" /> {verified ? "Hosted verified" : "Hosted unverified"}
        </span>
      </header>

      <div className="hosted-schedule-truth" role="status">
        <span><strong>{text(summary.status, status)}</strong> readiness</span>
        <span>{globalKill ? "Global kill armed" : "Operator gate available"}</span>
        <span>At-least-once, idempotent effects</span>
        <span>Reads: 0 provider calls</span>
      </div>

      {schedules.length === 0 ? (
        <div className="hosted-schedule-create">
          <div><strong>No hosted schedule</strong><span>Create is disabled-first. Enabling is always a second explicit action.</span></div>
          <label>Cadence<select value={cadence} onChange={(event) => onCadence(event.target.value)}><option value="60">Hourly</option><option value="240">Every 4 hours</option><option value="1440">Daily</option></select></label>
          <label>Timezone<input value={timezoneName} onChange={(event) => onTimezone(event.target.value)} maxLength={64} /></label>
          <label className="hosted-consent"><input type="checkbox" checked={consent} onChange={(event) => onConsent(event.target.checked)} /> I understand this creates a bounded schedule definition. It does not prove hosted operation.</label>
          <button type="button" className="primary" disabled={busy || accountState !== "ready" || !hasRule || !consent} onClick={onCreate}><Plus size={14} aria-hidden="true" /> Create disabled schedule</button>
        </div>
      ) : (
        <div className="hosted-schedule-list">
          {schedules.map((row) => {
            const state = text(row.state, "disabled");
            const bounds = record(row.bounds);
            return (
              <article key={text(row.schedule_id)} className="hosted-schedule-card" data-schedule-state={state}>
                <div className="hosted-schedule-card-head">
                  <div><span className={`alert-state ${state}`}>{state}</span><strong>{number(row.cadence_minutes, 60) === 1440 ? "Daily" : `Every ${number(row.cadence_minutes, 60) / 60}h`}</strong><small>{text(row.timezone, "UTC")}</small></div>
                  <div><span>Next due</span><strong>{formatTime(row.next_due_local ?? row.next_due_at)}</strong><small>Last complete {formatTime(row.last_completed_at)}</small></div>
                  <div><span>Run budget</span><strong>{number(bounds.max_symbols, 1)} symbol / {number(bounds.max_provider_calls, 0)} calls</strong><small>{number(bounds.timeout_seconds, 0)}s timeout, {number(bounds.max_attempts, 1)} attempts</small></div>
                </div>
                <label className="hosted-consent compact"><input type="checkbox" checked={consent} onChange={(event) => onConsent(event.target.checked)} /> Explicit consent for enable or recovery</label>
                <div className="hosted-schedule-actions">
                  {state === "disabled" ? <button type="button" className="primary" disabled={busy || accountState !== "ready" || !consent} onClick={() => onAction(row, "enable")}><Power size={14} aria-hidden="true" /> Enable</button> : null}
                  {state === "enabled" ? <button type="button" disabled={busy} onClick={() => onAction(row, "pause")}><Pause size={14} aria-hidden="true" /> Pause</button> : null}
                  {state === "paused" ? <button type="button" disabled={busy} onClick={() => onAction(row, "resume")}><Play size={14} aria-hidden="true" /> Resume</button> : null}
                  {state === "enabled" ? <button type="button" disabled={busy} onClick={() => onAction(row, "retry")}><RotateCcw size={14} aria-hidden="true" /> Retry due</button> : null}
                  {!['killed', 'deleted'].includes(state) ? <button type="button" className="danger" disabled={busy} onClick={() => onAction(row, "kill")}><ShieldAlert size={14} aria-hidden="true" /> Kill</button> : null}
                  {state === "killed" ? <button type="button" disabled={busy || !consent} onClick={() => onAction(row, "recover")}><RotateCcw size={14} aria-hidden="true" /> Recover paused</button> : null}
                  {["disabled", "paused", "killed"].includes(state) ? <button type="button" disabled={busy} onClick={() => onAction(row, "delete")}><Trash2 size={14} aria-hidden="true" /> Delete</button> : null}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="hosted-run-section">
        <div className="section-heading"><div><span className="eyebrow">Latest persisted evidence</span><h3>Run truth</h3></div><History size={16} aria-hidden="true" /></div>
        {latest ? (
          <>
            <div className="hosted-run-summary">
              <div><span>Status</span><strong className={`alert-state ${text(latest.status)}`}>{text(latest.status)}</strong><small>Attempt {number(latest.attempt_count)}</small></div>
              <div><span>Source</span><strong>{text(latestSource.provider, "unavailable")}</strong><small>{text(latestSource.source_status, "unavailable")}</small></div>
              <div><span>Quota</span><strong>{number(latestQuota.used)} / {number(latestQuota.budget)}</strong><small>{number(latestQuota.remaining)} remaining</small></div>
              <div><span>Outcome</span><strong>{number(latest.trigger_count)} trigger</strong><small>{formatTime(record(latest.clocks).completed_at)}</small></div>
            </div>
            <div className="hosted-run-caveat"><strong>Caveat</strong><span>{text(latestResult.caveat, "No additional caveat recorded.")}</span><strong>Data gap</strong><span>{text(latestResult.data_gap, "No recorded gap.")}</span></div>
          </>
        ) : <div className="alert-empty"><Clock3 size={18} aria-hidden="true" /><strong>No persisted hosted run</strong><span>A schedule definition or local fixture is not evidence of a deployed recurring invocation.</span></div>}
      </div>
    </section>
  );
}

function TriggerInspector({ row, runtimeMode }: { row: Row; runtimeMode: RuntimeMode }) {
  const clocks = record(row.clocks);
  const evidence = record(row.evidence);
  const links = asRecordArray(row.evidence_links);
  return <div className="alert-inspector-body"><div className="alert-inspector-head"><span className={`alert-severity ${text(row.severity)}`}>{text(row.severity)}</span><strong>{text(row.symbol)} · {ruleLabel(text(row.metric))}</strong><p>{text(row.message)}</p></div><dl><div><dt>Observed</dt><dd>{formatValue(row.observed_value)}</dd></div><div><dt>Threshold</dt><dd>{formatValue(row.threshold)}</dd></div><div><dt>Source</dt><dd>{text(row.provider, "stored observation")}</dd></div><div><dt>Status</dt><dd>{text(row.source_status)}</dd></div><div><dt>Snapshot</dt><dd>{text(evidence.snapshot_id, "unavailable")}</dd></div><div><dt>Confidence</dt><dd>{formatValue(evidence.confidence)}</dd></div></dl><div className="alert-clock-grid"><Clock label="Observation" value={clocks.observed_at} /><Clock label="Retrieval" value={clocks.retrieved_at} /><Clock label="Evaluation" value={clocks.evaluated_at} /><Clock label="Trigger" value={clocks.triggered_at} /><Clock label="Review" value={clocks.reviewed_at} /></div><div className="alert-caveat"><strong>Caveat</strong><span>{text(row.caveat, "No additional caveat recorded.")}</span><strong>Data gap</strong><span>{text(row.data_gap, "No recorded gap.")}</span></div><nav className="alert-evidence-links" aria-label="Exact trigger evidence">{links.map((link) => { const kind = text(link.kind); return <Link prefetch={false} key={kind} href={withReturnState(text(link.href), row, runtimeMode)}>{EVIDENCE_LABELS[kind] ?? text(link.label, "Evidence")}<ExternalLink size={12} aria-hidden="true" /></Link>; })}</nav></div>;
}

function Clock({ label, value }: { label: string; value: unknown }) { return <div><span>{label}</span><time>{formatTime(value)}</time></div>; }
function normalizeTab(value?: string): AlertTab { return value === "history" || value === "runs" || value === "schedule" ? value : "rules"; }
function record(value: unknown): Row { return isRecord(value) ? value : {}; }
function text(value: unknown, fallback = ""): string { return typeof value === "string" && value.trim() ? value : fallback; }
function number(value: unknown, fallback = 0): number { const current = Number(value); return Number.isFinite(current) ? current : fallback; }
function formatValue(value: unknown): string { if (typeof value === "number") return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value); return text(value, "—"); }
function formatTime(value: unknown): string { const parsed = Date.parse(text(value)); return Number.isFinite(parsed) ? new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(parsed) : "Not yet"; }
function ruleLabel(value: string): string { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function csrfCookie(): string { return decodeURIComponent(document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("gt_csrf="))?.split("=").slice(1).join("=") || ""); }
function defaultExpiry(): string { const value = new Date(Date.now() + 7 * 86_400_000); return value.toISOString().slice(0, 16); }
function withReturnState(href: string, row: Row, runtimeMode: RuntimeMode): string { try { const targetMode = runtimeMode === "fixture" ? "fixture" : "cache"; const url = new URL(href, window.location.origin); url.searchParams.set("mode", targetMode); url.searchParams.set("originView", "alert-manager"); url.searchParams.set("originState", new URLSearchParams({ view: "alert-manager", mode: targetMode, tab: "history", selectedTrigger: text(row.trigger_id) }).toString()); return `${url.pathname}?${url.searchParams}`; } catch { return `/?view=alert-manager&mode=${runtimeMode === "fixture" ? "fixture" : "cache"}&tab=history`; } }
