# Goal 11E Workflow Action Patch

## Direct action safety

`ADD_WATCHLIST_ITEM` now invokes the shared research command safety boundary. A forbidden direct payload returns a clean blocked result with safe alternatives and performs no DB mutation.

## Alert evaluation

`EVALUATE_ALERTS_NOW` now uses Alert Engine V2 when supplied rule/context data exists. Missing context returns a skipped/unavailable result with explicit caveats. No synthetic trigger is created.

## Tool actions

New safe manual actions:

- `RUN_PROVIDER_PROBE_DRY_RUN`
- `INSPECT_DATA_QUALITY`
- `BUILD_WAR_ROOM_CONTEXT`
- `INSPECT_VIEW_PRESETS`
- `INSPECT_RELEASE_HYGIENE`

These actions are dry-run or inspection payloads only.
