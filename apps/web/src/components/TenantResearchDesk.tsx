"use client";

import {
  BellRing,
  Check,
  ChevronDown,
  ChevronUp,
  CircleUserRound,
  Cloud,
  CloudOff,
  Download,
  Eye,
  GitCompareArrows,
  Inbox,
  LoaderCircle,
  LogIn,
  KeyRound,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { type ChangeEvent, useState } from "react";

type Row = Record<string, unknown>;
type LoadState = "idle" | "loading" | "anonymous" | "ready" | "offline";
const ACCOUNT_API_BASE = "/api/account";
const ACCOUNT_RESEARCH_DESK_API = "/api/account/research-desk";

function record(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}

function records(value: unknown): Row[] {
  return Array.isArray(value) ? value.filter((row): row is Row => Boolean(row) && typeof row === "object" && !Array.isArray(row)) : [];
}

function text(value: unknown, fallback = "") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const prefix = `${encodeURIComponent(name)}=`;
  const row = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(prefix));
  return row ? decodeURIComponent(row.slice(prefix.length)) : "";
}

async function accountRequest(path: string, init: RequestInit = {}): Promise<Row> {
  const method = (init.method || "GET").toUpperCase();
  const target = path === "research-desk"
    ? ACCOUNT_RESEARCH_DESK_API
    : `${ACCOUNT_API_BASE}/${path.replace(/^\/+/, "")}`;
  const response = await fetch(target, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRF-Token": readCookie("gt_csrf") } : {}),
      ...(init.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({})) as Row;
  if (!response.ok) {
    const detail = text(payload.detail || payload.error, `account-http-${response.status}`);
    throw new Error(detail);
  }
  return payload;
}

export function TenantResearchDesk({ sourceListId }: { sourceListId: string }) {
  const [expanded, setExpanded] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("Account research is idle. Local research remains private.");
  const [desk, setDesk] = useState<Row>({});
  const [preview, setPreview] = useState<Row>({});
  const [selected, setSelected] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [inboxFilter, setInboxFilter] = useState("attention");
  const [localSignInAvailable, setLocalSignInAvailable] = useState(false);
  const [hostedSignInAvailable, setHostedSignInAvailable] = useState(false);
  const [identityProvider, setIdentityProvider] = useState("none");
  const [accountCanWrite, setAccountCanWrite] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [continuity, setContinuity] = useState<Row>({});
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [sync, setSync] = useState<Row>({});
  const [syncPlan, setSyncPlan] = useState<Row>({});
  const [syncConsent, setSyncConsent] = useState(false);

  const summary = record(desk.summary);
  const watchlists = records(desk.watchlists);
  const rules = records(desk.rules);
  const inbox = records(desk.inbox);
  const attention = record(desk.attention);
  const attentionItems = records(attention.items);
  const filteredInbox = inboxFilter === "attention"
    ? attentionItems
    : inbox.filter((item) => inboxFilter === "all" || text(item.state) === inboxFilter);
  const candidates = records(preview.candidates);
  const syncQueue = records(sync.queue);
  const localSyncSnapshot = record(syncPlan.local);
  const continuityRepository = record(continuity.repository);
  const continuityState = text(continuity.state, identityProvider === "supabase" ? "checking" : "local-only");
  const hostedIdentity = identityProvider === "supabase";

  async function refreshDesk(includePreview = false) {
    const deskEnvelope = await accountRequest("research-desk");
    const nextDesk = record(deskEnvelope.data);
    setDesk(nextDesk);
    setSync(record(nextDesk.sync));
    const continuityEnvelope = await accountRequest("continuity");
    setContinuity(record(continuityEnvelope.data));
    if (includePreview) {
      const query = new URLSearchParams({ source_list_id: sourceListId, limit: "25" });
      const previewEnvelope = await accountRequest(`research-desk/imports/preview?${query.toString()}`);
      const nextPreview = record(previewEnvelope.data);
      setPreview(nextPreview);
      setSelected(records(nextPreview.candidates).map((row) => text(row.candidate_id)).filter(Boolean));
    }
  }

  async function openDesk() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (loadState !== "idle" && loadState !== "offline") return;
    setLoadState("loading");
    setMessage("Checking the process-local account boundary...");
    try {
      const sessionEnvelope = await accountRequest("session");
      const account = record(sessionEnvelope.data);
      const identity = record(account.identity);
      const runtimeTruth = record(account.runtime_truth);
      setLocalSignInAvailable(Boolean(runtimeTruth.local_test_sign_in_available));
      setHostedSignInAvailable(Boolean(runtimeTruth.hosted_sign_in_available));
      setAccountCanWrite(runtimeTruth.account_write !== false);
      setIdentityProvider(text(identity.identity_provider, "none"));
      if (!identity.authenticated) {
        setLoadState("anonymous");
        setMessage("Sign in only when you want an account-owned copy. Nothing is uploaded automatically.");
        return;
      }
      await refreshDesk(true);
      setLoadState("ready");
      setMessage("Account research loaded from the current session tenant.");
    } catch (error) {
      setLoadState("offline");
      setMessage(error instanceof Error ? error.message : "Account research is offline.");
    }
  }

  async function signIn(alias: "analyst-a" | "analyst-b") {
    setBusy(`signin-${alias}`);
    setMessage("Creating an explicitly local test session...");
    try {
      await accountRequest("local-session", {
        method: "POST",
        body: JSON.stringify({ alias, return_to: window.location.pathname + window.location.search }),
      });
      await refreshDesk(true);
      setIdentityProvider("process-local-test");
      setLoadState("ready");
      setMessage("Local QA identity active.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Local sign-in failed.");
    } finally {
      setBusy("");
    }
  }

  async function signInHosted() {
    if (!email.trim() || password.length < 8) {
      setMessage("Enter the hosted account email and password.");
      return;
    }
    setBusy("hosted-signin");
    setMessage("Verifying hosted account...");
    try {
      const envelope = await accountRequest("hosted-session", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          password,
          return_to: window.location.pathname + window.location.search,
        }),
      });
      const account = record(envelope.data);
      const identity = record(account.identity);
      setAccountCanWrite(record(account.runtime_truth).account_write !== false);
      setPassword("");
      setIdentityProvider(text(identity.identity_provider, "supabase"));
      await refreshDesk(true);
      setLoadState("ready");
      setMessage(`Hosted workspace ${text(record(account.restore).status, "restored")}.`);
    } catch (error) {
      setPassword("");
      setMessage(error instanceof Error ? error.message : "Hosted sign-in failed.");
    } finally {
      setBusy("");
    }
  }

  async function replayContinuity() {
    setBusy("continuity-replay");
    try {
      const envelope = await accountRequest("continuity/replay", { method: "POST", body: "{}" });
      setContinuity(record(envelope.data));
      await refreshDesk(false);
      setMessage(`Account recovery: ${text(record(envelope.data).status, "complete")}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Account recovery failed.");
    } finally {
      setBusy("");
    }
  }

  async function resolveContinuity(strategy: "keep-local" | "use-hosted") {
    setBusy(`continuity-${strategy}`);
    try {
      const envelope = await accountRequest("continuity/resolve", {
        method: "POST",
        body: JSON.stringify({
          strategy,
          idempotency_key: `phase6p-${strategy}-${crypto.randomUUID()}`,
        }),
      });
      setContinuity(record(envelope.data));
      await refreshDesk(false);
      setMessage(strategy === "keep-local" ? "Local workspace promoted to hosted." : "Hosted workspace restored locally.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Conflict resolution failed.");
    } finally {
      setBusy("");
    }
  }

  async function exportContinuity() {
    setBusy("continuity-export");
    try {
      const envelope = await accountRequest("continuity/export");
      const blob = new Blob([JSON.stringify(envelope.data, null, 2)], { type: "application/json" });
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = "global-terminal-account-export.json";
      anchor.click();
      URL.revokeObjectURL(href);
      setMessage("Bounded account export prepared.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Account export failed.");
    } finally {
      setBusy("");
    }
  }

  async function importContinuity(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 512_000) {
      setMessage("Account backup exceeds the 512 KB bound.");
      return;
    }
    setBusy("continuity-import");
    try {
      const parsed = JSON.parse(await file.text()) as Row;
      const envelope = await accountRequest("continuity/import", {
        method: "POST",
        body: JSON.stringify({
          bundle: parsed,
          strategy: "merge",
          idempotency_key: `phase6p-backup-${crypto.randomUUID()}`,
        }),
      });
      setContinuity(record(envelope.data));
      await refreshDesk(false);
      setMessage("Account backup merged and reconciled.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Account backup import failed.");
    } finally {
      setBusy("");
    }
  }

  async function deleteHostedContinuity() {
    if (!deleteArmed) {
      setDeleteArmed(true);
      setMessage("Confirm hosted document deletion. Local state remains available.");
      return;
    }
    setBusy("continuity-delete");
    try {
      const idempotency = `phase6p-delete-${crypto.randomUUID()}`;
      const envelope = await accountRequest(`continuity?idempotency_key=${encodeURIComponent(idempotency)}`, { method: "DELETE" });
      setContinuity(record(envelope.data));
      setDeleteArmed(false);
      setMessage("Hosted document deleted. Local workspace retained.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Hosted deletion failed.");
    } finally {
      setBusy("");
    }
  }

  async function previewLocalImport() {
    setBusy("preview");
    try {
      await refreshDesk(true);
      setMessage("Preview refreshed with zero provider calls. Private notes are excluded.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Import preview failed.");
    } finally {
      setBusy("");
    }
  }

  async function confirmImport() {
    if (!consent || !selected.length) {
      setMessage("Select at least one row and provide explicit consent before import.");
      return;
    }
    setBusy("import");
    try {
      await accountRequest("research-desk/imports", {
        method: "POST",
        body: JSON.stringify({
          preview_id: preview.preview_id,
          candidate_ids: selected,
          consent: true,
          idempotency_key: `watchlist-${text(preview.preview_id)}-${selected.slice().sort().join("-")}`.slice(0, 128),
          expected_version: 0,
          destination_name: `${text(preview.source_name, "Daily Radar")} / account`,
        }),
      });
      await refreshDesk(false);
      setConsent(false);
      setMessage("Selected public research fields copied into the current account workspace.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Account import failed.");
    } finally {
      setBusy("");
    }
  }

  async function saveRule(watchlist: Row) {
    const watchlistId = text(watchlist.resource_id);
    const existing = rules.find((row) => text(row.watchlist_resource_id) === watchlistId);
    setBusy(`rule-${watchlistId}`);
    try {
      await accountRequest(`research-desk/watchlists/${encodeURIComponent(watchlistId)}/rule`, {
        method: "PUT",
        body: JSON.stringify({
          enabled: true,
          minimum_severity: "material",
          cooldown_minutes: 60,
          expected_version: Number(existing?.version || 0),
        }),
      });
      await refreshDesk(false);
      setMessage("In-app saved-change rule enabled. External delivery remains unavailable.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Rule save failed.");
    } finally {
      setBusy("");
    }
  }

  async function scanChanges(watchlistId: string) {
    setBusy(`scan-${watchlistId}`);
    try {
      const envelope = await accountRequest(`research-desk/watchlists/${encodeURIComponent(watchlistId)}/inbox`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refreshDesk(false);
      setMessage(`Saved observations checked: ${text(record(envelope.data).status, "complete")}. Zero provider calls.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Saved-change scan failed.");
    } finally {
      setBusy("");
    }
  }

  async function updateInbox(item: Row, state: "reviewed" | "acknowledged") {
    const itemId = text(item.resource_id);
    setBusy(`${state}-${itemId}`);
    try {
      await accountRequest(`research-desk/inbox/${encodeURIComponent(itemId)}`, {
        method: "PATCH",
        body: JSON.stringify({ state, expected_version: Number(item.version || 1) }),
      });
      await refreshDesk(false);
      setMessage(state === "reviewed" ? "Research item marked reviewed." : "Research item acknowledged.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Inbox update failed.");
    } finally {
      setBusy("");
    }
  }

  async function reviewSyncPlan() {
    setBusy("sync-preview");
    try {
      const envelope = await accountRequest("research-desk/sync/preview");
      setSyncPlan(record(envelope.data));
      setSyncConsent(false);
      setMessage("Bounded sync plan reviewed. No hosted upload occurred.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sync preview failed.");
    } finally {
      setBusy("");
    }
  }

  async function queueSyncPlan() {
    if (!syncConsent) {
      setMessage("Explicit sync consent is required before a local sync intent can be queued.");
      return;
    }
    const fingerprint = text(localSyncSnapshot.snapshot_fingerprint, "local-snapshot");
    setBusy("sync-queue");
    try {
      await accountRequest("research-desk/sync/queue", {
        method: "POST",
        body: JSON.stringify({
          consent: true,
          idempotency_key: `phase6l-${fingerprint}`.slice(0, 128),
        }),
      });
      await refreshDesk(false);
      setSyncConsent(false);
      setMessage("Offline sync intent queued locally. Hosted persistence remains unavailable.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sync queue failed.");
    } finally {
      setBusy("");
    }
  }

  async function replaySyncQueue() {
    setBusy("sync-replay");
    try {
      const envelope = await accountRequest("research-desk/sync/replay", {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refreshDesk(false);
      setMessage(`Sync replay: ${text(record(envelope.data).status, "complete")}. Local research remained available.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sync replay failed.");
    } finally {
      setBusy("");
    }
  }

  async function cancelSyncMutation(mutationId: string) {
    setBusy(`sync-cancel-${mutationId}`);
    try {
      await accountRequest(`research-desk/sync/queue/${encodeURIComponent(mutationId)}`, { method: "DELETE" });
      await refreshDesk(false);
      setMessage("Pending local sync intent canceled. No hosted record changed.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sync cancellation failed.");
    } finally {
      setBusy("");
    }
  }

  function toggleCandidate(candidateId: string) {
    setSelected((current) => current.includes(candidateId)
      ? current.filter((value) => value !== candidateId)
      : [...current, candidateId]);
  }

  return (
    <section className="tenant-research-desk" data-phase6k-tenant-research="true" data-state={loadState}>
      <button type="button" className="tenant-research-launcher" onClick={() => void openDesk()} aria-expanded={expanded}>
        <span><CircleUserRound size={16} aria-hidden="true" /><strong>Account research</strong></span>
        <small>{loadState === "ready"
          ? `${text(summary.watchlist_count, "0")} lists / ${text(summary.unread_count, "0")} new`
          : loadState === "loading"
          ? "Checking account continuity"
          : loadState === "offline"
          ? "Account runtime offline"
          : "Hosted or local account"}</small>
        {expanded ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
      </button>

      {expanded ? (
        <div className="tenant-research-body">
          <div className="tenant-research-truthbar">
            <span><ShieldCheck size={14} aria-hidden="true" /> Session-derived ownership</span>
            <span data-state={hostedIdentity ? continuityState : "local-only"}>
              {hostedIdentity ? <Cloud size={14} aria-hidden="true" /> : <CloudOff size={14} aria-hidden="true" />}
              {hostedIdentity ? `Hosted ${continuityState}` : "Local-only session"}
            </span>
            <span><BellRing size={14} aria-hidden="true" /> External delivery unavailable</span>
          </div>

          {loadState === "loading" ? <div className="tenant-research-loading"><LoaderCircle className="spin" size={16} /> Loading account boundary</div> : null}

          {loadState === "anonymous" ? (
            <div className="tenant-signin-panel">
              <div className="tenant-hosted-signin">
                <div><span className="eyebrow">Hosted research account</span><strong>Restore your saved terminal state</strong></div>
                <label><span>Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" disabled={!hostedSignInAvailable || Boolean(busy)} /></label>
                <label><span>Password</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" disabled={!hostedSignInAvailable || Boolean(busy)} /></label>
                <button type="button" className="primary" onClick={() => void signInHosted()} disabled={!hostedSignInAvailable || Boolean(busy)}><KeyRound size={14} /> Sign in</button>
              </div>
              <div className="tenant-local-qa-signin">
                <span className="eyebrow">Local QA identity</span>
                {localSignInAvailable ? (
                  <div>
                    <button type="button" onClick={() => void signIn("analyst-a")} disabled={Boolean(busy)}><LogIn size={14} /> Analyst A</button>
                    <button type="button" onClick={() => void signIn("analyst-b")} disabled={Boolean(busy)}><LogIn size={14} /> Analyst B</button>
                  </div>
                ) : <small>Disabled</small>}
              </div>
            </div>
          ) : null}

          {loadState === "ready" ? (
            <>
            {hostedIdentity ? (
              <section className="account-continuity-console" data-phase6p-continuity={continuityState}>
                <header>
                  <div><span className="eyebrow">Supabase account continuity</span><h3><Cloud size={15} aria-hidden="true" /> Hosted workspace</h3></div>
                  <div className="account-continuity-actions">
                    <button type="button" onClick={() => void replayContinuity()} disabled={Boolean(busy) || !accountCanWrite} title="Retry pending account recovery"><RefreshCw size={14} aria-hidden="true" /></button>
                    <button type="button" onClick={() => void exportContinuity()} disabled={Boolean(busy)} title="Export account workspace"><Download size={14} aria-hidden="true" /></button>
                    <label className="account-continuity-upload" title="Import account backup" aria-disabled={Boolean(busy) || !accountCanWrite}>
                      <Upload size={14} aria-hidden="true" />
                      <input className="sr-only" type="file" accept="application/json,.json" aria-label="Import account backup" onChange={(event) => void importContinuity(event)} disabled={Boolean(busy) || !accountCanWrite} />
                    </label>
                    <button type="button" className={deleteArmed ? "danger" : ""} onClick={() => void deleteHostedContinuity()} disabled={Boolean(busy) || !accountCanWrite} title={deleteArmed ? "Confirm hosted document deletion" : "Delete hosted account document"}><Trash2 size={14} aria-hidden="true" /></button>
                  </div>
                </header>
                <div className="account-continuity-state" role="status" aria-live="polite" aria-atomic="true">
                  <span data-state={continuityState}>{continuityState}</span>
                  <span>Remote v{text(continuity.remote_version, "0")}</span>
                  <span data-state={Number(continuity.pending_count || 0) ? "pending" : "quiet"}>Pending {text(continuity.pending_count, "0")}</span>
                  <span data-state={Number(continuity.conflict_count || 0) ? "conflict" : "quiet"}>Conflicts {text(continuity.conflict_count, "0")}</span>
                  <span>{text(continuityRepository.source_status, "configured-unverified")}</span>
                  {!accountCanWrite ? <span data-state="conflict">Read only</span> : null}
                  <span>Market calls 0</span>
                </div>
                {continuityState === "conflict" || Number(continuity.conflict_count || 0) > 0 ? (
                  <div className="account-continuity-conflict">
                    <strong>Local and hosted versions differ</strong>
                    <div>
                      <button type="button" onClick={() => void resolveContinuity("keep-local")} disabled={Boolean(busy) || !accountCanWrite}>Keep local</button>
                      <button type="button" onClick={() => void resolveContinuity("use-hosted")} disabled={Boolean(busy) || !accountCanWrite}>Use hosted</button>
                    </div>
                  </div>
                ) : null}
                <dl>
                  <div><dt>Restored</dt><dd>{shortClock(continuity.last_restore_at)}</dd></div>
                  <div><dt>Synced</dt><dd>{shortClock(continuity.last_sync_at)}</dd></div>
                  <div><dt>Recovered</dt><dd>{shortClock(continuity.last_recovery_at)}</dd></div>
                </dl>
              </section>
            ) : (
            <section className="tenant-sync-console" data-phase6l-sync-state={text(sync.state, "hosted-unavailable")}>
              <header>
                <div><span className="eyebrow">Local-first / explicit reconciliation</span><h3><GitCompareArrows size={15} aria-hidden="true" /> Research sync</h3></div>
                <button type="button" onClick={() => void reviewSyncPlan()} disabled={Boolean(busy)}><Eye size={14} /> Review sync plan</button>
              </header>
              <div className="tenant-sync-state-strip" role="status" aria-live="polite">
                <span data-state="local">Local available</span>
                <span data-state="hosted"><CloudOff size={13} aria-hidden="true" /> Hosted unavailable</span>
                <span data-state={Number(sync.pending_count || 0) ? "pending" : "quiet"}>Pending {text(sync.pending_count, "0")}</span>
                <span data-state={Number(sync.conflict_count || 0) ? "conflict" : "quiet"}>Conflicts {text(sync.conflict_count, "0")}</span>
                <span>Market provider calls 0</span>
              </div>

              {Object.keys(syncPlan).length ? (
                <div className="tenant-sync-plan">
                  <div>
                    <strong>{text(localSyncSnapshot.resource_count, "0")} bounded records</strong>
                    <small>{text(localSyncSnapshot.payload_bytes, "0")} bytes / private notes, credentials, identity excluded</small>
                    <p>This queues a sanitized offline intent. It does not contact or claim a hosted account store.</p>
                  </div>
                  <label>
                    <input type="checkbox" checked={syncConsent} onChange={(event) => setSyncConsent(event.target.checked)} />
                    <span><strong>Explicit sync consent</strong><small>Queue this bounded snapshot locally for a future verified adapter.</small></span>
                  </label>
                  <button type="button" className="primary" onClick={() => void queueSyncPlan()} disabled={!syncConsent || Boolean(busy)}><Check size={14} /> Queue offline plan</button>
                </div>
              ) : null}

              {syncQueue.length ? (
                <div className="tenant-sync-queue" aria-label="Bounded offline sync queue">
                  {syncQueue.map((mutation) => (
                    <article key={text(mutation.mutation_id)} data-state={text(mutation.status)}>
                      <div><strong>{text(mutation.status, "pending")}</strong><small>{text(mutation.resource_count, "0")} records / {text(mutation.payload_bytes, "0")} bytes / attempt {text(mutation.attempt_count, "0")}</small></div>
                      {Boolean(sync.retry_available) ? <button type="button" onClick={() => void replaySyncQueue()} disabled={Boolean(busy)}><RotateCcw size={14} /> Retry</button> : null}
                      <button type="button" aria-label="Cancel pending sync plan" onClick={() => void cancelSyncMutation(text(mutation.mutation_id))} disabled={Boolean(busy)}><Trash2 size={14} /> Cancel</button>
                    </article>
                  ))}
                </div>
              ) : <p className="tenant-sync-empty">No sync intent is queued. Local account research is complete without hosted persistence.</p>}
            </section>
            )}

            <div className="tenant-research-grid">
              <section className="tenant-import-preview">
                <header>
                  <div><span className="eyebrow">Local to account / explicit consent</span><h3>Import preview</h3></div>
                  <button type="button" onClick={() => void previewLocalImport()} disabled={Boolean(busy)}><Eye size={14} /> Preview local import</button>
                </header>
                <div className="tenant-import-meta"><span>{text(preview.candidate_count, "0")} candidates</span><span>{text(preview.provider_call_count, "0")} provider calls</span><span>Notes excluded</span></div>
                <div className="tenant-candidate-list" role="list" aria-label="Bounded local import candidates">
                  {candidates.map((candidate) => {
                    const id = text(candidate.candidate_id);
                    const evidence = record(candidate.evidence);
                    return (
                      <label key={id}>
                        <input type="checkbox" checked={selected.includes(id)} onChange={() => toggleCandidate(id)} />
                        <strong>{text(candidate.symbol)}</strong>
                        <span>{text(candidate.display_name)}</span>
                        <small>{text(evidence.source_status, "unavailable")} / {text(evidence.provider, "saved local")} / {shortClock(evidence.observed_at)}</small>
                      </label>
                    );
                  })}
                </div>
                <label className="tenant-import-consent">
                  <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
                  <span>I consent to copy the selected public research fields into this account workspace.</span>
                </label>
                <div className="tenant-import-actions">
                  <button type="button" onClick={() => { setSelected([]); setConsent(false); setMessage("Import canceled. No account data changed."); }}><X size={14} /> Cancel</button>
                  <button type="button" className="primary" onClick={() => void confirmImport()} disabled={!consent || !selected.length || Boolean(busy)}><Check size={14} /> Confirm import</button>
                </div>
              </section>

              <section className="tenant-account-watchlists">
                <header><div><span className="eyebrow">Tenant-owned daily radar</span><h3>Account watchlists</h3></div><strong>{watchlists.length}</strong></header>
                {watchlists.length ? watchlists.map((watchlist) => (
                  <article key={text(watchlist.resource_id)}>
                    <div><strong>{text(watchlist.name)}</strong><small>{text(watchlist.item_count, "0")} exact identities / v{text(watchlist.version, "1")}</small></div>
                    <div className="tenant-watchlist-symbols">
                      {records(watchlist.items).map((item) => <Link key={text(item.resource_id)} href={text(item.research_href, "/?view=analyst-workspace")}>{text(item.symbol)}<small>{text(item.source_status)} / {shortClock(item.observed_at)}</small></Link>)}
                    </div>
                    <div className="tenant-watchlist-actions">
                      <button type="button" onClick={() => void saveRule(watchlist)} disabled={Boolean(busy)}><BellRing size={14} /> In-app rule</button>
                      <button type="button" onClick={() => void scanChanges(text(watchlist.resource_id))} disabled={Boolean(busy)}><RefreshCw size={14} className={busy === `scan-${text(watchlist.resource_id)}` ? "spin" : ""} /> Check saved changes</button>
                    </div>
                  </article>
                )) : <p className="tenant-empty">No account watchlist yet. Review the bounded preview, select rows, and explicitly confirm.</p>}
              </section>

              <section className="tenant-inbox">
                <header>
                  <div><span className="eyebrow">Research inbox / fewer, more meaningful changes</span><h3><Inbox size={16} /> Attention queue</h3></div>
                  <label className="tenant-inbox-filter"><span className="sr-only">Inbox state</span><select value={inboxFilter} onChange={(event) => setInboxFilter(event.target.value)}><option value="attention">Attention {text(attention.attention_count, "0")}</option><option value="all">All {inbox.length}</option><option value="new">New</option><option value="reviewed">Reviewed</option><option value="acknowledged">Acknowledged</option><option value="expired">Expired</option></select></label>
                </header>
                <div className="tenant-attention-summary"><span>{text(attention.attention_count, "0")} needs review</span><span>{text(attention.degraded_source_count, "0")} source gaps</span><span>No push noise</span></div>
                {filteredInbox.length ? filteredInbox.map((item) => (
                  <article key={text(item.resource_id)} data-state={text(item.state)}>
                    <div><span className={`severity ${text(item.severity)}`}>{text(item.severity)}</span><strong>{text(item.title)}</strong><small>{text(item.source_status)} / {text(item.state)} / {shortClock(item.observed_at)}</small></div>
                    <p>{text(item.summary)}</p>
                    {Array.isArray(item.attention_reason) ? <small className="tenant-attention-reason">Priority: {item.attention_reason.map(String).join(" / ")}</small> : null}
                    <div>
                      <Link href={text(item.research_href, "/?view=analyst-workspace")}>Open evidence</Link>
                      {text(item.state) === "new" ? <button type="button" onClick={() => void updateInbox(item, "reviewed")} disabled={Boolean(busy)}>Review</button> : null}
                      {text(item.state) !== "acknowledged" ? <button type="button" onClick={() => void updateInbox(item, "acknowledged")} disabled={Boolean(busy)}>Acknowledge</button> : <span><Check size={13} /> Acknowledged</span>}
                    </div>
                  </article>
                )) : <p className="tenant-empty">No saved-change item. Enable an in-app rule, then check two saved observations.</p>}
              </section>
            </div>
            </>
          ) : null}

          <p className="tenant-research-status" role="status" aria-live="polite">{message}</p>
        </div>
      ) : null}
    </section>
  );
}

function shortClock(value: unknown) {
  const raw = text(value, "clock unavailable");
  if (raw === "clock unavailable") return raw;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? raw.slice(0, 16) : parsed.toISOString().slice(0, 16).replace("T", " ") + "Z";
}
