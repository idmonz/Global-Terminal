# Phase 5Y Implementation Report

Updated: 2026-07-01

## Verdict

Phase 5Y improved real map intelligence, not only layout or fixture fallback.

The commercial Next.js War Map now joins current runtime markers, a complete normalized
news set, bounded event relationships, market transmission context, and direct
source evidence. It also remains usable and truthful when FastAPI is unreachable.

This is a strong internal-beta slice. It is not WorldMonitor/worldview parity:
verified flight, AIS, sanctions, broad weather/infrastructure layers, durable hosted
history, and low-latency background refresh are still absent.

## User Journey Delivered

```text
War Map
-> inspect prioritized current event
-> verify provider, coordinate method, freshness and caveat
-> inspect directly matched reporting or an explicit no-match state
-> inspect bounded transmission paths and related assets
-> open the source-backed News desk or a supported symbol workstation
-> return to the selected map event with URL state preserved
```

## Runtime And Contract Changes

- `lib/war_room_map.py`
  - derives a broad display region from source coordinates only when a provider does
    not supply a useful region;
  - labels the method as `coordinate-derived-broad-region`;
  - retains the original provider coordinate method and source status.
- `lib/map_news_event_fusion.py`
  - advances the contract to `map_news_event_fusion.v2`;
  - exposes the complete deduplicated normalized news set;
  - creates an `event_contexts` row for every map marker;
  - supports source URL, exact title, specific provider region and bounded
    domain-keyword matching;
  - forbids coordinate-derived broad regions as news-match evidence;
  - restricts graph links to edges directly touching the selected event;
  - marks contextual links as non-causal research context.
- `apps/web/src/components/LeafletWarMap.tsx`
  - adds a prioritized event focus rail;
  - renders related reporting, explicit no-match state, transmission path and
    connected assets in the inspector;
  - preserves map state with `window.history.replaceState`, avoiding a live-provider
    server refresh on every map click;
  - preserves War Map origin state in supported asset links.
- `apps/web/src/components/WarMapReplayWorkspace.tsx`
  - defaults to the current map;
  - enters replay only when an explicit snapshot time is selected.
- `apps/web/src/app/page.tsx`
  - consumes current `event_contexts`;
  - reports marker-derived source-backed counts;
  - treats both `fresh` and `live/fresh` news rows as source-backed.
- `apps/web/scripts/capture-phase5y.mjs`
  - proves online/offline desktop and mobile behavior, event selection, News
    continuity, AAPL return navigation, map readiness and explicit no-news actions.

## Truth And Safety

- A USGS event is not assigned unrelated news merely because both fall inside a broad
  derived region.
- A chokepoint row is not linked to generic energy reporting without a logistics
  term such as shipping, tanker, freight, canal, strait or port.
- No related reporting produces a visible source-backed News action instead of
  invented context.
- Static chokepoints remain fixture/proxy rows.
- Credentials or configured layers without successful rows are not called live.
- Outputs remain research context, not causal proof, surveillance, military
  targeting, advice, hedging instructions or execution.

## Observed Final Runtime

Observed on 2026-07-01; counts are time and provider dependent:

- runtime: online;
- map markers/events: 37;
- source-backed markers: 29;
- prioritized event buttons: 5;
- normalized News workspace rows: 40, with 41 visible news UI rows including the
  selected/detail surface;
- default event: current USGS M6.0 Mexico earthquake;
- direct matched reporting for that event: 0, shown honestly;
- explicit News desk action for the no-match state: present;
- browser console/page errors: 0.

Controlled offline evidence:

- runtime: offline;
- runtime fallback: explicit;
- fixture/proxy map events: 2;
- source-backed markers: 0;
- map, event inspector, News route, AAPL chart and return action remained usable.

## Performance Finding

Map event selection is now immediate because it no longer triggers a server/provider
reload. However, a cold `include_runtime=true` map fusion request was observed taking
roughly 70-80 seconds while waiting across the live provider set. This is the primary
runtime bottleneck carried forward: provider-specific deadlines, broader concurrent
fetching, background refresh and materialized current-state reads are needed.

## Main Files

- `lib/war_room_map.py`
- `lib/map_news_event_fusion.py`
- `apps/web/src/components/LeafletWarMap.tsx`
- `apps/web/src/components/WarMapReplayWorkspace.tsx`
- `apps/web/src/components/SymbolWorkstation.tsx`
- `apps/web/src/lib/product-routes.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/scripts/capture-phase5y.mjs`
- `tests/test_map_news_event_fusion_contracts.py`
- `tests/test_war_room_map_contracts.py`
- `tests/test_phase5h_global_risk_map.py`
- `tests/test_phase5u_map_first_war_room.py`
- `tests/test_phase5t_options_news_product_depth.py`

