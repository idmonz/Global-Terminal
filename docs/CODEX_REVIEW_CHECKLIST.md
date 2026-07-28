# Codex Review Checklist

## Product

- The intended user journey is complete and reachable.
- The first viewport shows the market object rather than diagnostics.
- URL state survives refresh and navigation.
- Loading, empty, unavailable, stale, and error states are useful.

## Data And API

- Provider/source URL/fetched time/freshness/caveat/data gap are present.
- Fixture/proxy/static data never appears live.
- Contracts are JSON-safe and additive.
- Runtime failure does not silently fabricate or mislabel data.

## Frontend

- Desktop and 390px mobile screenshots were inspected.
- Chart/map readiness and nonblank checks pass.
- No overlap, clipping, unreadable text, or broken focus order.
- Controls use appropriate icons, labels, and tooltips.

## Safety And Clean Room

- No advice, execution, order, position-sizing, or broker path.
- No secret, private path, user data, or unsafe HTML leakage.
- External source/assets/data have an exact adoption stance.

## Verification And Release

- Focused tests and full pytest pass.
- Web test, lint, build, runtime smoke, and audit pass.
- Release includes first-party harness/web/backend and excludes sensitive/external/generated artifacts.
- Final report lists failures and limitations honestly.
- Next goal follows the scorecard evidence.
