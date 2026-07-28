"use client";

import {
  BellOff,
  Check,
  CheckCheck,
  Clock3,
  ExternalLink,
  FileText,
  Filter,
  Gauge,
  MapPinned,
  Newspaper,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  SlidersHorizontal,
  Square,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import type { ContractEnvelope, RuntimeMode } from "@/lib/contracts";


type Row = Record<string, unknown>;
type ReviewState = "new" | "reviewed" | "acknowledged" | "snoozed";
type ReviewScope = "local" | "account";

interface LocalReviewRow {
  review_state: ReviewState;
  prior_state: "new" | "reviewed";
  snoozed_until: string | null;
  version: number;
  reviewed_at?: string | null;
  acknowledged_at?: string | null;
}

interface LocalAttentionState {
  states: Record<string, LocalReviewRow>;
  policy: {
    minimum_severity: string;
    included_change_kinds: string[];
    source_health_handling: string;
    version: number;
  };
  checkpoint: { reviewed_through_at: string | null; version: number };
}

interface AttentionDeskProps {
  envelope: ContractEnvelope;
  runtimeMode: RuntimeMode;
  initialSeverity?: string;
  initialKind?: string;
  initialSource?: string;
  initialRegion?: string;
  initialReview?: string;
}

const STORAGE_KEY = "global-terminal.attention-desk.v1";
const SEVERITY_SCORE: Record<string, number> = { info: 10, material: 30, high: 50, critical: 70 };
const DEFAULT_LOCAL_STATE: LocalAttentionState = {
  states: {},
  policy: {
    minimum_severity: "info",
    included_change_kinds: ["market-change", "new-evidence", "source-degradation", "stale-evidence", "resolved"],
    source_health_handling: "include",
    version: 0,
  },
  checkpoint: { reviewed_through_at: null, version: 0 },
};
const OBSERVATION_TERMINAL_STATES = new Set(["partial", "completed", "cancelled", "failed"]);
const OBSERVATION_RUN_STATES = ["queued", "running", "partial", "completed", "cancelled", "failed"];

export function AttentionDesk({
  envelope,
  runtimeMode,
  initialSeverity = "all",
  initialKind = "all",
  initialSource = "all",
  initialRegion = "all",
  initialReview = "needs-review",
}: AttentionDeskProps) {
  const router = useRouter();
  const [data, setData] = useState<Row>(() => record(envelope.data));
  const [localState, setLocalState] = useState<LocalAttentionState>(DEFAULT_LOCAL_STATE);
  const [reviewScope, setReviewScope] = useState<ReviewScope>("local");
  const [severity, setSeverity] = useState(initialSeverity);
  const [kind, setKind] = useState(initialKind);
  const [source, setSource] = useState(initialSource);
  const [region, setRegion] = useState(initialRegion);
  const [reviewFilter, setReviewFilter] = useState(initialReview);
  const [selectedFingerprint, setSelectedFingerprint] = useState("");
  const [statusMessage, setStatusMessage] = useState("Local review state is ready.");
  const [accountState, setAccountState] = useState<"idle" | "loading" | "ready" | "offline" | "signed-out">("idle");
  const [runOverride, setRunOverride] = useState<Row | null>(null);
  const [runMutationState, setRunMutationState] = useState<"idle" | "starting" | "polling" | "cancelling">("idle");
  const runRequestKey = useRef("");

  useEffect(() => {
    const restore = window.setTimeout(() => {
      try {
        const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null") as unknown;
        if (isRecord(parsed) && isRecord(parsed.states) && isRecord(parsed.policy) && isRecord(parsed.checkpoint)) {
          setLocalState(parsed as unknown as LocalAttentionState);
        }
      } catch {
        setStatusMessage("Stored local review state was invalid and was reset safely.");
      }
    }, 0);
    return () => window.clearTimeout(restore);
  }, []);

  const sourceItems = useMemo(() => records(data.all_items).filter((row) => row.material === true), [data]);
  const reviewItems = useMemo(
    () => sourceItems.map((row) => overlayLocalReview(row, reviewScope === "local" ? localState.states : {})),
    [sourceItems, reviewScope, localState.states],
  );
  const policy = reviewScope === "local" ? localState.policy : policyFromData(data);
  const checkpoint = reviewScope === "local" ? localState.checkpoint : checkpointFromData(data);
  const visibleItems = useMemo(() => {
    const minimum = SEVERITY_SCORE[policy.minimum_severity] ?? 10;
    return reviewItems
      .filter((row) => SEVERITY_SCORE[text(row.severity, "info")] >= minimum)
      .filter((row) => policy.included_change_kinds.includes(text(row.change_kind)))
      .filter((row) => policy.source_health_handling !== "hide" || !isSourceHealth(row))
      .filter((row) => severity === "all" || text(row.severity) === severity)
      .filter((row) => kind === "all" || text(row.change_kind) === kind)
      .filter((row) => source === "all" || rowSources(row).some((item) => text(item.provider) === source))
      .filter((row) => region === "all" || text(record(row.subject).region) === region)
      .filter((row) => reviewMatches(text(row.review_state, "new"), reviewFilter))
      .sort((left, right) => rankScore(right, policy) - rankScore(left, policy));
  }, [reviewItems, policy, severity, kind, source, region, reviewFilter]);

  const selected = visibleItems.find((row) => text(row.fingerprint) === selectedFingerprint) || visibleItems[0];
  const sourceOptions = unique(reviewItems.flatMap(rowSources).map((row) => text(row.provider)).filter(Boolean));
  const regionOptions = unique(reviewItems.map((row) => text(record(row.subject).region)).filter(Boolean));
  const kindOptions = unique(reviewItems.map((row) => text(row.change_kind)).filter(Boolean));
  const since = sinceCheckpoint(reviewItems, checkpoint.reviewed_through_at);
  const sourceGapCount = reviewItems.filter(isSourceHealth).length;
  const providerCalls = number(record(data.summary).provider_call_count ?? data.provider_call_count);
  const modeLabel = runtimeMode === "fixture" ? "fixture evidence" : "saved cache";
  const observationContext = record(data.observation_run);
  const latestRun = record(observationContext.latest_run);
  const activeRun = record(observationContext.active_run);
  const displayedRun = runOverride || (text(activeRun.run_id) ? activeRun : latestRun);

  function persistLocal(next: LocalAttentionState) {
    setLocalState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      setStatusMessage("Local review changed for this tab, but browser persistence is unavailable.");
    }
  }

  function updateUrl(key: string, value: string) {
    const params = new URLSearchParams(window.location.search);
    params.set("view", "attention-desk");
    params.set("mode", runtimeMode === "fixture" ? "fixture" : "cache");
    if (value === "all" || value === "needs-review") params.delete(key);
    else params.set(key, value);
    router.replace(`/?${params.toString()}`, { scroll: false });
  }

  function setFilter(key: string, value: string) {
    if (key === "attentionSeverity") setSeverity(value);
    if (key === "attentionKind") setKind(value);
    if (key === "attentionSource") setSource(value);
    if (key === "attentionRegion") setRegion(value);
    if (key === "review") setReviewFilter(value);
    updateUrl(key, value);
  }

  async function loadAccountReview() {
    setAccountState("loading");
    setStatusMessage("Loading account-owned review state.");
    try {
      const response = await fetch(`/api/account/attention-desk?mode=${runtimeMode === "fixture" ? "fixture" : "cache"}`, {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (response.status === 401) {
        setAccountState("signed-out");
        setStatusMessage("Sign in from Account Research to use account review. Local review remains available.");
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json() as unknown;
      if (!isRecord(payload) || !isRecord(payload.data)) throw new Error("invalid account attention payload");
      setData(payload.data);
      setReviewScope("account");
      setAccountState("ready");
      setStatusMessage("Account review state loaded. No market-provider request was made.");
    } catch {
      setAccountState("offline");
      setStatusMessage("Account runtime is offline. Saved source evidence and local review remain available.");
    }
  }

  async function mutateReview(row: Row, action: "review" | "acknowledge" | "snooze" | "undo-snooze") {
    const fingerprint = text(row.fingerprint);
    const currentVersion = number(row.review_version ?? row.version);
    if (reviewScope === "local") {
      const current = localState.states[fingerprint] || {
        review_state: "new" as const,
        prior_state: "new" as const,
        snoozed_until: null,
        version: 0,
      };
      const next = localReviewMutation(current, action);
      persistLocal({ ...localState, states: { ...localState.states, [fingerprint]: next } });
      setStatusMessage(localActionMessage(action));
      return;
    }
    try {
      const response = await fetch(`/api/account/attention-desk/items/${encodeURIComponent(fingerprint)}`, {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfCookie() },
        body: JSON.stringify({
          action,
          expected_version: currentVersion,
          ...(action === "snooze" ? { snoozed_until: fourHoursFromNow() } : {}),
        }),
      });
      if (response.status === 409) {
        setStatusMessage("Review version changed in another session. Reload account review before retrying.");
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json() as unknown;
      const saved = isRecord(payload) ? record(payload.data) : {};
      setData((current) => ({
        ...current,
        all_items: records(current.all_items).map((item) => text(item.fingerprint) === fingerprint
          ? { ...item, ...saved, review_version: saved.version }
          : item),
      }));
      setStatusMessage(`${localActionMessage(action)} Account state saved without a market-provider request.`);
    } catch {
      setAccountState("offline");
      setStatusMessage("Account review could not be saved. Source evidence remains visible; switch to local review to continue.");
    }
  }

  function updateLocalPolicy(field: string, value: string | string[]) {
    const nextPolicy = { ...localState.policy, [field]: value, version: localState.policy.version + 1 };
    persistLocal({ ...localState, policy: nextPolicy });
    setStatusMessage("Local in-app attention policy updated. No notification was sent.");
  }

  async function saveAccountPolicy() {
    const current = policyFromData(data);
    try {
      const response = await fetch("/api/account/attention-desk/policy", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfCookie() },
        body: JSON.stringify({ ...current, expected_version: current.version }),
      });
      if (response.status === 409) {
        setStatusMessage("Policy version conflict. Reload account review before saving again.");
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setStatusMessage("Account policy saved. External delivery remains unavailable.");
      await loadAccountReview();
    } catch {
      setStatusMessage("Account policy is unavailable. Local policy remains usable.");
    }
  }

  async function markCheckpoint() {
    const timestamp = new Date().toISOString();
    if (reviewScope === "local") {
      persistLocal({
        ...localState,
        checkpoint: { reviewed_through_at: timestamp, version: localState.checkpoint.version + 1 },
      });
      setStatusMessage("Local review checkpoint advanced. Provider observation clocks were not changed.");
      return;
    }
    try {
      const response = await fetch("/api/account/attention-desk/checkpoint", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfCookie() },
        body: JSON.stringify({ expected_version: number(record(data.checkpoint).version) }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setStatusMessage("Account review checkpoint advanced without changing provider clocks.");
      await loadAccountReview();
    } catch {
      setStatusMessage("Account checkpoint was not saved. Local evidence remains available.");
    }
  }

  async function pollObservationRun(runId: string): Promise<Row> {
    setRunMutationState("polling");
    for (let attempt = 0; attempt < 80; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 750));
      const response = await fetch(`/api/account/observation-runs/${encodeURIComponent(runId)}`, {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json() as unknown;
      const run = isRecord(payload) ? record(payload.data) : {};
      if (!text(run.run_id)) throw new Error("invalid observation run payload");
      setRunOverride(run);
      const status = text(run.status);
      setStatusMessage(`Saved Watchlist observation is ${status}. Status checks make no market-provider requests.`);
      if (OBSERVATION_TERMINAL_STATES.has(status)) return run;
    }
    throw new Error("observation polling timeout");
  }

  async function refreshObservation() {
    const action = record(observationContext.refresh_action);
    const watchlist = record(observationContext.available_watchlist);
    if (runtimeMode === "fixture") {
      setStatusMessage("Fixture evidence cannot contact providers. Switch to saved cache and account review.");
      return;
    }
    if (reviewScope !== "account" || accountState !== "ready") {
      setStatusMessage("Load account review before refreshing an account-owned saved Watchlist.");
      return;
    }
    if (action.enabled !== true || !text(watchlist.resource_id)) {
      setStatusMessage(text(action.reason, "No saved Watchlist is eligible for an observation run."));
      return;
    }
    if (!runRequestKey.current) {
      runRequestKey.current = `phase6n:${Date.now()}:${crypto.randomUUID()}`;
    }
    setRunMutationState("starting");
    setStatusMessage("Submitting one bounded saved-Watchlist observation run.");
    try {
      const response = await fetch("/api/account/observation-runs", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfCookie() },
        body: JSON.stringify({
          watchlist_id: watchlist.resource_id,
          idempotency_key: runRequestKey.current,
          interval: "1d",
          range: "3mo",
          max_symbols: 5,
          session_policy: "market-aware",
        }),
      });
      if (response.status === 409) {
        setStatusMessage("Another observation run is active or this request key conflicts. Reload account review before retrying.");
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json() as unknown;
      let run = isRecord(payload) ? record(payload.data) : {};
      if (!text(run.run_id)) throw new Error("invalid observation run payload");
      setRunOverride(run);
      if (!OBSERVATION_TERMINAL_STATES.has(text(run.status))) {
        run = await pollObservationRun(text(run.run_id));
      }
      runRequestKey.current = "";
      setStatusMessage(`Observation run ${text(run.status)}. Reloading committed changes without another provider call.`);
      await loadAccountReview();
    } catch {
      setStatusMessage("Observation runtime is offline or timed out. Last completed evidence remains available; retry keeps the same idempotency key.");
    } finally {
      setRunMutationState("idle");
    }
  }

  async function cancelObservation() {
    const runId = text(displayedRun.run_id);
    if (!runId || !["queued", "running"].includes(text(displayedRun.status))) return;
    setRunMutationState("cancelling");
    try {
      const response = await fetch(`/api/account/observation-runs/${encodeURIComponent(runId)}/cancel`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfCookie() },
        body: "{}",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json() as unknown;
      const run = isRecord(payload) ? record(payload.data) : {};
      setRunOverride(run);
      setStatusMessage(text(run.status) === "cancelled" ? "Observation run cancelled before commit." : "Cancellation requested; the current bounded provider operation will finish safely.");
    } catch {
      setStatusMessage("Cancellation could not be confirmed. Reload account review to inspect the authoritative run state.");
    } finally {
      setRunMutationState("idle");
    }
  }

  return (
    <section
      className="attention-desk"
      data-phase6m-attention-desk="true"
      data-attention-visible-count={visibleItems.length}
      data-attention-provider-calls={providerCalls}
      data-attention-review-scope={reviewScope}
      data-attention-account-state={accountState}
      aria-labelledby="attention-desk-title"
    >
      <header className="attention-command-header">
        <div>
          <span className="eyebrow">Daily source review / {modeLabel}</span>
          <h2 id="attention-desk-title">What materially changed since your last review</h2>
          <p>{visibleItems.length} prioritized rows from stored market, catalyst, news, brief, provider, and map evidence.</p>
        </div>
        <div className="attention-header-actions">
          <span className={`attention-scope-state ${reviewScope}`}><Gauge size={14} /> {reviewScope} review</span>
          {reviewScope === "local" ? (
            <button type="button" onClick={loadAccountReview} disabled={accountState === "loading"} title="Load current-session account review state">
              <RefreshCw size={15} /> {accountState === "loading" ? "Loading account" : "Use account review"}
            </button>
          ) : (
            <button type="button" onClick={() => { setReviewScope("local"); setStatusMessage("Returned to browser-local review state."); }}>
              <RotateCcw size={15} /> Use local review
            </button>
          )}
        </div>
      </header>

      <div className="attention-truth-line">
        <span><ShieldAlert size={14} /> Source truth retained</span>
        <span><Clock3 size={14} /> Observation and retrieval clocks stay separate</span>
        <span><Check size={14} /> No market-provider request</span>
        <span>{providerCalls} calls</span>
      </div>

      <ObservationRunStrip
        context={observationContext}
        run={displayedRun}
        runtimeMode={runtimeMode}
        reviewScope={reviewScope}
        accountState={accountState}
        mutationState={runMutationState}
        onRefresh={refreshObservation}
        onCancel={cancelObservation}
      />

      <section className="attention-digest-band" aria-labelledby="attention-digest-title">
        <div className="attention-digest-copy">
          <span className="eyebrow">Bounded daily digest</span>
          <h3 id="attention-digest-title">{digestHeadline(visibleItems, sourceOptions.length)}</h3>
          <p>{sourceGapCount ? `${sourceGapCount} source-health gaps are kept beside market evidence.` : "No source degradation row is currently promoted."}</p>
        </div>
        <div className="attention-since-strip" aria-label="Since last review">
          <strong>Since last review</strong>
          <span><b>{since.newCount}</b> new</span>
          <span><b>{since.materialCount}</b> material</span>
          <span><b>{since.changedCount}</b> changed</span>
          <span><b>{since.resolvedCount}</b> resolved</span>
          <button type="button" onClick={markCheckpoint}><CheckCheck size={14} /> Mark review checkpoint</button>
        </div>
      </section>

      <nav className="attention-filter-bar" aria-label="Attention filters">
        <span><Filter size={14} /> Filter</span>
        <label>Severity<select aria-label="Attention severity" value={severity} onChange={(event) => setFilter("attentionSeverity", event.target.value)}><option value="all">All severity</option>{["critical", "high", "material", "info"].map((value) => <option value={value} key={value}>{title(value)}</option>)}</select></label>
        <label>Change kind<select aria-label="Attention change kind" value={kind} onChange={(event) => setFilter("attentionKind", event.target.value)}><option value="all">All kinds</option>{kindOptions.map((value) => <option value={value} key={value}>{title(value)}</option>)}</select></label>
        <label>Source<select aria-label="Attention source" value={source} onChange={(event) => setFilter("attentionSource", event.target.value)}><option value="all">All sources</option>{sourceOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
        <label>Region<select aria-label="Attention region" value={region} onChange={(event) => setFilter("attentionRegion", event.target.value)}><option value="all">All regions</option>{regionOptions.map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
        <div className="attention-review-segments" aria-label="Review state">
          {["needs-review", "all", "reviewed", "snoozed", "acknowledged"].map((value) => <button type="button" key={value} className={reviewFilter === value ? "active" : ""} onClick={() => setFilter("review", value)}>{title(value)}</button>)}
        </div>
      </nav>

      <div className="attention-workspace">
        <section className="attention-queue" aria-labelledby="attention-queue-title">
          <div className="section-heading">
            <div><span className="eyebrow">Prioritized queue</span><h3 id="attention-queue-title">Material review</h3></div>
            <span>{visibleItems.length} / {reviewItems.length}</span>
          </div>
          {visibleItems.length ? (
            <div className="attention-queue-list">
              {visibleItems.map((row) => (
                <AttentionRow
                  key={text(row.fingerprint)}
                  row={row}
                  selected={text(row.fingerprint) === text(selected?.fingerprint)}
                  onSelect={() => setSelectedFingerprint(text(row.fingerprint))}
                  onReview={(action) => mutateReview(row, action)}
                />
              ))}
            </div>
          ) : (
            <div className="attention-empty" role="status">
              <CheckCheck size={22} />
              <strong>No material change matches this review state.</strong>
              <p>Source evidence is retained. Relax a filter or inspect acknowledged history; a retrieval-clock-only refresh is not promoted.</p>
            </div>
          )}
        </section>

        <aside className="attention-source-rail" aria-labelledby="attention-source-title">
          <div className="section-heading"><div><span className="eyebrow">Exact evidence</span><h3 id="attention-source-title">Source truth</h3></div><ShieldAlert size={16} /></div>
          {selected ? <SourceTruth row={selected} /> : <p className="panel-note">Select a material row to inspect exact origin, clocks, caveats, and data gaps.</p>}
          <AttentionPolicy
            policy={policy}
            kinds={kindOptions}
            scope={reviewScope}
            onChange={reviewScope === "local" ? updateLocalPolicy : (field, value) => setData((current) => ({ ...current, policy: { ...record(current.policy), [field]: value } }))}
            onSave={saveAccountPolicy}
          />
        </aside>
      </div>

      {(accountState === "offline" || accountState === "signed-out") ? (
        <div className="attention-recovery" role="status"><ShieldAlert size={15} /><strong>{accountState === "offline" ? "Account runtime offline" : "Account sign-in required"}</strong><span>Local review and saved source evidence remain usable.</span></div>
      ) : null}
      <div className="attention-status" aria-live="polite">{statusMessage}</div>
      <footer className="attention-footer">Research information only. Review state changes do not send email, SMS, push, webhook, broker, or autonomous actions.</footer>
    </section>
  );
}

function ObservationRunStrip({
  context,
  run,
  runtimeMode,
  reviewScope,
  accountState,
  mutationState,
  onRefresh,
  onCancel,
}: {
  context: Row;
  run: Row;
  runtimeMode: RuntimeMode;
  reviewScope: ReviewScope;
  accountState: string;
  mutationState: string;
  onRefresh: () => void;
  onCancel: () => void;
}) {
  const action = record(context.refresh_action);
  const watchlist = record(context.available_watchlist);
  const session = record(run.session);
  const budget = record(run.provider_budget);
  const status = text(run.status, "not-run");
  const active = ["queued", "running"].includes(status);
  const requested = number(run.requested_count);
  const completed = number(run.completed_count);
  const progress = requested ? Math.min(100, Math.round((completed / requested) * 100)) : active ? 8 : 0;
  const enabled = runtimeMode !== "fixture" && reviewScope === "account" && accountState === "ready" && action.enabled === true && !active && mutationState === "idle";
  const calls = number(run.provider_call_count ?? budget.actual_calls);
  const maximumCalls = number(run.provider_call_budget ?? budget.maximum_calls) || 16;
  const lkg = number(run.lkg_reused_count);
  const material = number(context.material_change_count);
  const stateVocabulary = OBSERVATION_RUN_STATES.join(" / ");
  return (
    <section
      className={`attention-observation-run state-${status}`}
      data-phase6n-observation-run="true"
      data-observation-run-status={status}
      data-observation-run-states={stateVocabulary}
      aria-labelledby="attention-observation-title"
    >
      <header>
        <div>
          <span className="eyebrow">Saved Watchlist observation</span>
          <h3 id="attention-observation-title">{text(run.watchlist_name || watchlist.name, "No saved run yet")}</h3>
        </div>
        <span className={`attention-run-status ${status}`}>{status}</span>
      </header>
      <div className="attention-run-metrics">
        <div><span>Last completed</span><strong>{shortClock(run.completed_at)}</strong><small>{text(run.run_id, "not run")}</small></div>
        <div><span>Session policy</span><strong>{text(session.policy, runtimeMode === "fixture" ? "fixture" : "not evaluated")}</strong><small>{text(session.calendar_status, "no session evidence")}</small></div>
        <div><span>Provider budget</span><strong>{calls} / {maximumCalls}</strong><small>{number(budget.cache_hits)} cache / {lkg} LKG</small></div>
        <div><span>Material changes</span><strong>{material}</strong><small>{completed} / {requested || number(watchlist.item_count)} symbols committed</small></div>
      </div>
      {active ? <div className="attention-run-progress" aria-label={`Observation run ${status}`}><span style={{ width: `${progress}%` }} /><small>{status} / {progress}% committed</small></div> : null}
      <div className="attention-run-actions">
        <button type="button" onClick={onRefresh} disabled={!enabled} title={enabled ? "Start one bounded source-backed observation run" : text(action.reason, "Account saved Watchlist required")}>
          <RefreshCw size={14} /> {mutationState === "starting" ? "Starting run" : "Refresh saved Watchlist"}
        </button>
        {active ? <button type="button" onClick={onCancel} disabled={mutationState === "cancelling"} title="Request safe cancellation before snapshot commit"><Square size={13} /> Cancel run</button> : null}
        <span>{runtimeMode === "fixture" ? "Fixture never contacts providers" : text(action.reason, "Saved evidence remains available")}</span>
      </div>
      {status === "partial" || status === "failed" || status === "cancelled" ? <p className="attention-run-recovery"><ShieldAlert size={14} /> {status === "partial" ? `${lkg} last-known-good rows retained; inspect source gaps before review.` : status === "cancelled" ? "No incomplete snapshot set was promoted." : "The last completed snapshot remains authoritative; no automatic retry was started."}</p> : null}
    </section>
  );
}

function AttentionRow({ row, selected, onSelect, onReview }: { row: Row; selected: boolean; onSelect: () => void; onReview: (action: "review" | "acknowledge" | "snooze" | "undo-snooze") => void }) {
  const subject = record(row.subject);
  const state = text(row.review_state, "new");
  const drilldowns = record(row.drilldowns);
  const primary = primaryDrilldown(drilldowns);
  return (
    <article className={`attention-queue-row ${selected ? "selected" : ""}`} data-attention-severity={text(row.severity)} data-attention-review-state={state}>
      <button type="button" className="attention-row-select" onClick={onSelect} aria-label={`Inspect ${text(row.title)}`}>
        <span className={`attention-severity ${text(row.severity)}`}>{text(row.severity)}</span>
        <span className="attention-row-identity"><strong>{text(subject.symbol || subject.region || subject.label, "Source")}</strong><small>{text(row.change_kind)} / {state}</small></span>
        <span className="attention-rank">{number(record(row.rank).score)}</span>
      </button>
      <h4>{text(row.title)}</h4>
      <p>{text(row.summary)}</p>
      <div className="attention-row-clocks"><span>Observed {shortClock(row.observed_at)}</span><span>Retrieved {shortClock(row.retrieved_at)}</span><span>{row.snooze_expired === true ? "Snooze expired" : text(row.source_status)}</span></div>
      <small className="attention-why">{text(row.why_it_matters)}</small>
      <div className="attention-row-actions">
        {primary ? <Link prefetch={false} href={ensureOrigin(primary)}><ExternalLink size={14} /> Open exact evidence</Link> : null}
        {state === "new" ? <button type="button" onClick={() => onReview("review")}><Check size={14} /> Review</button> : null}
        {state !== "acknowledged" ? <button type="button" onClick={() => onReview("acknowledge")}><CheckCheck size={14} /> Acknowledge</button> : null}
        {state === "snoozed" ? <button type="button" onClick={() => onReview("undo-snooze")}><RotateCcw size={14} /> Undo snooze</button> : state !== "acknowledged" ? <button type="button" onClick={() => onReview("snooze")}><BellOff size={14} /> Snooze 4h</button> : null}
      </div>
    </article>
  );
}

function SourceTruth({ row }: { row: Row }) {
  const sources = rowSources(row);
  const drilldowns = record(row.drilldowns);
  return (
    <div className="attention-source-detail">
      <h4>{text(row.title)}</h4>
      <div className="attention-source-metrics"><span><b>{text(row.source_status)}</b> state</span><span><b>{percent(row.confidence)}</b> confidence</span><span><b>{sources.length}</b> sources</span></div>
      <dl>
        <div><dt>Observed</dt><dd>{longClock(row.observed_at)}</dd></div>
        <div><dt>Retrieved</dt><dd>{longClock(row.retrieved_at)}</dd></div>
        <div><dt>Caveat</dt><dd>{text(row.caveat, "No additional caveat supplied.")}</dd></div>
        <div><dt>Data gap</dt><dd>{text(row.data_gap, "No explicit gap supplied.")}</dd></div>
      </dl>
      <div className="attention-source-list">
        {sources.map((source, index) => (
          <div key={`${text(source.provider)}-${text(source.source_url)}-${index}`}>
            <strong>{text(source.provider, "unknown")}</strong>
            <span>{text(source.source_status)} / {shortClock(source.retrieved_at)}</span>
            {safeHttp(source.source_url) ? <a href={text(source.source_url)} target="_blank" rel="noreferrer"><ExternalLink size={13} /> Original source</a> : <small>No public source URL</small>}
          </div>
        ))}
      </div>
      <nav className="attention-drilldown-grid" aria-label="Evidence destinations">
        {text(drilldowns.analyst) ? <Link prefetch={false} href={ensureOrigin(text(drilldowns.analyst))}><Gauge size={14} /> Analyst</Link> : null}
        {text(drilldowns.news) ? <Link prefetch={false} href={ensureOrigin(text(drilldowns.news))}><Newspaper size={14} /> News</Link> : null}
        {text(drilldowns.brief) ? <Link prefetch={false} href={ensureOrigin(text(drilldowns.brief))}><FileText size={14} /> Brief</Link> : null}
        {text(drilldowns.map) ? <Link prefetch={false} href={ensureOrigin(text(drilldowns.map))}><MapPinned size={14} /> Map</Link> : null}
      </nav>
      <div className="attention-rank-factors"><span>Rank factors</span>{strings(record(row.rank).factors).map((factor) => <code key={factor}>{factor}</code>)}</div>
    </div>
  );
}

function AttentionPolicy({ policy, kinds, scope, onChange, onSave }: { policy: LocalAttentionState["policy"]; kinds: string[]; scope: ReviewScope; onChange: (field: string, value: string | string[]) => void; onSave: () => void }) {
  return (
    <section className="attention-policy" aria-labelledby="attention-policy-title">
      <div className="section-heading"><div><span className="eyebrow">In-app only</span><h4 id="attention-policy-title"><SlidersHorizontal size={14} /> Attention policy</h4></div></div>
      <label>Minimum severity<select aria-label="Minimum severity" value={policy.minimum_severity} onChange={(event) => onChange("minimum_severity", event.target.value)}>{["info", "material", "high", "critical"].map((value) => <option value={value} key={value}>{title(value)}</option>)}</select></label>
      <label>Source health<select aria-label="Source health" value={policy.source_health_handling} onChange={(event) => onChange("source_health_handling", event.target.value)}><option value="include">Include</option><option value="deprioritize">Deprioritize</option><option value="hide">Hide</option></select></label>
      <fieldset><legend>Included change kinds</legend>{kinds.map((value) => <label key={value}><input type="checkbox" checked={policy.included_change_kinds.includes(value)} onChange={(event) => onChange("included_change_kinds", event.target.checked ? unique([...policy.included_change_kinds, value]) : policy.included_change_kinds.filter((item) => item !== value))} />{title(value)}</label>)}</fieldset>
      {scope === "account" ? <button type="button" onClick={onSave}><Check size={14} /> Save account policy</button> : <small>Saved only in this browser. No external notification.</small>}
    </section>
  );
}

function overlayLocalReview(row: Row, states: Record<string, LocalReviewRow>): Row {
  const state = states[text(row.fingerprint)];
  if (!state) return row;
  const expired = state.review_state === "snoozed" && Boolean(state.snoozed_until && new Date(state.snoozed_until).getTime() <= Date.now());
  return {
    ...row,
    review_state: expired ? state.prior_state : state.review_state,
    review_version: state.version,
    snoozed_until: state.snoozed_until,
    snooze_expired: expired,
    reviewed_at: state.reviewed_at,
    acknowledged_at: state.acknowledged_at,
  };
}

function localReviewMutation(current: LocalReviewRow, action: "review" | "acknowledge" | "snooze" | "undo-snooze"): LocalReviewRow {
  const now = new Date().toISOString();
  if (action === "review") return { ...current, review_state: "reviewed", prior_state: "reviewed", reviewed_at: now, snoozed_until: null, version: current.version + 1 };
  if (action === "acknowledge") return { ...current, review_state: "acknowledged", acknowledged_at: now, reviewed_at: current.reviewed_at || now, snoozed_until: null, version: current.version + 1 };
  if (action === "snooze") return { ...current, prior_state: current.review_state === "reviewed" ? "reviewed" : "new", review_state: "snoozed", snoozed_until: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(), version: current.version + 1 };
  return { ...current, review_state: current.prior_state, snoozed_until: null, version: current.version + 1 };
}

function policyFromData(data: Row): LocalAttentionState["policy"] {
  const policy = record(data.policy);
  return {
    minimum_severity: text(policy.minimum_severity, "info"),
    included_change_kinds: strings(policy.included_change_kinds).length ? strings(policy.included_change_kinds) : DEFAULT_LOCAL_STATE.policy.included_change_kinds,
    source_health_handling: text(policy.source_health_handling, "include"),
    version: number(policy.version),
  };
}

function checkpointFromData(data: Row): LocalAttentionState["checkpoint"] {
  const checkpoint = record(data.checkpoint);
  return { reviewed_through_at: text(checkpoint.reviewed_through_at) || null, version: number(checkpoint.version) };
}

function sinceCheckpoint(rows: Row[], checkpoint: string | null) {
  const threshold = checkpoint ? new Date(checkpoint).getTime() : 0;
  const since = rows.filter((row) => new Date(text(row.observed_at || row.retrieved_at, "1970-01-01T00:00:00Z")).getTime() > threshold);
  return {
    newCount: since.filter((row) => text(row.review_state, "new") === "new").length,
    materialCount: since.length,
    changedCount: since.filter((row) => text(row.change_kind) !== "resolved").length,
    resolvedCount: since.filter((row) => text(row.change_kind) === "resolved").length,
  };
}

function rankScore(row: Row, policy: LocalAttentionState["policy"]): number {
  const base = number(record(row.rank).score);
  return base + (policy.source_health_handling === "deprioritize" && isSourceHealth(row) ? -15 : 0);
}

function rowSources(row: Row): Row[] { return records(row.source_register); }
function isSourceHealth(row: Row): boolean { return ["source-degradation", "stale-evidence"].includes(text(row.change_kind)); }
function reviewMatches(state: string, filter: string): boolean { return filter === "all" || (filter === "needs-review" ? ["new", "reviewed"].includes(state) : state === filter); }
function digestHeadline(rows: Row[], sourceCount: number): string { return rows.length ? `${rows.length} material changes across ${sourceCount} named sources` : "No material change is waiting in this view"; }
function localActionMessage(action: string): string { return action === "review" ? "Marked reviewed." : action === "acknowledge" ? "Acknowledged." : action === "snooze" ? "Snoozed for four hours." : "Snooze undone."; }
function primaryDrilldown(value: Row): string { return text(value.analyst || value.news || value.brief || value.map || value.watchlist); }
function ensureOrigin(href: string): string {
  if (!href.startsWith("/?")) return href;
  const url = new URL(href, "http://local.test");
  if (!url.searchParams.has("originView")) url.searchParams.set("originView", "attention-desk");
  if (!url.searchParams.has("originState")) url.searchParams.set("originState", "view=attention-desk&review=needs-review");
  return `/?${url.searchParams.toString()}`;
}
function csrfCookie(): string { return decodeURIComponent(document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("gt_csrf="))?.split("=").slice(1).join("=") || ""); }
function fourHoursFromNow(): string { return new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(); }
function safeHttp(value: unknown): boolean { try { const url = new URL(text(value)); return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password; } catch { return false; } }
function percent(value: unknown): string { const numeric = Number(value); return Number.isFinite(numeric) ? `${Math.round(numeric * 100)}%` : "unknown"; }
function shortClock(value: unknown): string { const raw = text(value); if (!raw) return "unknown"; const date = new Date(raw); return Number.isNaN(date.getTime()) ? raw : date.toISOString().slice(5, 16).replace("T", " ") + "Z"; }
function longClock(value: unknown): string { const raw = text(value); if (!raw) return "not supplied"; const date = new Date(raw); return Number.isNaN(date.getTime()) ? raw : date.toISOString().replace(".000", ""); }
function title(value: string): string { return value.split("-").map((part) => part ? part[0].toUpperCase() + part.slice(1) : part).join(" "); }
function unique(values: string[]): string[] { return [...new Set(values)].sort(); }
function number(value: unknown): number { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : 0; }
function text(value: unknown, fallback = ""): string { return typeof value === "string" && value.trim() ? value.trim() : value === 0 ? "0" : fallback; }
function record(value: unknown): Row { return isRecord(value) ? value : {}; }
function records(value: unknown): Row[] { return Array.isArray(value) ? value.filter(isRecord) : []; }
function strings(value: unknown): string[] { return Array.isArray(value) ? value.map(String).filter(Boolean) : []; }
function isRecord(value: unknown): value is Row { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
