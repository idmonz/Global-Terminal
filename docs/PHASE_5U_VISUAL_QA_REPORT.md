# Phase 5U Visual QA Report

Updated: 2026-06-30

## Method

The in-app Browser connector was unavailable in this session. Visual QA used repository `playwright-core` with local Chrome against production Next.js at:

```text
http://127.0.0.1:3000
```

Command:

```powershell
npm.cmd --prefix apps/web run visual:phase5u
```

## Captures

Final evidence is stored under `review_workspace/phase5u_final/`:

- `war-map-cache-desktop.png`
- `war-map-fixture-desktop.png`
- `war-map-fallback-desktop.png`
- `news-fixture-desktop.png`
- `war-map-cache-mobile.png`
- `war-map-fixture-mobile.png`
- `summary.json`

## Result Summary

- Browser console errors: 0
- Page errors: 0
- Horizontal overflow: false on captured routes
- Contract diagnostics text: false on captured product routes

| Route | Map top | State | Markers | Tiles | Source strip | Ops toolbar | Layer rows | Inspector | Event rows |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| Cache desktop | 391 | ready | 2 | 15 | 1 | 1 | 12 | 1 | 2 |
| Fixture desktop | 391 | ready | 2 | 20 | 1 | 1 | 1 | 1 | 2 |
| Fallback desktop | 391 | fallback | 2 | 0 | 1 | 1 | 1 | 1 | 2 |
| Cache mobile | 550 | ready | 2 | 10 | 1 | 1 | 12 | 1 | 2 |
| Fixture mobile | 550 | ready | 2 | 9 | 1 | 1 | 1 | 1 | 2 |

## Manual Inspection Notes

- Desktop now shows the map, layer overlay, event inspector, source boundary and compact replay clocks in the first working viewport.
- Mobile now reaches the map in the first viewport and avoids horizontal overflow.
- The cache route shows related reporting and market-transmission links when the selected event has them.
- The fallback route clearly uses deterministic fallback rendering and does not claim live tiles.
- Detailed timeline and diff controls remain available below the map rather than blocking it.

## Remaining Visual Gaps

- Map data density is still low in fixture/cache captures compared with WorldMonitor examples.
- There is not yet a true multi-monitor terminal layout with detachable panels.
- Weather, AIS, verified flight, sanctions and satellite-style layers remain unavailable or proxy/static unless a provider fetch is verified.

Outputs remain research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, autonomous monitoring, or execution instructions.
