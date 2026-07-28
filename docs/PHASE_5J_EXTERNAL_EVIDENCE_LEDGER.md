# Phase 5J External Evidence Ledger

Updated: 2026-06-21

| Reference | Exact evidence | License stance | Observed behavior | Adopted clean-room behavior | Rejected |
|---|---|---|---|---|---|
| OpenBB | `review_workspace/external2_analysis/unzipped/OpenBB-develop/OpenBB-develop/openbb_platform/core/openbb_core/provider/standard_models/options_chains.py` | AGPL-3.0, behavior-only | Provider-neutral row model, expiries/strikes, OI/volume/IV/Greeks availability | First-party JSON row contract and capability-gated views | No Pydantic definitions, properties, source, or text copied |
| OpenBB yfinance | `.../providers/yfinance/openbb_yfinance/models/options_chains.py` | AGPL-3.0, behavior-only | Alias normalization, separate underlying metadata, expiry/DTE context | First-party mapper over the repository's existing yfinance dependency | No fetcher/source copied; no missing values replaced with zero |
| OpenAlice | `OpenAlice-master/LICENSE`, `packages/opentypebb/src/standard-models/options-chains.ts`, `providers/yfinance/models/options-chains.ts` | AGPL-3.0, behavior-only | TypeScript provider/model separation | Python provider boundary plus TypeScript consumer contract | No source or types copied |
| BB-Terminal | `review_workspace/external2_analysis/unzipped/BB-Terminal-main/BB-Terminal-main/README.md` | No clear archive license; behavior-only | OMON full-screen calls/strike/puts and keyboard command | Dense chain hierarchy and OMON navigation concept | No source, CSS, screenshot, signal rules, or wording copied |
| bloomberg-terminal | `.../components/bloomberg/views/volatility-view.tsx`, archive README | README says MIT but full archive LICENSE absent; behavior-only | Dense sortable volatility table and compact filters | Dense first-party volatility/Greeks table and segmented analysis modes | Randomly generated IV/HV values explicitly rejected |
| optlib | `optlib-master/LICENSE`, `optlib/gbs.py`, `tests/test_gbs.py` | MIT; direct adaptation possible after notice review | Generalized Black-Scholes family and numerical validation cases | Existing project-native pricing/Greek modules retained | No optlib code or tests copied |

## Acceptance Boundary

Implementation is first-party Python, TypeScript, React, SVG, and CSS. External projects supply behavior and validation questions only. Runtime market rows come from the existing yfinance dependency and are subject to its terms; deterministic fixture rows are project-owned test data.
