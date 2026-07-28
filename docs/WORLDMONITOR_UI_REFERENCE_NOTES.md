# WorldMonitor UI Reference Notes

## Reference Scope

WorldMonitor is used as a design and intelligence-workflow reference only.

Concepts referenced:

- Command-center layout.
- News feed clustering.
- Source freshness badges.
- Intelligence severity badges.
- Event timelines.
- Event maps.
- Regional risk cards.
- Chokepoint maps.
- Infrastructure, shipping, and energy route proxy panels.
- AI intelligence brief structure.
- Multi-source signal fusion.
- Data layer toggles.

## Runtime Boundary

- No WorldMonitor TypeScript code is copied into runtime modules.
- `external/worldmonitor-main/` is ignored and reference-only.
- Runtime modules do not import from `external/`.
- Private or pro-gated WorldMonitor surfaces are not scraped.
- Optional adapter calls require explicit `WORLD_MONITOR_BASE_URL` and optional `WORLD_MONITOR_KEY`.

## Provider Caveats

- Live AIS and vessel flow are unavailable without a real AIS provider.
- Route intelligence is optional and may be unavailable or pro-gated.
- Static chokepoint and route maps are proxy estimates.
- News severity, region, and impact classifications are heuristic.
