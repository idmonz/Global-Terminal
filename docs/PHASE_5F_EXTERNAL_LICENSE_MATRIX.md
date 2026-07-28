# Phase 5F External License Matrix

Updated: 2026-06-19

This matrix governs source adoption from `external (2)/external`. A repository-level license does not automatically clear every vendored subdirectory, dataset, model, font, image, or dependency. Direct reuse requires exact-path review and notice retention.

| Project/archive | Detected evidence | Product stance | Direct source use |
|---|---|---|---|
| agent-skills | MIT | workflow instructions may be adapted with notice | allowed after path review |
| BB-Terminal | no clear archive license | behavior reference only | blocked |
| bloomberg-terminal | MIT stated in README, full archive license absent | behavior reference; legal review for source | needs review |
| dexter | MIT stated in README, full archive license absent | behavior reference; legal review for source | needs review |
| FinanceDatabase | MIT | taxonomy/schema concepts; avoid bulk dataset copy by default | allowed after path/data review |
| helix-db | Apache root with AGPL subcomponent evidence | graph concepts only until path isolation | needs review |
| Kronos | MIT | optional model research only; model weights/terms reviewed separately | allowed after model review |
| open-design | Apache-2.0 root, mixed template notices | design process and rubrics; no blind asset/template import | allowed after path review |
| OpenAlice | AGPL-3.0 | behavior only | no |
| OpenBB | AGPL-3.0 repository, mixed nested evidence | provider/workflow behavior only in proprietary boundary | no |
| OpenStock | AGPL-3.0 | behavior only | no |
| optlib | MIT | formulas/tests may inform native implementation with attribution | allowed after path review |
| osiris | MIT | selected provider/map patterns may be adapted with notice | allowed after path review |
| quant-traderr-lab | MIT | selected quantitative methods may be adapted with validation | allowed after path review |
| QuantDinger | Apache-2.0 | API/MCP architecture patterns may be adapted | allowed after path review |
| supabase | Apache-2.0 root, mixed examples/dependencies | persistence architecture reference; prefer official client packages | allowed after path review |
| tensortrade | Apache-2.0 | research environment concepts only; no autonomous trading path | allowed after path review |
| worldmonitor | AGPL-3.0 | behavior and public documentation evidence only | no |
| worldview | NASA Open Source Agreement 1.3 | behavior only pending legal review | no |

## Non-Code Assets

- The five benchmark screenshots are user-supplied reference evidence and are not product assets.
- External CSV rows, map textures, logos, fonts, screenshots, icons, and model weights are not cleared merely because neighboring source is permissive.
- TradingView, Finviz, Bloomberg, OpenBB, WorldMonitor, and NASA names are benchmark references, not implied endorsements.

## License Gate

Before direct adoption, record:

1. archive and exact path;
2. governing license and nested notices;
3. copied or adapted lines/assets;
4. attribution/NOTICE requirements;
5. dataset or model terms;
6. security and dependency review;
7. target first-party module and tests.

When any item is unresolved, implement clean-room behavior from public specifications and observed product behavior instead.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
