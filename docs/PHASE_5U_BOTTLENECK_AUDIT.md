# Phase 5U Bottleneck Audit

Updated: 2026-06-30

## Scope

Phase 5U responds to the visible product complaint that `/?view=war-room-map` had real map/contracts underneath, but still did not feel like a WorldMonitor/worldview-style operating surface. The goal was not another hidden contract. It was first-viewport usefulness.

## Before-State Findings

Visual baseline used local Chrome plus repository `playwright-core` because the in-app browser connector was unavailable.

| Route | Before-state evidence | Root cause | Required correction |
|---|---:|---|---|
| `/?view=war-room-map&mode=cache` desktop | Map started around `576px` from the top of the viewport | Product header, runtime banner, replay deck, timeline and diff strip all rendered before the map | Move map above detailed replay controls and keep only compact source/replay truth before it |
| `/?view=war-room-map&mode=fixture` desktop | Map started around `585px` | Same layout problem in deterministic mode | Same correction without weakening fixture labels |
| `/?view=war-room-map&mode=cache` mobile | Map started around `947px` | Mobile header and replay controls pushed the map below first working view | Compact mobile title/source/replay controls |
| `/?view=news&mode=fixture` | News route had story rows after 5T | Link context existed separately from map | Keep map selected-event panel wired to related reporting and market transmission |

## Implemented Fix

The War Map route now keeps source truth and replay controls, but orders the first viewport around the map:

1. Compact product header with source-backed/static/gap counts.
2. Compact source boundary strip.
3. Compact operations toolbar with active/compare/truth clocks.
4. Leaflet/fallback map with layer controls and event inspector.
5. Detailed replay timeline, diff strip, and full runtime banner below the map.

## After-State Evidence

Final visual harness: `npm.cmd --prefix apps/web run visual:phase5u`

| Route | Map top | Map state | Markers | Layers | Inspector | Event rows | Related reporting | Market links | Overflow/errors |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| Cache desktop | `391px` | `ready` | 2 | 12 | 1 | 2 | 1 | 7 | none |
| Fixture desktop | `391px` | `ready` | 2 | 1 | 1 | 2 | 0 | 0 | none |
| Fallback desktop | `391px` | `fallback` | 2 | 1 | 1 | 2 | 0 | 0 | none |
| Cache mobile | `550px` | `ready` | 2 | 12 | 1 | 2 | 1 | 7 | none |
| Fixture mobile | `550px` | `ready` | 2 | 1 | 1 | 2 | 0 | 0 | none |

## Verdict

Phase 5U closes the immediate first-viewport War Map layout defect. It does not complete WorldMonitor/worldview parity: broad live provider layers, verified flight/AIS/sanctions, richer weather/satellite overlays, larger live event density, hosted snapshots, and multi-monitor terminal composition remain future work.

Outputs remain research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, autonomous monitoring, or execution instructions.
