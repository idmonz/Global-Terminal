# Phase 5H External Evidence Ledger

Updated: 2026-06-20

| Reference | Exact evidence path | License stance | Observed behavior | Adopted first-party behavior | Rejected/copied |
|---|---|---|---|---|---|
| WorldMonitor | `worldmonitor-main/docs/map-engine.mdx`, `docs/maps-and-geocoding.mdx`, `src/config/map-layer-definitions.ts`, `e2e/map-harness.spec.ts`, `e2e/mobile-map-popup.spec.ts` | AGPL-3.0, behavior-only | map-first hierarchy, layer gates, mobile popup and harness evidence | large map, compact layer truth, mobile event inspector, renderer markers | no source, CSS, snapshots, styles, assets, data |
| WorldMonitor | `worldmonitor-main/src/components/MapContainer.ts`, `MapPopup.ts`, `map-popup-source-links.ts` | AGPL-3.0, behavior-only | selected marker context and source links | first-party selected-event source/provenance inspector | no implementation copied |
| worldview | `worldview-main/e2e/features/compare/compare-test.spec.js`, `compare/permalinks-test.spec.js`, `compare/timeline-test.spec.js` | NASA-1.3, behavior-only pending legal review | compare/timeline state and permalinks | URL-backed local compare/timeline state | no source, config, imagery, colormaps |
| worldview | `worldview-main/e2e/features/timeline/timeline-mobile-test.spec.js`, `timeline/date-selector-test.spec.js` | NASA-1.3, behavior-only | mobile timeline controls | responsive timeline strip | no source copied |
| osiris | `osiris-master/src/app/api/earthquakes/route.ts`, `api/flights/route.ts`, `components/LayerPanel.tsx`, `components/OsirisMap.tsx` | MIT but direct adaptation requires path notice review | earthquake/flight provider separation and layer composition | existing native USGS/OpenSky providers plus status-gated layers | no source copied; vendored dependencies blocked |
| Commercial map products | public Bloomberg/Google Earth/TradingView/Koyfin product behavior | proprietary behavior reference | dense context, selected object continuity, compact controls | first-party terminal density and persistent selected context | no branding, screenshots, data, icons, CSS |

The Phase 5F inventory mechanically covers the archive set. This ledger is a scoped semantic review for Phase 5H only and does not claim every external line is approved for reuse.
