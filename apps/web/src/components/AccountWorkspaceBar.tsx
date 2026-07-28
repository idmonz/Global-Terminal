"use client";

import { CloudOff, CloudUpload, KeyRound, LogIn, LogOut, RotateCcw, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import type { ContractEnvelope } from "@/lib/contracts";

type Row = Record<string, unknown>;

export interface AccountLayoutValue {
  preset: string;
  splitPercent: number;
  focusedPanel: string;
  visiblePanels: string[];
}

interface AccountState {
  envelope: ContractEnvelope | null;
  loading: boolean;
  error: string | null;
  message: string | null;
}

export function AccountWorkspaceBar({
  layout,
  onRestore,
}: {
  layout: AccountLayoutValue;
  onRestore: (layout: AccountLayoutValue) => void;
}) {
  const [state, setState] = useState<AccountState>({
    envelope: null,
    loading: true,
    error: null,
    message: null,
  });
  const [alias, setAlias] = useState("analyst-a");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const data = record(state.envelope?.data);
  const identity = record(data.identity);
  const runtimeTruth = record(data.runtime_truth);
  const workspace = record(data.workspace);
  const preference = record(workspace.preference);
  const value = record(preference.value);
  const persistence = record(data.persistence);
  const authenticated = identity.authenticated === true;
  const localSignInAvailable = runtimeTruth.local_test_sign_in_available === true;
  const hostedSignInAvailable = runtimeTruth.hosted_sign_in_available === true;
  const hostedIdentity = identity.identity_provider === "supabase";
  const accountCanWrite = runtimeTruth.account_write !== false;
  const persistenceState = text(persistence.state, text(persistence.source_status, "local-only"));
  const accountStatus = state.error
    ? "offline"
    : state.message?.startsWith("Conflict:")
    ? "conflict"
    : hostedIdentity
    ? persistenceState
    : authenticated
    ? preference.resource_id
      ? "saved-local-test"
      : "signed-in-local-test"
    : "local";

  async function loadSession(message: string | null = null) {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const response = await fetch("/api/account/session", {
        cache: "no-store",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`account-session-http-${response.status}`);
      const envelope = (await response.json()) as ContractEnvelope;
      setState({ envelope, loading: false, error: null, message });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "account-session-unavailable",
        message: "Local workspace remains available.",
      }));
    }
  }

  useEffect(() => {
    void loadSession();
  }, []);

  async function signInLocal() {
    setState((current) => ({ ...current, loading: true, error: null, message: null }));
    try {
      const response = await fetch("/api/account/local-session", {
        method: "POST",
        cache: "no-store",
        credentials: "same-origin",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ alias, return_to: window.location.pathname + window.location.search }),
      });
      if (!response.ok) throw new Error(`account-signin-http-${response.status}`);
      await loadSession("Signed in to a process-local test workspace.");
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "account-signin-unavailable",
        message: null,
      }));
    }
  }

  async function signInHosted() {
    if (!email.trim() || password.length < 8) {
      setState((current) => ({ ...current, error: null, message: "Enter the hosted account email and password." }));
      return;
    }
    setState((current) => ({ ...current, loading: true, error: null, message: null }));
    try {
      const response = await fetch("/api/account/hosted-session", {
        method: "POST",
        cache: "no-store",
        credentials: "same-origin",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          return_to: window.location.pathname + window.location.search,
        }),
      });
      setPassword("");
      if (!response.ok) throw new Error(`hosted-signin-http-${response.status}`);
      await loadSession("Hosted account restored.");
    } catch (error) {
      setPassword("");
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "hosted-signin-unavailable",
        message: "Browser-local layout remains available.",
      }));
    }
  }

  async function saveToAccount() {
    const csrf = readCookie("gt_csrf");
    setState((current) => ({ ...current, loading: true, error: null, message: "Saving..." }));
    try {
      const response = await fetch("/api/account/preferences/analyst-layout", {
        method: "PUT",
        cache: "no-store",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({
          expected_version: Number(preference.version || 0),
          value: layout,
        }),
      });
      if (response.status === 409) {
        setState((current) => ({ ...current, loading: false, error: null, message: "Conflict: restore the current saved version before retrying." }));
        return;
      }
      if (!response.ok) throw new Error(`account-save-http-${response.status}`);
      await loadSession(hostedIdentity ? "Workspace saved to the hosted account repository." : "Workspace saved to the local QA tenant.");
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "account-save-unavailable",
        message: "Local browser layout remains unchanged.",
      }));
    }
  }

  async function signOut() {
    const csrf = readCookie("gt_csrf");
    setState((current) => ({ ...current, loading: true, error: null, message: null }));
    try {
      const response = await fetch("/api/account/signout", {
        method: "POST",
        cache: "no-store",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
        },
        body: "{}",
      });
      if (!response.ok) throw new Error(`account-signout-http-${response.status}`);
      await loadSession("Signed out. Browser-local workspace is still available.");
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "account-signout-unavailable",
        message: null,
      }));
    }
  }

  function restoreSaved() {
    const candidate: AccountLayoutValue = {
      preset: text(value.preset, "research"),
      splitPercent: Number(value.splitPercent || 58),
      focusedPanel: text(value.focusedPanel, "chart-core"),
      visiblePanels: Array.isArray(value.visiblePanels)
        ? value.visiblePanels.map((item) => String(item))
        : ["chart-core", "financials", "catalysts", "sources"],
    };
    onRestore(candidate);
    setState((current) => ({ ...current, message: "Saved account layout restored in this browser." }));
  }

  return (
    <section
      className="account-workspace-bar"
      data-phase6j-account-workspace="true"
      data-account-status={accountStatus}
      aria-label="Account and workspace persistence"
    >
      <div className="account-workspace-identity">
        {authenticated ? <ShieldCheck size={15} aria-hidden="true" /> : <CloudOff size={15} aria-hidden="true" />}
        <div>
          <span className="eyebrow">Workspace identity</span>
          <strong>{text(identity.display_name, "Local workspace")}</strong>
          <small>{accountStatus} / {accountCanWrite ? text(persistence.source_status, "local-only") : "read-only"}</small>
        </div>
      </div>

      {!authenticated ? (
        <div className="account-signin-controls">
          {hostedSignInAvailable ? (
            <div className="account-hosted-signin">
              <input aria-label="Hosted account email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" placeholder="Email" disabled={state.loading} />
              <input aria-label="Hosted account password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" placeholder="Password" disabled={state.loading} />
              <button type="button" onClick={() => void signInHosted()} disabled={state.loading} title="Sign in to hosted account"><KeyRound size={14} aria-hidden="true" /></button>
            </div>
          ) : null}
          {localSignInAvailable ? (
            <div className="account-local-qa-signin">
              <select aria-label="Process-local test identity" value={alias} onChange={(event) => setAlias(event.target.value)} disabled={state.loading}>
                <option value="analyst-a">QA A</option>
                <option value="analyst-b">QA B</option>
              </select>
              <button type="button" onClick={() => void signInLocal()} disabled={state.loading} title="Use local QA identity" aria-label="Use local test identity"><LogIn size={14} aria-hidden="true" /></button>
            </div>
          ) : null}
          {!hostedSignInAvailable && !localSignInAvailable ? <small>Account sign-in unavailable</small> : null}
        </div>
      ) : (
        <div className="account-sync-controls">
          <button type="button" onClick={() => void saveToAccount()} disabled={state.loading || !accountCanWrite}>
            <CloudUpload size={14} aria-hidden="true" />
            <span>Save account layout</span>
          </button>
          <button type="button" onClick={restoreSaved} disabled={!preference.resource_id || state.loading}>
            <RotateCcw size={14} aria-hidden="true" />
            <span>Restore saved</span>
          </button>
          <button type="button" onClick={() => void signOut()} disabled={state.loading} aria-label="Sign out of account workspace">
            <LogOut size={14} aria-hidden="true" />
          </button>
        </div>
      )}

      <div className={`account-sync-status status-${accountStatus}`} role="status" aria-live="polite" aria-atomic="true">
        <strong>{state.loading ? "Checking" : accountStatus}</strong>
        <small>
          {state.error
            ? `${state.error}. ${state.message || "Local workspace remains available."}`
            : state.message || (hostedIdentity ? "Hosted account continuity active." : "Local layout is never uploaded automatically.")}
        </small>
      </div>
    </section>
  );
}

function record(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}

function text(value: unknown, fallback = "unavailable"): string {
  const candidate = String(value ?? "").trim();
  return candidate || fallback;
}

function readCookie(name: string): string {
  const prefix = `${encodeURIComponent(name)}=`;
  const row = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(prefix));
  return row ? decodeURIComponent(row.slice(prefix.length)) : "";
}
