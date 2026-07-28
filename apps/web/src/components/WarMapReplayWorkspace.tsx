"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { LeafletWarMap } from "@/components/LeafletWarMap";
import type { ContractEnvelope, RuntimeMode } from "@/lib/contracts";
import { sanitizeWarMapSearchParams } from "@/lib/product-routes";

type Row = Record<string, unknown>;
type ReplayState = "loading" | "ready" | "empty" | "fixture" | "unavailable" | "error";

interface WarMapReplayWorkspaceProps {
  currentMarkers: Row[];
  currentLayers: Row[];
  currentNews: Row[];
  currentAssets: Row[];
  currentLinks: Row[];
  currentEventContexts: Row[];
  defaultSelectedMarkerId: string;
  unavailableSources: Row[];
  readiness: Row;
  replayFixture: ContractEnvelope | null;
  apiBaseUrl: string | null;
  runtimeMode: RuntimeMode;
}

export function WarMapReplayWorkspace({
  currentMarkers,
  currentLayers,
  currentNews,
  currentAssets,
  currentLinks,
  currentEventContexts,
  defaultSelectedMarkerId,
  unavailableSources,
  readiness,
  replayFixture,
  apiBaseUrl,
  runtimeMode,
}: WarMapReplayWorkspaceProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fixtureMode = runtimeMode === "fixture";
  const [replay, setReplay] = useState<Row>(() => fixtureMode ? replayData(replayFixture) : {});
  const [state, setState] = useState<ReplayState>(() => fixtureMode ? "fixture" : apiBaseUrl ? "loading" : "unavailable");
  const [notice, setNotice] = useState("");
  const requestedTime = safeSnapshotId(searchParams.get("time"));
  const requestedCompare = safeSnapshotId(searchParams.get("compareTo"));

  const updateUrl = useCallback((values: { time?: string; compareTo?: string }) => {
    const params = sanitizeWarMapSearchParams(new URLSearchParams(searchParams.toString()));
    for (const [key, value] of Object.entries(values)) {
      if (value) params.set(key, value);
      else params.delete(key);
    }
    router.replace(`/?${params.toString()}`, { scroll: false });
  }, [router, searchParams]);

  const loadReplay = useCallback(async (time = requestedTime, compareTo = requestedCompare) => {
    if (fixtureMode) {
      setReplay(replayData(replayFixture));
      setState("fixture");
      return;
    }
    if (!apiBaseUrl) {
      setState("unavailable");
      return;
    }
    setState("loading");
    const query = new URLSearchParams();
    if (time) query.set("time", time);
    if (compareTo && compareTo !== time) query.set("compareTo", compareTo);
    try {
      const response = await fetch(`${apiBaseUrl}/api/war-room-map-replay${query.size ? `?${query}` : ""}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Replay API returned ${response.status}.`);
      const envelope = await response.json() as ContractEnvelope;
      const data = replayData(envelope);
      setReplay(data);
      setState(asRows(data.snapshots).length ? "ready" : "empty");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Replay API unavailable.");
      setState("error");
    }
  }, [apiBaseUrl, fixtureMode, replayFixture, requestedCompare, requestedTime]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadReplay(), 0);
    return () => window.clearTimeout(timer);
  }, [loadReplay]);

  const timeline = asRows(replay.snapshots);
  const activeSnapshot = asRow(replay.active_snapshot);
  const comparisonSnapshot = asRow(replay.comparison_snapshot);
  const diff = asRow(replay.diff);
  const collections = asRow(diff.collections);
  const eventDiff = asRow(collections.events);
  const activeMarkers = asRows(activeSnapshot.markers);
  const snapshotMode = Boolean(requestedTime && activeSnapshot.snapshot_id);
  const replayMarkers = decorateMarkers(snapshotMode && activeMarkers.length ? activeMarkers : currentMarkers, snapshotMode ? eventDiff : {});
  const replayLayers = snapshotMode && asRows(activeSnapshot.layers).length ? asRows(activeSnapshot.layers) : currentLayers;
  const replayNews = snapshotMode && asRows(activeSnapshot.news).length ? asRows(activeSnapshot.news) : currentNews;
  const replayAssets = snapshotMode && asRows(activeSnapshot.assets).length ? asRows(activeSnapshot.assets) : currentAssets;
  const summary = asRow(diff.summary);
  const readinessRow = asRow(replay.readiness);
  const captureEnabled = Boolean(apiBaseUrl && !fixtureMode && state !== "loading");

  async function captureSnapshot() {
    if (!captureEnabled || !apiBaseUrl) return;
    setNotice("Capturing current source-labeled observation...");
    setState("loading");
    try {
      const response = await fetch(`${apiBaseUrl}/api/war-room-map-snapshots`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ runtime_mode: runtimeMode === "live-if-available" ? "live-if-available" : "cache", retention_days: 30 }),
      });
      if (!response.ok) throw new Error(`Capture API returned ${response.status}.`);
      const envelope = await response.json() as ContractEnvelope;
      const data = replayData(envelope);
      const capture = asRow(data.capture_result);
      const activeId = text(asRow(data.active_snapshot).snapshot_id, "");
      setReplay(data);
      setState("ready");
      setNotice(capture.deduplicated === true ? "Identical observation already exists; history was not duplicated." : "New local-private observation captured.");
      if (activeId) updateUrl({ time: activeId, compareTo: requestedCompare === activeId ? "" : requestedCompare });
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Snapshot capture failed.");
      setState("error");
    }
  }

  function chooseTime(snapshotId: string) {
    const safe = safeSnapshotId(snapshotId);
    if (!safe) return;
    const nextCompare = requestedCompare === safe ? "" : requestedCompare;
    updateUrl({ time: safe, compareTo: nextCompare });
  }

  function chooseCompare(snapshotId: string) {
    const safe = safeSnapshotId(snapshotId);
    updateUrl({ compareTo: safe });
  }

  return (
    <div className="war-map-replay phase5u-map-first" data-phase5u-map-first="true" data-replay-state={state} data-snapshot-count={String(timeline.length)} data-compare-active={String(Boolean(snapshotMode && comparisonSnapshot.snapshot_id))}>
      <section className="replay-command-deck war-map-ops-toolbar" aria-labelledby="replay-title">
        <div className="replay-title-block">
          <span className="eyebrow">Observed risk history</span>
          <h3 id="replay-title">Global Risk Replay</h3>
          <p>{text(replay.caveat, "Capture the current map to begin local observed history.")}</p>
        </div>
        <div className="replay-clock-grid" aria-label="Replay clocks">
          <ReplayClock label="Active" value={snapshotMode ? text(activeSnapshot.captured_at, "time unavailable") : "Current map"} tone={snapshotMode ? "active" : "current"} />
          <ReplayClock label="Compare" value={snapshotMode ? text(comparisonSnapshot.captured_at, "Off") : "Off"} tone={snapshotMode && comparisonSnapshot.snapshot_id ? "compare" : "off"} />
          <ReplayClock label="Truth" value={text(replay.historical_truth, "current-state-only")} tone={fixtureMode ? "fixture" : "truth"} />
        </div>
        <label className="war-map-ops-compare">
          <span>Compare</span>
          <select value={snapshotMode ? text(comparisonSnapshot.snapshot_id, requestedCompare) : ""} onChange={(event) => chooseCompare(event.target.value)} disabled={!snapshotMode || timeline.length < 2 || fixtureMode}>
            <option value="">Off</option>
            {timeline.filter((row) => text(row.snapshot_id) !== text(activeSnapshot.snapshot_id)).map((row) => (
              <option key={text(row.snapshot_id)} value={text(row.snapshot_id)}>{formatClock(row.captured_at)} / {text(row.source_status)}</option>
            ))}
          </select>
        </label>
        <button className="snapshot-capture-button" type="button" disabled={!captureEnabled} onClick={captureSnapshot} title={captureEnabled ? "Capture the current server-built map observation" : "Local API connection required"}>
          <span aria-hidden="true">+</span> Capture observation
        </button>
      </section>

      <LeafletWarMap
        markers={replayMarkers}
        layers={replayLayers}
        timelineFilters={[{ filter_id: "all", label: "All captured rows", window_hours: null, marker_count: replayMarkers.length, reference_time: activeSnapshot.captured_at }]}
        relatedNews={replayNews}
        connectedAssets={replayAssets}
        eventLinks={currentLinks}
        eventContexts={currentEventContexts}
        defaultSelectedMarkerId={defaultSelectedMarkerId}
        unavailableSources={unavailableSources}
        readiness={{ ...readiness, ...readinessRow, historical_truth: replay.historical_truth }}
        snapshotReplay={snapshotMode}
        comparisonActive={Boolean(snapshotMode && comparisonSnapshot.snapshot_id)}
      />

      <section className="snapshot-timeline war-map-ops-timeline" aria-label="Captured observation timeline">
        <div className="snapshot-timeline-heading">
          <div><strong>{timeline.length} observations</strong><span>{stateLabel(state, apiBaseUrl)}</span></div>
          <label>
            <span>Compare to</span>
            <select value={text(comparisonSnapshot.snapshot_id, requestedCompare)} onChange={(event) => chooseCompare(event.target.value)} disabled={timeline.length < 2 || fixtureMode}>
              <option value="">Off</option>
              {timeline.filter((row) => text(row.snapshot_id) !== text(activeSnapshot.snapshot_id)).map((row) => (
                <option key={text(row.snapshot_id)} value={text(row.snapshot_id)}>{formatClock(row.captured_at)} / {text(row.source_status)}</option>
              ))}
            </select>
          </label>
        </div>
        {timeline.length ? (
          <div className="snapshot-density-strip" role="list" aria-label="Available captured times">
            {[...timeline].reverse().map((row, index) => {
              const id = text(row.snapshot_id);
              const active = id === text(activeSnapshot.snapshot_id);
              const compared = id === text(comparisonSnapshot.snapshot_id);
              const density = Math.max(10, Math.min(100, number(row.marker_count) ?? (index + 1) * 28));
              return (
                <button type="button" role="listitem" className={`${active ? "active" : ""}${compared ? " compared" : ""}`} key={id} onClick={() => chooseTime(id)} disabled={fixtureMode && !active} title={`${formatClock(row.captured_at)} / ${text(row.source_status)}`}>
                  <i style={{ height: `${density}%` }} />
                  <time>{shortClock(row.captured_at)}</time>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="snapshot-empty-state"><strong>No observed history yet.</strong><span>Current map rows stay current; they are not backfilled as historical data.</span></div>
        )}
        {notice ? <p className={`replay-notice ${state}`}>{notice}</p> : null}
      </section>

      <section className="replay-diff-strip war-map-ops-diff" aria-label="Snapshot changes">
        <DiffMetric label="Events" collection={asRow(collections.events)} />
        <DiffMetric label="Layers" collection={asRow(collections.layers)} />
        <DiffMetric label="Providers" collection={asRow(collections.providers)} />
        <DiffMetric label="News" collection={asRow(collections.news)} />
        <DiffMetric label="Assets" collection={asRow(collections.assets)} />
        <div className="diff-total"><span>Total change</span><strong>{number(summary.added) ?? 0} + / {number(summary.changed) ?? 0} ~ / {number(summary.removed) ?? 0} -</strong></div>
      </section>
    </div>
  );
}

function ReplayClock({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <div className={`replay-clock ${tone}`}><span>{label}</span><strong>{formatClock(value)}</strong></div>;
}

function DiffMetric({ label, collection }: { label: string; collection: Row }) {
  const summary = asRow(collection.summary);
  return (
    <article>
      <span>{label}</span>
      <strong>{number(summary.added) ?? 0}<i>+</i> {number(summary.changed) ?? 0}<i>~</i> {number(summary.removed) ?? 0}<i>-</i></strong>
      <small>{number(summary.unchanged) ?? 0} unchanged / {number(summary.refreshed) ?? 0} refreshed</small>
    </article>
  );
}

function decorateMarkers(active: Row[], eventDiff: Row): Row[] {
  const additions = asRows(eventDiff.added);
  const changes = asRows(eventDiff.changed);
  const removals = asRows(eventDiff.removed);
  const addedIds = new Set(additions.map((row) => text(row.identity)));
  const changedById = new Map(changes.map((row) => [text(row.identity), row]));
  const output = active.map((marker) => {
    const identity = markerIdentity(marker);
    const changed = changedById.get(identity);
    if (addedIds.has(identity)) return { ...marker, change_status: "added" };
    if (changed) return { ...marker, change_status: "changed", changed_fields: changed.changed_fields };
    return marker;
  });
  for (const row of removals) {
    const before = asRow(row.before);
    if (before.marker_id) output.push({ ...before, change_status: "removed" });
  }
  return output;
}

function markerIdentity(marker: Row): string {
  for (const key of ["marker_id", "event_id", "source_url", "title"]) {
    const value = text(marker[key], "");
    if (value) return `${key}:${value}`;
  }
  return "";
}

function replayData(envelope: ContractEnvelope | null): Row {
  return envelope && asRow(envelope.data) ? asRow(envelope.data) : {};
}

function safeSnapshotId(value: string | null): string {
  return value && /^mapsnap_[a-f0-9]{20}$/.test(value) ? value : "";
}

function stateLabel(state: ReplayState, apiBaseUrl: string | null): string {
  if (state === "fixture") return "fictional demo, capture disabled";
  if (!apiBaseUrl) return "local API connection required";
  if (state === "empty") return "local-private store is empty";
  if (state === "loading") return "refreshing local history";
  if (state === "error") return "local history unavailable";
  return "project-captured, local-private";
}

function formatClock(value: unknown): string {
  const parsed = typeof value === "string" ? Date.parse(value) : Number.NaN;
  if (!Number.isFinite(parsed)) return text(value, "unavailable");
  return new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZoneName: "short" }).format(parsed);
}

function shortClock(value: unknown): string {
  const parsed = typeof value === "string" ? Date.parse(value) : Number.NaN;
  if (!Number.isFinite(parsed)) return "--";
  return new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit" }).format(parsed);
}

function asRow(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}

function asRows(value: unknown): Row[] {
  return Array.isArray(value) ? value.filter((item): item is Row => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
}

function number(value: unknown): number | null {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function text(value: unknown, fallback = "none"): string {
  return value === null || value === undefined || value === "" || typeof value === "object" ? fallback : String(value);
}
