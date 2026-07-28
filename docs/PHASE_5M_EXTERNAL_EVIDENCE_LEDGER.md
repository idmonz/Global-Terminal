# Phase 5M External Evidence Ledger

## Adoption Stance

This phase uses external products only to define behavior and information hierarchy. Implementation is project-native Python, TypeScript, React, CSS, and existing permissive dependencies.

| Reference | Evidence | Stance | Adopted behavior | Not copied |
| --- | --- | --- | --- | --- |
| FinanceDatabase | `FinanceDatabase-main.zip`; top-level MIT evidence in `pyproject.toml`; equity/ETF/crypto header evidence recorded by Phase 2E | schema behavior; rows not imported | explicit asset-class identity, searchable fields, provider symbol concepts | CSV rows, descriptions, classifications, or bundled datasets |
| OpenBB | `OpenBB-develop.zip`; AGPL-3.0 | behavior-only | provider-aware command/search/result hierarchy | source, prompts, provider code, UI assets |
| OpenAlice | `OpenAlice-master.zip`; AGPL-3.0 | behavior-only | source-aware workspace behavior | source, CSS, assets, prompts |
| TradingView public product | public symbol search/chart behavior | behavior-only | exact identity, search ranking, interval/range control, chart-first hierarchy | CSS, screenshots, widgets beyond existing licensed chart library, data payloads |
| Finviz public product | public screener/quote behavior | behavior-only | discovery-to-symbol flow and compact identity/fundamental summary | page structure, CSS, datasets, screenshots |
| Bloomberg-like terminals | public product behavior and prior archive audit | behavior-only | dense identity/tape/source strip and keyboard-efficient navigation | brand, proprietary layouts, data, source, screenshots |
| BB-Terminal archive | license unclear in archive | blocked for direct use | command intent only from prior clean-room evidence | all source/assets |

## First-Party Acceptance Criteria

1. The registry is constructed from the existing reviewed local 60-row equity taxonomy plus a separately authored ETF list and public crypto pair conventions.
2. No external security-master row is imported.
3. Every registry row states its provenance and non-authoritative boundary.
4. Search, cache, runtime normalization, and UI are independently implemented.
5. Release tests reject `external (2)`, copied archive paths, private data, and secrets.

