"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { LatLng, LatLngBounds, LayerGroup, Map as LeafletMap, Marker as LeafletMarker } from "leaflet";
import { canonicalAssetHref, sanitizeWarMapSearchParams } from "@/lib/product-routes";

type Row = Record<string, unknown>;
type LeafletModule = typeof import("leaflet");
type MapState = "loading" | "ready" | "empty" | "fallback" | "error";

interface LeafletWarMapProps {
  markers: Row[];
  layers: Row[];
  timelineFilters: Row[];
  compareWindows?: Row[];
  relatedNews?: Row[];
  connectedAssets?: Row[];
  eventLinks?: Row[];
  eventContexts?: Row[];
  defaultSelectedMarkerId?: string;
  unavailableSources?: Row[];
  readiness?: Row;
  snapshotReplay?: boolean;
  comparisonActive?: boolean;
}

export function LeafletWarMap({
  markers,
  layers,
  timelineFilters,
  compareWindows = [],
  relatedNews = [],
  connectedAssets = [],
  eventLinks = [],
  eventContexts = [],
  defaultSelectedMarkerId = "",
  unavailableSources = [],
  readiness = {},
  snapshotReplay = false,
  comparisonActive = false,
}: LeafletWarMapProps) {
  const searchParams = useSearchParams();
  const mapNodeRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const markerLayerRef = useRef<LayerGroup | null>(null);
  const markerRefs = useRef<Map<string, LeafletMarker>>(new Map());
  const forceFallback = searchParams.get("mapMode") === "fallback";
  const [leaflet, setLeaflet] = useState<LeafletModule | null>(null);
  const [rendererState, setMapState] = useState<MapState>("loading");
  const [rendererMarkerCount, setRenderedMarkerCount] = useState(0);
  const [layerOverride, setLayerOverride] = useState<string[] | null>(null);
  const [timelineOverride, setTimelineOverride] = useState("");
  const [compareOverride, setCompareOverride] = useState("");
  const [selectedMarkerOverride, setSelectedMarkerOverride] = useState("");
  const requestedLayerIds = useMemo(() => layersFromUrl(searchParams.get("layers"), layers), [layers, searchParams]);
  const activeLayerIds = layerOverride ?? requestedLayerIds;
  const activeTimelineId = snapshotReplay ? "all" : timelineOverride || searchParams.get("timeline") || text(timelineFilters[0]?.filter_id, "all");
  const selectedMarkerId = selectedMarkerOverride || searchParams.get(snapshotReplay ? "selected" : "event") || defaultSelectedMarkerId || text(markers[0]?.marker_id, "");
  const compareWindowId = compareOverride || searchParams.get("compare") || "off";
  const mapState: MapState = forceFallback ? "fallback" : rendererState;

  const activeTimeline = useMemo(
    () => timelineFilters.find((filter) => text(filter.filter_id, "all") === activeTimelineId) ?? timelineFilters[0],
    [timelineFilters, activeTimelineId],
  );

  const visibleMarkers = useMemo(
    () => filterMarkers(markers, activeLayerIds, activeTimeline),
    [markers, activeLayerIds, activeTimeline],
  );
  const displayMarkers = useMemo(() => clusterMarkers(visibleMarkers), [visibleMarkers]);
  const renderedMarkerCount = forceFallback ? visibleMarkers.length : rendererMarkerCount;

  const selectedMarker = useMemo(
    () => visibleMarkers.find((marker) => text(marker.marker_id, "") === selectedMarkerId) ?? visibleMarkers[0] ?? markers[0],
    [markers, selectedMarkerId, visibleMarkers],
  );
  const selectedContext = useMemo(
    () => contextForMarker(eventContexts, selectedMarker),
    [eventContexts, selectedMarker],
  );

  const selectedNews = useMemo(
    () => selectedContext.marker_id ? asRows(selectedContext.related_news) : newsForMarker(relatedNews, selectedMarker),
    [relatedNews, selectedContext, selectedMarker],
  );
  const selectedAssets = useMemo(
    () => selectedContext.marker_id ? asRows(selectedContext.connected_assets) : assetsForMarker(connectedAssets, selectedMarker, eventLinks),
    [connectedAssets, eventLinks, selectedContext, selectedMarker],
  );
  const selectedEventLinks = useMemo(
    () => asRows(selectedContext.event_links),
    [selectedContext],
  );
  const focusMarkers = useMemo(
    () => focusMarkersForContexts(visibleMarkers, eventContexts),
    [eventContexts, visibleMarkers],
  );

  useEffect(() => {
    const params = mapSearchParams(searchParams, snapshotReplay);
    let changed = false;
    if (!params.has("layers")) {
      params.set("layers", activeLayerIds.join(","));
      changed = true;
    }
    if (!snapshotReplay && !params.has("timeline")) {
      params.set("timeline", activeTimelineId);
      changed = true;
    }
    if (!snapshotReplay && !params.has("compare")) {
      params.set("compare", compareWindowId);
      changed = true;
    }
    const selectedKey = snapshotReplay ? "selected" : "event";
    if (!params.has(selectedKey) && selectedMarkerId) {
      params.set(selectedKey, selectedMarkerId);
      changed = true;
    }
    if (changed) replaceClientMapUrl(params);
  }, [activeLayerIds, activeTimelineId, compareWindowId, searchParams, selectedMarkerId, snapshotReplay]);

  useEffect(() => {
    if (forceFallback) {
      return;
    }

    let cancelled = false;
    import("leaflet")
      .then((module) => {
        if (!cancelled) {
          setLeaflet(module);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMapState("error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [forceFallback, visibleMarkers.length]);

  useEffect(() => {
    if (forceFallback || !leaflet || !mapNodeRef.current || mapRef.current) {
      return;
    }

    try {
      const map = leaflet.map(mapNodeRef.current, {
        attributionControl: true,
        keyboard: true,
        scrollWheelZoom: "center",
        worldCopyJump: true,
      }).setView([22, 18], 2);

      leaflet.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 10,
        minZoom: 2,
      }).addTo(map);

      leaflet.control.scale({ imperial: false }).addTo(map);
      mapRef.current = map;
    } catch {
      queueMicrotask(() => setMapState("error"));
    }

    const refs = markerRefs.current;
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
      refs.clear();
    };
  }, [forceFallback, leaflet]);

  useEffect(() => {
    const map = mapRef.current;
    if (forceFallback || !map || !leaflet) {
      return;
    }

    if (markerLayerRef.current) {
      markerLayerRef.current.removeFrom(map);
    }

    const group = leaflet.layerGroup();
    markerRefs.current.clear();
    let rendered = 0;

    for (const marker of displayMarkers) {
      const lat = number(marker.lat);
      const lon = number(marker.lon);
      const markerId = text(marker.marker_id, text(marker.title, "marker"));
      const representativeId = text(marker.cluster_representative_id, markerId);
      const clusterCount = number(marker.cluster_count) ?? 1;
      if (lat === null || lon === null) {
        continue;
      }

      const leafletMarker = leaflet.marker([lat, lon], {
        icon: leaflet.divIcon({
          className: `leaflet-risk-marker ${markerToneClass(marker)}${clusterCount > 1 ? " cluster" : ""}`,
          html: `<span>${clusterCount > 1 ? clusterCount : escapeHtml(severityInitial(marker.severity))}</span>`,
          iconSize: clusterCount > 1 ? [32, 32] : [26, 26],
          iconAnchor: clusterCount > 1 ? [16, 16] : [13, 13],
          popupAnchor: [0, -11],
        }),
        title: text(marker.title, "Global risk event"),
      });

      leafletMarker.bindPopup(markerPopupHtml(marker), { maxWidth: 340 });
      leafletMarker.on("click", () => selectMarker(representativeId));
      leafletMarker.addTo(group);
      markerRefs.current.set(representativeId, leafletMarker);
      rendered += 1;
    }

    group.addTo(map);
    markerLayerRef.current = group;
    setRenderedMarkerCount(rendered);
    setMapState(rendered > 0 ? "ready" : "empty");

    const bounds = markerBounds(visibleMarkers, leaflet);
    if (bounds) {
      map.fitBounds(bounds, { padding: [42, 42], maxZoom: 5 });
    }
  // Map interaction state stays in the URL without re-running source providers.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayMarkers, forceFallback, leaflet, visibleMarkers]);

  function selectMarker(markerId: string) {
    setSelectedMarkerOverride(markerId);
    const params = clientMapSearchParams(snapshotReplay);
    if (snapshotReplay) params.set("selected", markerId);
    else params.set("event", markerId);
    replaceClientMapUrl(params);
  }

  function focusMarker(marker: Row) {
    const markerId = text(marker.marker_id, "");
    selectMarker(markerId);
    const leafletMarker = markerRefs.current.get(markerId);
    const lat = number(marker.lat);
    const lon = number(marker.lon);
    if (mapRef.current && lat !== null && lon !== null) {
      mapRef.current.flyTo([lat, lon], Math.max(mapRef.current.getZoom(), 4), { duration: 0.45 });
    }
    leafletMarker?.openPopup();
  }

  function toggleLayer(layerId: string) {
    const next = activeLayerIds.includes(layerId) ? activeLayerIds.filter((id) => id !== layerId) : [...activeLayerIds, layerId];
    const usable = next.length ? next : defaultLayerIds(layers);
    setLayerOverride(usable);
    const params = clientMapSearchParams(snapshotReplay);
    params.set("layers", usable.join(","));
    replaceClientMapUrl(params);
  }

  function setTimeline(filterId: string) {
    setTimelineOverride(filterId);
    const params = clientMapSearchParams(snapshotReplay);
    params.set("timeline", filterId);
    replaceClientMapUrl(params);
  }

  function setCompare(windowId: string) {
    setCompareOverride(windowId);
    const params = clientMapSearchParams(snapshotReplay);
    params.set("compare", windowId);
    replaceClientMapUrl(params);
  }

  return (
    <div
      className="leaflet-war-workspace global-map-stage"
      data-renderer="leaflet-war-map"
      data-map-state={mapState}
      data-map-marker-count={String(renderedMarkerCount)}
      data-map-event-count={String(visibleMarkers.length)}
    >
      <div className="global-map-toolbar" aria-label="Map time and comparison controls">
        {snapshotReplay ? <div className="map-replay-mode-label"><span>Captured observation</span><strong>{comparisonActive ? "Comparison overlay" : "Single snapshot"}</strong></div> : null}
        {!snapshotReplay ? <>
        <div className="global-map-time-controls">
          {timelineFilters.map((filter) => {
            const filterId = text(filter.filter_id, "all");
            return (
              <button
                className={filterId === activeTimelineId ? "active" : ""}
                type="button"
                key={filterId}
                onClick={() => setTimeline(filterId)}
              >
                {text(filter.label, filterId)}
              </button>
            );
          })}
        </div>
        <label className="global-map-compare-control">
          <span>Compare</span>
          <select value={compareWindowId} onChange={(event) => setCompare(event.target.value)}>
            <option value="off">Off</option>
            {compareWindows.map((window) => {
              const windowId = text(window.window_id, "off");
              return <option key={windowId} value={windowId}>{text(window.label, windowId)}</option>;
            })}
          </select>
        </label>
        </> : null}
        <span className={`global-map-state ${mapState}`}>{mapState}</span>
      </div>

      <div className="global-map-canvas-grid">
        <section className="global-map-canvas" aria-labelledby="leaflet-map-title">
          <div className="global-map-canvas-heading">
            <div>
              <span className="eyebrow">Operational geography</span>
              <h3 id="leaflet-map-title">{visibleMarkers.length} visible events across {activeLayerIds.length} layers</h3>
            </div>
            <div className="map-legend" aria-label="Coordinate legend">
              <span><i className="legend-dot source" /> source-backed</span>
              <span><i className="legend-dot approx" /> approximate</span>
              <span><i className="legend-dot static" /> static/proxy</span>
              {comparisonActive ? <><span><i className="legend-dot added" /> added</span><span><i className="legend-dot changed" /> changed</span><span><i className="legend-dot removed" /> removed</span></> : null}
            </div>
          </div>

          <div className="global-map-focus-rail" aria-label="Priority event context">
            {focusMarkers.map((marker) => {
              const context = contextForMarker(eventContexts, marker);
              return (
                <button
                  className={text(marker.marker_id) === text(selectedMarker?.marker_id) ? "active" : ""}
                  type="button"
                  key={text(marker.marker_id)}
                  onClick={() => focusMarker(marker)}
                >
                  <span>{text(marker.region, "Global")}</span>
                  <strong>{text(marker.title, "Untitled event")}</strong>
                  <small>{text(context.context_status, "event-only")} / {text(context.context_score, "0")}</small>
                </button>
              );
            })}
          </div>

          {forceFallback ? (
            <FallbackMap markers={visibleMarkers} onSelect={focusMarker} />
          ) : (
            <div ref={mapNodeRef} className="leaflet-map-stage global-leaflet-canvas" aria-label="Interactive global risk map" />
          )}

          {mapState === "loading" ? <div className="global-map-overlay">Loading map renderer...</div> : null}
          {mapState === "empty" ? <div className="global-map-overlay">No coordinate-backed events match the active filters.</div> : null}
          {mapState === "error" ? (
            <div className="global-map-overlay error">
              <strong>Map renderer unavailable</strong>
              <a href={fallbackHref(searchParams, snapshotReplay)}>Open the accessible fallback map</a>
            </div>
          ) : null}

          <div className="global-map-layer-overlay" aria-label="Map layers">
            <div className="global-map-overlay-heading">
              <strong>Layers</strong>
              <span>{activeLayerIds.length} on</span>
            </div>
            {layers.slice(0, 12).map((layer) => {
              const layerId = text(layer.layer_id, text(layer.label, "layer"));
              const disabled = text(layer.availability, "") === "unavailable";
              const checked = activeLayerIds.includes(layerId);
              return (
                <label className={`global-map-layer-row${disabled ? " disabled" : ""}`} key={layerId}>
                  <input type="checkbox" checked={checked} disabled={disabled} onChange={() => toggleLayer(layerId)} />
                  <span className={`layer-source-dot ${statusToneClass(layer.source_status)}`} />
                  <b>{text(layer.label, layerId)}</b>
                  <small>{text(layer.visible_marker_count, text(layer.row_count, "0"))}</small>
                </label>
              );
            })}
          </div>
        </section>

        <aside
          className="global-event-inspector"
          aria-labelledby="leaflet-marker-title"
          data-event-context-status={text(selectedContext.context_status, "event-only")}
        >
          <div className="section-heading">
            <h3 id="leaflet-marker-title">Event Intelligence</h3>
            <span>{text(selectedContext.context_status, text(selectedMarker?.severity, "none"))}</span>
          </div>
          {selectedMarker ? (
            <>
              <MarkerDetail marker={selectedMarker} />
              <EvidenceNews rows={selectedNews} mode={runtimeMode(searchParams.get("mode"))} marker={selectedMarker} />
              <EvidencePath rows={selectedEventLinks} />
              <EvidenceAssets rows={selectedAssets} mode={runtimeMode(searchParams.get("mode"))} originState={originStateForSelection(searchParams, snapshotReplay, selectedMarkerId)} />
            </>
          ) : (
            <p>No event matches the active layers and timeline.</p>
          )}
        </aside>
      </div>

      <div className="global-map-mobile-drawer">
        <section aria-labelledby="global-map-events-title">
          <div className="section-heading">
            <h3 id="global-map-events-title">Event Stream</h3>
            <span>{visibleMarkers.length} rows</span>
          </div>
          <div className="global-map-event-list">
            {visibleMarkers.slice(0, 30).map((marker) => (
              <button
                className={text(marker.marker_id) === text(selectedMarker?.marker_id) ? "active" : ""}
                type="button"
                key={text(marker.marker_id, text(marker.title))}
                onClick={() => focusMarker(marker)}
              >
                <span className={`event-severity ${severityTone(marker.severity)} ${text(marker.change_status, "")}`}>{severityInitial(marker.severity)}</span>
                <span><strong>{text(marker.title, "Untitled event")}</strong><small>{text(marker.region)} / {text(marker.provider)} / {text(marker.source_status)}</small></span>
                <time>{shortTime(marker.timestamp || marker.fetched_at)}</time>
              </button>
            ))}
          </div>
        </section>
        <section className="global-map-source-gaps" aria-labelledby="global-map-gaps-title">
          <div className="section-heading">
            <h3 id="global-map-gaps-title">Source Boundary</h3>
            <span>{unavailableSources.length} gaps</span>
          </div>
          <p>{text(readiness.caveat || readiness.data_gap, "Only successful providers are represented as live map layers.")}</p>
          {unavailableSources.slice(0, 6).map((source, index) => (
            <div key={`${text(source.provider, "source")}-${index}`}>
              <strong>{text(source.provider, text(source.source_id, "Unavailable source"))}</strong>
              <small>{text(source.status, text(source.source_status))} / {text(source.data_gap || source.caveat || source.error)}</small>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

function MarkerDetail({ marker }: { marker: Row }) {
  const sourceUrl = text(marker.source_url, "");
  return (
    <div className="marker-detail">
      <strong className="marker-detail-title">{text(marker.title, "Untitled event")}</strong>
      <p>{text(marker.summary || marker.caveat || marker.data_gap, "No event summary supplied")}</p>
      <div className="detail-pills">
        <span className={`mini-status ${coordinateToneClass(marker.coordinate_status)}`}>coord {text(marker.coordinate_status)}</span>
        <span className={`mini-status ${statusToneClass(marker.source_status)}`}>source {text(marker.source_status)}</span>
      </div>
      <dl>
        {[
          ["Provider", marker.provider],
          ["Region", marker.region],
          ["Confidence", marker.confidence],
          ["Coordinate", marker.coordinate_method],
          ["Freshness", marker.freshness || marker.fetched_at],
        ].map(([label, value]) => (
          <div key={label as string}><dt>{label as string}</dt><dd>{text(value)}</dd></div>
        ))}
      </dl>
      {sourceUrl.startsWith("http") ? <a className="marker-source-link" href={sourceUrl} target="_blank" rel="noreferrer">Open primary source</a> : null}
      <small>{text(marker.data_gap || marker.caveat, "No caveat supplied")}</small>
    </div>
  );
}

function EvidenceNews({ rows, mode, marker }: { rows: Row[]; mode: "fixture" | "cache" | "live-if-available"; marker: Row }) {
  const newsHref = `/?view=news&mode=${encodeURIComponent(mode)}&region=${encodeURIComponent(text(marker.region, "Global"))}&topic=${encodeURIComponent(text(marker.domain, "risk"))}`;
  return (
    <section className="event-evidence-section event-news-section" aria-labelledby="event-news-title">
      <div className="section-heading"><h4 id="event-news-title">Related reporting</h4><span>{rows.length}</span></div>
      {rows.length ? rows.slice(0, 5).map((row, index) => {
        const href = text(row.source_url || row.url, "");
        return (
          <article key={`${text(row.title)}-${index}`}>
            {href.startsWith("http") ? <a href={href} target="_blank" rel="noreferrer">{text(row.title, "Untitled report")}</a> : <strong>{text(row.title, "Untitled report")}</strong>}
            <small>{text(row.provider)} / {text(row.source_status || row.freshness)} / {text(row.match_method, "source context")} / {shortTime(row.published_at || row.fetched_at)}</small>
            {row.match_caveat ? <small>{text(row.match_caveat)}</small> : null}
          </article>
        );
      }) : (
        <div className="event-evidence-empty">
          <p>No direct source-matched reporting for this event.</p>
          <a href={newsHref}>Open the source-backed News desk</a>
        </div>
      )}
    </section>
  );
}

function EvidencePath({ rows }: { rows: Row[] }) {
  return (
    <section className="event-evidence-section event-path-section" aria-labelledby="event-path-title">
      <div className="section-heading"><h4 id="event-path-title">Transmission path</h4><span>{rows.length}</span></div>
      {rows.length ? rows.slice(0, 6).map((row, index) => (
        <article key={`${text(row.edge_id, "edge")}-${index}`}>
          <strong>{text(row.relationship, "linked to")} / {text(row.label, "Context node")}</strong>
          <small>{text(row.node_type)} / {text(row.source_status)} / confidence {text(row.confidence)}</small>
          <small>{text(row.caveat || row.data_gap, "Taxonomy relationship; inspect source context.")}</small>
        </article>
      )) : <p>No bounded event-to-market relationship for this event.</p>}
    </section>
  );
}

function EvidenceAssets({ rows, mode, originState }: { rows: Row[]; mode: "fixture" | "cache" | "live-if-available"; originState: string }) {
  return (
    <section className="event-evidence-section event-assets-section" aria-labelledby="event-assets-title">
      <div className="section-heading"><h4 id="event-assets-title">Market transmission</h4><span>{rows.length}</span></div>
      {rows.length ? rows.slice(0, 7).map((row) => {
        const href = productHrefForAsset(row, mode, originState);
        const content = <><strong>{text(row.label, text(row.id, "Asset"))}</strong><small>{text(row.type)} / {text(row.source_status)} / confidence {text(row.confidence)}</small></>;
        return href ? <a className="event-asset-link" href={href} key={text(row.id)}>{content}</a> : <div className="event-asset-link" key={text(row.id)}>{content}</div>;
      }) : <p>No evidence-backed asset links for this event.</p>}
    </section>
  );
}

function FallbackMap({ markers, onSelect }: { markers: Row[]; onSelect: (marker: Row) => void }) {
  return (
    <div className="global-map-fallback" role="img" aria-label="Accessible geographic event fallback">
      <div className="fallback-map-grid" />
      {markers.slice(0, 50).map((marker) => {
        const lat = number(marker.lat) ?? 0;
        const lon = number(marker.lon) ?? 0;
        return (
          <button
            type="button"
            key={text(marker.marker_id, text(marker.title))}
            title={text(marker.title)}
            style={{ left: `${((lon + 180) / 360) * 100}%`, top: `${((90 - lat) / 180) * 100}%` }}
            onClick={() => onSelect(marker)}
          >
            {severityInitial(marker.severity)}
          </button>
        );
      })}
    </div>
  );
}

function layersFromUrl(value: string | null, layers: Row[]): string[] {
  if (value) {
    const requested = value.split(",").map((item) => item.trim()).filter(Boolean);
    if (requested.length) return requested;
  }
  return defaultLayerIds(layers);
}

function defaultLayerIds(layers: Row[]): string[] {
  const active = layers
    .filter((layer) => text(layer.availability, "") !== "unavailable" && number(layer.visible_marker_count) !== 0)
    .map((layer) => text(layer.layer_id, text(layer.label, "layer")))
    .filter(Boolean);
  if (active.length) return active;
  return layers.filter((layer) => text(layer.availability, "") !== "unavailable").map((layer) => text(layer.layer_id, text(layer.label, "layer"))).filter(Boolean);
}

function filterMarkers(markers: Row[], activeLayerIds: string[], activeTimeline: Row | undefined): Row[] {
  return markers.filter((marker) => {
    if (!markerInTimeline(marker, activeTimeline)) return false;
    const markerLayerIds = stringList(marker.layer_ids);
    return markerLayerIds.length === 0 || activeLayerIds.length === 0 || markerLayerIds.some((id) => activeLayerIds.includes(id));
  });
}

function markerInTimeline(marker: Row, activeTimeline: Row | undefined): boolean {
  const windowHours = number(activeTimeline?.window_hours);
  if (windowHours === null) return true;
  const markerTime = dateMs(marker.timestamp) ?? dateMs(marker.fetched_at);
  const referenceTime = dateMs(activeTimeline?.reference_time) ?? Date.now();
  if (markerTime === null) return true;
  return Math.abs(referenceTime - markerTime) / 3_600_000 <= windowHours;
}

function newsForMarker(newsRows: Row[], marker: Row | undefined): Row[] {
  if (!marker) return [];
  const sourceUrl = text(marker.source_url, "");
  const region = text(marker.region, "").toLowerCase();
  const eventId = text(marker.event_id, "");
  return newsRows.filter((row) => {
    const rowUrl = text(row.source_url || row.url, "");
    const rowRegion = text(row.region || row.location, "").toLowerCase();
    const rowEventId = text(row.event_id, "");
    return Boolean(
      (sourceUrl && rowUrl === sourceUrl) ||
      (eventId && rowEventId === eventId) ||
      (region && region !== "global" && rowRegion === region),
    );
  });
}

function assetsForMarker(assets: Row[], marker: Row | undefined, links: Row[]): Row[] {
  if (!marker) return [];
  const directIds = new Set(stringList(marker.related_asset_node_ids));
  const eventNodeId = text(marker.event_graph_node_id, "");
  for (const link of links) {
    if (text(link.source, "") === eventNodeId) directIds.add(text(link.target, ""));
    if (text(link.target, "") === eventNodeId) directIds.add(text(link.source, ""));
  }
  return assets.filter((asset) => directIds.has(text(asset.id, "")));
}

function contextForMarker(contexts: Row[], marker: Row | undefined): Row {
  if (!marker) return {};
  const markerId = text(marker.marker_id, "");
  return contexts.find((context) => text(context.marker_id, "") === markerId) ?? {};
}

function focusMarkersForContexts(markers: Row[], contexts: Row[]): Row[] {
  const scoreByMarker = new Map(contexts.map((context) => [text(context.marker_id, ""), number(context.context_score) ?? 0]));
  return markers
    .slice()
    .sort((left, right) => {
      const scoreDelta = (scoreByMarker.get(text(right.marker_id, "")) ?? 0) - (scoreByMarker.get(text(left.marker_id, "")) ?? 0);
      if (scoreDelta) return scoreDelta;
      return (number(right.severity_score) ?? 0) - (number(left.severity_score) ?? 0);
    })
    .slice(0, 5);
}

function clusterMarkers(markers: Row[]): Row[] {
  if (markers.length <= 60) return markers;

  const gridDegrees = markers.length > 140 ? 8 : 5;
  const buckets = new Map<string, Row[]>();
  for (const marker of markers) {
    const lat = number(marker.lat);
    const lon = number(marker.lon);
    if (lat === null || lon === null) continue;
    const key = `${Math.floor(lat / gridDegrees)}:${Math.floor(lon / gridDegrees)}`;
    buckets.set(key, [...(buckets.get(key) ?? []), marker]);
  }

  return [...buckets.entries()].map(([key, rows]) => {
    if (rows.length === 1) return rows[0];
    const representative = rows
      .slice()
      .sort((left, right) => (number(right.severity_score) ?? 0) - (number(left.severity_score) ?? 0))[0];
    const lat = rows.reduce((sum, row) => sum + (number(row.lat) ?? 0), 0) / rows.length;
    const lon = rows.reduce((sum, row) => sum + (number(row.lon) ?? 0), 0) / rows.length;
    return {
      ...representative,
      marker_id: `cluster:${key}`,
      cluster_count: rows.length,
      cluster_representative_id: text(representative.marker_id, ""),
      lat,
      lon,
      title: `${rows.length} events in this area`,
      summary: "Select the cluster to inspect its highest-severity event; use the event stream for every member.",
    };
  });
}

function markerBounds(markers: Row[], L: LeafletModule): LatLngBounds | null {
  const latLngs = markers.map((marker) => {
    const lat = number(marker.lat);
    const lon = number(marker.lon);
    return lat === null || lon === null ? null : L.latLng(lat, lon);
  }).filter((latLng): latLng is LatLng => Boolean(latLng));
  return latLngs.length ? L.latLngBounds(latLngs) : null;
}

function markerPopupHtml(marker: Row): string {
  return `<div class="leaflet-risk-popup"><strong>${escapeHtml(text(marker.title, "Untitled event"))}</strong><span>${escapeHtml(text(marker.region))} / ${escapeHtml(text(marker.source_status))}</span><dl><div><dt>Provider</dt><dd>${escapeHtml(text(marker.provider))}</dd></div><div><dt>Confidence</dt><dd>${escapeHtml(text(marker.confidence))}</dd></div><div><dt>Coordinate</dt><dd>${escapeHtml(text(marker.coordinate_status))}</dd></div></dl><p>${escapeHtml(text(marker.data_gap || marker.caveat, "No caveat supplied"))}</p></div>`;
}

function fallbackHref(searchParams: ReturnType<typeof useSearchParams>, snapshotReplay: boolean): string {
  const params = mapSearchParams(searchParams, snapshotReplay);
  params.set("mapMode", "fallback");
  return `/?${params.toString()}`;
}

function productHrefForAsset(asset: Row, mode: "fixture" | "cache" | "live-if-available", originState: string): string | null {
  const id = text(asset.id, "").toLowerCase();
  if (id.includes("btcusd") || id.includes("bitcoin")) {
    return canonicalAssetHref("BTCUSDT", "crypto", "1d", mode, "overview", "3mo", { originView: "war-room-map", originState });
  }
  if (id.includes("aapl") || id.includes("apple")) {
    return canonicalAssetHref("AAPL", "equity", "1d", mode, "overview", "3mo", { originView: "war-room-map", originState });
  }
  return null;
}

function runtimeMode(value: string | null): "fixture" | "cache" | "live-if-available" {
  return value === "fixture" || value === "cache" ? value : "live-if-available";
}

function number(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function dateMs(value: unknown): number | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function shortTime(value: unknown): string {
  const date = dateMs(value);
  if (date === null) return "time unavailable";
  return new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function stringList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => text(item)).filter(Boolean);
  if (typeof value === "string" && value.trim()) return value.split(",").map((item) => item.trim()).filter(Boolean);
  return [];
}

function asRows(value: unknown): Row[] {
  return Array.isArray(value) ? value.filter((item): item is Row => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
}

function text(value: unknown, fallback = "none"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (Array.isArray(value)) return value.length ? value.map((item) => text(item)).join(", ") : fallback;
  if (typeof value === "object") return fallback;
  return String(value);
}

function severityInitial(value: unknown): string {
  return text(value, "w").slice(0, 1).toUpperCase();
}

function severityTone(value: unknown): string {
  const severity = text(value, "").toLowerCase();
  if (["critical", "severe", "high"].some((item) => severity.includes(item))) return "danger";
  if (["elevated", "medium", "watch"].some((item) => severity.includes(item))) return "warn";
  return "neutral";
}

function markerToneClass(marker: Row): string {
  const changeStatus = text(marker.change_status, "");
  if (["added", "changed", "removed"].includes(changeStatus)) return `change-${changeStatus}`;
  const coordinateStatus = text(marker.coordinate_status, "");
  const sourceStatus = text(marker.source_status, "");
  if (sourceStatus.includes("unavailable") || sourceStatus.includes("missing")) return "blocked";
  if (coordinateStatus === "source-backed") return "source";
  if (coordinateStatus === "static/proxy" || sourceStatus.includes("proxy")) return "static";
  return "approx";
}

function coordinateToneClass(value: unknown): string {
  const status = text(value, "");
  if (status === "source-backed") return "ok";
  if (status === "unavailable") return "danger";
  if (["fixture", "static/proxy", "approximate"].includes(status)) return "warn";
  return "neutral";
}

function statusToneClass(value: unknown): string {
  const status = text(value, "");
  if (["live/fresh", "cached", "available"].includes(status)) return "ok";
  if (["missing-key", "unavailable"].includes(status) || status.includes("forbidden")) return "danger";
  if (status.includes("proxy") || ["fixture", "stale"].includes(status) || status.includes("schema-ready")) return "warn";
  return "neutral";
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char] ?? char));
}

function mapSearchParams(searchParams: ReturnType<typeof useSearchParams>, snapshotReplay: boolean): URLSearchParams {
  const params = new URLSearchParams(searchParams.toString());
  return snapshotReplay ? sanitizeWarMapSearchParams(params) : params;
}

function replaceClientMapUrl(params: URLSearchParams) {
  window.history.replaceState(window.history.state, "", `/?${params.toString()}`);
}

function clientMapSearchParams(snapshotReplay: boolean): URLSearchParams {
  const params = new URLSearchParams(window.location.search);
  return snapshotReplay ? sanitizeWarMapSearchParams(params) : params;
}

function originStateForSelection(
  searchParams: ReturnType<typeof useSearchParams>,
  snapshotReplay: boolean,
  selectedMarkerId: string,
): string {
  const params = mapSearchParams(searchParams, snapshotReplay);
  params.set(snapshotReplay ? "selected" : "event", selectedMarkerId);
  return params.toString();
}
