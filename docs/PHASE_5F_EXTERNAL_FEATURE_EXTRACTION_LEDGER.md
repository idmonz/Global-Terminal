# Phase 5F External Feature Extraction Ledger

Updated: 2026-06-19

## Audit Coverage

- 19 archives inspected
- 40,932 file entries indexed
- 30,403 text/code candidates
- 7,968,399 total text/code lines counted
- 170,395 symbols extracted
- 0 read errors
- 35 large files used full line counting with prefix-only symbol extraction
- 600 vendored files identified
- root `external.zip` classified as a duplicate container and not double-counted

This is exhaustive mechanical inventory, not a claim that a human semantically reviewed every line. Adoption candidates below received manual spot review; any direct source adoption still requires exact-path review.

| Project | Extracted product idea | Evidence example | Adoption decision | First-party target |
|---|---|---|---|---|
| agent-skills | gated spec, plan, implementation, verification lifecycle | required `SKILL.md` set | adopt workflow | docs and repo skill |
| BB-Terminal | command mnemonic and dense terminal navigation | archive UI/command files | clean-room behavior | terminal command router |
| bloomberg-terminal | compact multi-panel market workstation | README/UI evidence | clean-room behavior | web shell |
| dexter | research-agent orchestration and source presentation | README evidence | clean-room behavior | research assistant boundary |
| FinanceDatabase | asset classes, taxonomy, search/filter, option discovery | README lines 13-20, 60-392 | schema behavior; no bulk row copy | asset universe/screener |
| helix-db | typed nodes/edges and graph query model | README | clean-room graph concepts | event-asset graph |
| Kronos | OHLCV tokenization and probabilistic forecast research | README lines 61-170 | future optional research plugin | model lab |
| open-design | audit-first redesign, design dials, preflight, responsive QA | taste/redesign skills | adopt process, not templates | design system/visual QA |
| OpenAlice | staged research actions and guard pipeline | README | behavior only, no execution | actionless research workflow |
| OpenBB | provider hierarchy, command routes, context, metadata | `command_runner.py` lines 34-645 | behavior only | API/provider contracts |
| OpenStock | stock discovery, analysis, and portfolio surface ideas | README | behavior only | symbol/screener views |
| optlib | option chain schema, pricing models, implied volatility | README lines 53-180 | formulas only after validation | options quant |
| osiris | flight, earthquake, conflict, CCTV, news layer composition | README | selective MIT-informed behavior | war room providers |
| quant-traderr-lab | quantitative diagnostics/workbench patterns | archive modules | selected validated methods | quant lab |
| QuantDinger | backend API and MCP service boundaries | README/backend/mcp | selective Apache-informed architecture | optional tool API |
| supabase | auth/database/realtime/storage product architecture | README and apps | official-service integration later | persistence/account layer |
| tensortrade | composable research environments and evaluation | README/examples | concepts only; no autonomous execution | simulation lab |
| worldmonitor | 500+ feeds, dual map engine, 56 layers, finance radar, source freshness | README lines 38-50, 94-117; map docs | behavior only | map/news/provider surfaces |
| worldview | compare, timeline, layer opacity and map-state behavior | compare components/e2e specs | behavior only | map compare controls |

## Gold Quant Report Extraction

The 1,505-line user-provided Gold Quant report is a research requirements source, not executable trading logic. Safe concepts include:

- source timestamps and missing-data disclosure;
- futures/OI/curve context;
- option chain, IV/RV, skew, term structure, and GEX inputs;
- explicit distinction between observed data, assumptions, and proxies;
- macro, news, event calendar, technical, cross-asset, scenario, and confidence sections;
- limitations register and data source register.

Excluded from the product boundary:

- trade permission;
- recommended leverage;
- entry, stop, target, liquidation, or execution instructions;
- autonomous directional calls;
- broker/order actions.

Those fields may only be reformulated as neutral historical scenario inputs or risk education, never as personalized recommendations.

## Immediate Safe Adoption Queue

1. FinanceDatabase-style filter vocabulary using native schema and provider-backed rows.
2. WorldMonitor/worldview-style map/news/timeline behavior via first-party implementation.
3. OpenBB-style provider metadata and command contexts via current API contracts.
4. open-design audit and visual preflight as a repeatable repo skill.
5. optlib-informed formula test vectors only after numerical validation and attribution review.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
