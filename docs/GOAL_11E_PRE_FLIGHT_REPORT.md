# Goal 11E Pre-Flight Report

## Baseline

Working baseline: Goal 11D release ZIP uploaded by the user.

## Commands run before implementation

```text
python -m compileall -q app.py lib pages scripts tests -> PASS
python scripts/run_smoke_tests.py -> PASS
python -m pytest -q -> PASS
python scripts/build_release_zip.py -> PASS
```

## File counts before Goal 11E patching

- Project files inspected/available: 835
- Python files: 634

## Current Goal 11D limitations identified

| Area | Limitation | Goal 11E response |
|---|---|---|
| Command safety | Some descriptive macro/market-structure phrases were over-blocked. | Context-aware command safety false-positive patch. |
| Direct actions | Direct watchlist add could surface an exception-style result for blocked intent. | Shared safety boundary inside workflow action layer. |
| Alerts | Manual alert evaluation action did not call Alert Engine V2 when context was supplied. | Manual Alert Engine V2 wiring with skipped-data caveats. |
| Energy brief | Energy brief used a War Room type. | Distinct `energy_geopolitics` report type. |
| Tool Center | Some cards had no action mapping. | Safe dry-run/inspect workflow actions or explicit disabled route semantics. |
| Selected state | Report/strategy selection needed stronger persistence through review updates. | Session-state-aware selected payloads and refresh semantics. |
| Rendering | Some paths escaped entire Markdown too aggressively. | Markdown-readable, HTML-safe render helpers. |

## Command safety false-positive matrix

Allowed research terms to preserve: long-term Treasury, short-term rates, order flow, orderflow, long duration, short duration, limit order book, order book depth, taker ratio terms, ratio and interest terms.

Blocked intent classes to retain: direct market action intent, directional action intent, market-order intent, route/execution intent.

## Workflow action gap matrix

| Action | Pre-Goal11E state | Goal11E target |
|---|---|---|
| ADD_WATCHLIST_ITEM | Partial safety through palette only | Direct action safety check and clean blocked card |
| EVALUATE_ALERTS_NOW | Placeholder | Alert Engine V2 with supplied context; skipped if context missing |
| GENERATE_ENERGY_BRIEF | War Room type | Energy-specific report type |
| Provider/Data/Release tools | Static/partial | Safe dry-run or inspection actions |

## Release hygiene status

The baseline release build passed and excluded external/private/secrets/cache/generated runtime artifacts. Goal 11E retains the same exclusion model.

## Scope boundary

Goal 11E will not implement Goal 12, broker connectivity, background daemons, external source trees, external runtime dependencies, live execution, or autonomous agents.
