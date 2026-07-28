# Phase 6G Next Goal Rationale

Updated: 2026-07-03

## Decision

Proceed with **Phase 6H: Synchronized Analyst Workspace**.

## Why

Phase 6G completes one daily review loop: refresh, compare, inspect evidence,
open the exact asset, and return. The strongest remaining visible product gap
is composition. Chart, technicals, fundamentals, catalysts/news, source ledger,
changes, map context, and command actions exist, but an analyst must traverse
separate one-panel routes.

Current OpenBB documentation emphasizes data source, metadata, visual,
parameters, and linked parameter behavior in each widget. Bloomberg-like value
also depends on dense, synchronized context. A clean-room workspace assembled
from our existing exact contracts improves real daily usefulness without adding
provider quota or another mock route.

## Deferred

- Always-on local service: machine-specific and not a B2C hosted model.
- Hosted auth/billing: premature before the composed product workflow is proven.
- More provider breadth: current evidence is not yet composed efficiently.
- External code/visual copying: unnecessary and legally unsafe where licenses
  are restrictive or unclear.

## Phase 6H Product Journey

```text
Change Inbox
-> open exact synchronized workspace
-> inspect chart + financial + catalyst/news + source/change panels together
-> change symbol/timeframe once and synchronize compatible panels
-> save local layout
-> open exact evidence/source
-> return to the same change inbox state
```

