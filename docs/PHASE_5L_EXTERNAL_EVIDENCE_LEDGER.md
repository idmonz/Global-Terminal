# Phase 5L External Evidence Ledger

Updated: 2026-06-22

## Scope

The prior archive inventory and license matrix were reused, followed by a scoped semantic read of research/workspace/watchlist/storage paths. Mechanical inventory is not treated as semantic review of every line.

| Reference | Evidence | Adoption | Boundary |
|---|---|---|---|
| OpenBB / OpenAlice | workspace, source-aware panels, saved research hierarchy | behavior-only | AGPL; no code, CSS or assets copied |
| BB-Terminal | command/workspace hierarchy | behavior-only | archive license uncertainty remains blocked |
| Supabase | migration, row-oriented persistence and future auth separation concepts | architecture-only | no hosted auth, client, cloud sync or copied Studio code |
| Dexter | research-agent memory concepts | behavior-only | no private context is sent to an external model |
| Bloomberg / Koyfin / TradingView public product behavior | compact watchlist, source history and return-to-origin hierarchy | clean-room behavior | no proprietary datasets, screenshots, brand assets or CSS |
| Existing Streamlit research OS | watchlist, reports, source caveats, review workflow | direct project-native reuse | internal project code |

## Clean-Room Decision

Phase 5L is implemented with project-native Python, SQLite and React. External references informed hierarchy and workflow only. No external source, prompt, visual asset, telemetry implementation or dataset was copied.

## Deferred

Supabase hosted persistence/auth, external vector search, AI summarization, cloud synchronization and delivery notifications remain out of scope until a later commercial-platform phase with explicit privacy, tenancy and entitlement design.

