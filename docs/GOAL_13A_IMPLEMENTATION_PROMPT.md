# Goal 13A Implementation Prompt

Use this prompt to continue the existing Global Market Analyst Terminal project into Goal 13A.

````text
/goal
You are Codex operating as an implementation engineer, release-gate fixer, regression auditor, and model-governance safety reviewer for the existing "Global Market Analyst Terminal" project.

MISSION
Implement Goal 13A: Action-less Simulation Case System & Model Artifact Governance.

This is a Goal 13A implementation task only.
Do not implement Goal 13B, Goal 14, autonomous trading, live execution, broker integration, RL execution, external model inference, or any action-taking system.

ACTIVE DEVELOPMENT WORKSPACE
Use the current working directory as the active development workspace.
It is the "Global Macro + Equity + Crypto + Commodity + Geopolitical Risk Terminal" project folder on the user's Desktop.

IMPORTANT BASELINE
The workspace should already be at the Goal 12E repackaged hotfix baseline.
Before writing code, inspect and preserve the existing Goal 12E behavior, especially:

- docs/GOAL_12E_REPACKAGED_HOTFIX_REPORT.md
- docs/GOAL_13_ACTIONLESS_SIMULATION_ARCHITECTURE_PREP.md
- docs/EXTERNAL_REFERENCE_GOAL_BY_GOAL_ADOPTION_PLAN.md
- docs/GOAL_12E_EXTERNAL_REFERENCE_RESEARCH_REPORT.md
- docs/GOAL_12D_EXTERNAL_REFERENCE_RESEARCH_REPORT.md
- release_manifest.json
- scripts/build_release_zip.py
- scripts/cleanup_release_artifacts.py
- lib/options_research_case_store.py
- lib/options_research_case_index.py
- lib/options_surface_review_store.py
- lib/options_research_case_workflow.py
- lib/options_lab_workflow_actions.py
- lib/options_lab_page_layout.py
- lib/options_strategy_commit_bridge.py
- lib/quant_model_snapshot_schema.py
- lib/quant_model_registry.py
- lib/quant_model_lab.py
- lib/research_artifact_store.py
- lib/research_workspace_db.py
- tests/test_goal12e_options_case_workflow_actions.py
- tests/test_goal12e_release_hygiene.py

INPUT REFERENCE ARTIFACTS

- user Downloads/global_market_terminal_goal12e_repackaged_hotfix.zip
- user Downloads/global_market_terminal_goal12e_inspected_hotfix.zip
- workspace root\external (2).zip
- workspace root\external.zip

WORKING METHOD
Follow the agent-skills workflow found inside external (2).zip, especially external/agent-skills-main.zip.
Use it as a strong workflow reference, including its lifecycle logic, checklist structure, task decomposition style, and review gates.
You may adapt the workflow logic into this project in project-native wording and structure.

Required workflow:

1. DEFINE
   - Read the current Goal 12E/Goal 13 prep docs.
   - Define the exact Goal 13A acceptance criteria.
   - Keep the system local, private, research-only, and action-less.

2. PLAN
   - Create or update a Goal 13A plan/spec document before broad implementation.
   - Break the work into testable vertical slices.

3. BUILD
   - Prefer test-first or test-near development.
   - Reuse the existing Goal 12D/12E patterns for private case storage, redacted exports, workflow actions, page payloads, Strategy-as-Git artifacts, and release hygiene.
   - Use small, focused modules instead of a large new framework.

4. VERIFY
   - Run focused Goal 13A tests.
   - Run existing Goal 12D/12E regression tests.
   - Run compile, smoke, collect-only, and full pytest before final packaging.

5. REVIEW
   - Perform a code review, model-governance review, security review, release-hygiene review, and regression audit.

6. SHIP
   - Rebuild the release ZIP.
   - Inspect the ZIP contents and manifest.
   - Write final Goal 13A reports with a clear go/no-go result.

EXTERNAL REFERENCE RESEARCH REQUIREMENTS
Inspect external (2).zip thoroughly enough to understand the relevant implementation logic, not just high-level concepts.
You may use external projects as research references for control flow, state machines, schema shape, validation logic, queue/idempotency semantics, review lifecycles, artifact governance, and test patterns.

Copyright and license handling is mandatory:

- Before adapting any external logic, inspect the exact LICENSE, NOTICE, COPYING, COPYRIGHT, and package metadata for that source.
- Create docs/GOAL_13A_EXTERNAL_LICENSE_AUDIT.md with a source-by-source matrix: source path, license, observed copyright notices, logic studied, code copied or not copied, attribution required, compatibility decision, and risk notes.
- Prefer clean-room, project-native reimplementation of logic. This means studying behavior and structure, then writing new code that fits this repo's existing modules and tests.
- Do not paste large verbatim code blocks from any external project.
- Do not copy files, source trees, dependency lockfiles, vendored packages, generated assets, model weights, checkpoints, or notebooks from external projects.
- If a small direct code excerpt is ever justified from MIT or Apache-2.0 material, it must be minimal, attributed, covered by retained notices, documented in the license audit, and added only if it is clearly compatible with this release. Prefer avoiding this.
- For AGPL, unknown-license, no-license, mixed-license, or NASA Open Source Agreement material, do not copy code. Use behavior-only analysis and independent reimplementation unless the user explicitly approves a separate license-compliance plan.
- If license status is unclear, treat the source as "research only, no code copying".
- This is not legal advice; record the engineering license audit and residual risk transparently.

Known external reference contents to study:

- agent-skills-main.zip
  - Observed license: MIT.
  - Study and adapt DEFINE, PLAN, BUILD, VERIFY, REVIEW, SHIP workflow logic.
  - Reuse the process model, checklist sequencing, spec-driven planning, TDD loop, review workflow, and ship gates in project-native documentation and automation.

- tensortrade-master.zip
  - Observed license: Apache-2.0.
  - Study its data feed, environment/scenario, action, observer, and modular domain boundaries in detail.
  - Adapt the separation logic into an action-less simulation schema and validator design.
  - For Goal 13A, remove all action execution, RL training, agents, exchange execution, reward optimization, and trading control.

- QuantDinger-main.zip
  - Observed license: Apache-2.0.
  - Study lifecycle, review state, backtest-limit, strategy-review, workflow, and guardrail logic.
  - Adapt the review and limit-checking logic into local, action-less simulation governance.
  - Do not add broker/API execution, autonomous agent runtime, or direct copied source without license-audit approval.

- Kronos-master.zip
  - Observed license: MIT.
  - Study model artifact metadata, forecast provenance, caveats, model-card-like records, and data preparation expectations.
  - Adapt metadata and governance logic into local model artifact cards.
  - Do not add model weights, checkpoints, Torch/Hugging Face runtime dependencies, inference calls, or external model execution.

- OpenAlice-master.zip
  - Observed license: AGPL-3.0.
  - Study review queue behavior, artifact workflow, tool audit flow, and thesis/build discipline.
  - Reimplement independently from behavior and docs only.
  - Do not copy AGPL code or introduce OpenAlice runtime.

- worldmonitor-main.zip
  - Observed license: AGPL-3.0-only.
  - Study simulation package logic, status transitions, run-id validation, idempotency, queue parity tests, and package-pointer design.
  - Reimplement local Goal 13A equivalents independently from behavior and tests.
  - Keep implementation local and synchronous unless the existing app has a clear local pattern.
  - Do not add a server, Redis queue, worker daemon, background job runner, API endpoint, or external service dependency.

- OpenBB-develop.zip, BB-Terminal-main.zip, bloomberg-terminal-main.zip, OpenStock-main.zip, optlib-master.zip, osiris-master.zip, quant-traderr-lab-main.zip
  - Observed licenses include mixed AGPL/MIT/no-license/unknown/MIT families depending on the exact project and subdirectory.
  - Study naming, validation, option-domain logic, terminal UX flows, artifact governance, error handling, and test patterns where useful.
  - Use MIT/Apache logic more freely as research reference after recording license status.
  - Treat AGPL, unknown-license, no-license, and mixed-license areas as behavior-only references with no copied code.
  - Do not add paid provider requirements, vendor SDK assumptions, external service dependencies, or vendored code.

WEB RESEARCH REQUIREMENTS
Use web search for current authoritative governance references before implementation. Prefer primary sources.
Use these sources as design inspiration and cite them in Goal 13A docs:

- NIST AI Risk Management Framework:
  https://www.nist.gov/itl/ai-risk-management-framework
- NIST AIRC AI RMF Core functions:
  https://airc.nist.gov/airmf-resources/airmf/
- Model Cards for Model Reporting:
  https://arxiv.org/abs/1810.03993
- Datasheets for Datasets:
  https://arxiv.org/abs/1803.09010
- MLflow Model Registry concepts:
  https://mlflow.org/docs/latest/ml/model-registry/

Use these references to shape Goal 13A around:

- Govern, Map, Measure, Manage style governance.
- Model card fields: intended use, limitations, evaluation, caveats, provenance.
- Datasheet fields: dataset/data-feed motivation, composition, collection/generation, preprocessing, limitations, recommended use.
- Model registry fields: model name, version, lineage, aliases/tags, lifecycle status, review state, artifact pointer, metadata.

STRICT SAFETY AND SCOPE BOUNDARIES
Goal 13A must remain action-less.

Forbidden:

- Broker execution, order routing, order preview, one-click trade, paper trading, live trading, or simulated trading controls that resemble execution.
- Autonomous trading, strategy deployment, portfolio rebalancing instructions, hedging instructions, position-sizing recommendations, or trade recommendation language.
- RL agent runtime, TensorTrade runtime, reward optimization, exchange execution, model training loop, or policy execution.
- Kronos or external model inference, downloaded weights, checkpoints, model files, GPU dependencies, or heavy ML dependencies.
- OpenBB, Bloomberg, broker, or paid-provider hard dependencies.
- API server, worker daemon, Redis queue, external queue, background scheduler, webhook, or service integration.
- Copying external source trees, vendored dependencies, generated assets, or license-sensitive code into the repo without a documented license audit, attribution, and explicit compatibility decision.
- Packaging .env, private data, generated case databases, caches, logs, notebooks, model weights, checkpoints, or local external ZIPs.
- Absolute local path leakage in release manifests, exported case JSON, reports, or ZIP contents.
- Fake claims of live data, real predictions, investment advice, or execution readiness.

Required language posture:

- Use "research-only", "action-less", "simulation case", "scenario", "artifact", "diagnostic", "governance record", and "not investment advice".
- Avoid "buy", "sell", "execute", "trade now", "rebalance now", "deploy strategy", "order", "signal to trade", or similar action language except in negative safety checks.

GOAL 13A PRODUCT OBJECTIVE
Build a local/private Action-less Simulation Case System that lets the app package research scenarios, option/market snapshots, model artifact metadata, diagnostics, caveats, review states, and report/strategy-commit attachments without enabling any trading action.

The feature should feel like a natural continuation of the existing Goal 12D/12E Options Lab and research case system.

Core capabilities:

1. Simulation Case Schema
   - Define a deterministic schema for action-less simulation cases.
   - Include case id, title, objective, created/updated timestamps, status, source context, linked options case ids, linked strategy commit ids, scenario ids, feed snapshot ids, model artifact ids, diagnostics ids, review ids, caveats, notices, and research-only flags.
   - Validate safe ids and block unsafe paths.
   - Validate action-less wording.

2. Scenario Set Schema
   - Represent what-if scenarios and assumptions.
   - Include horizon, asset universe, macro/geopolitical assumptions, volatility assumptions, options-surface references, stress parameters, and caveats.
   - Keep all scenarios descriptive and non-prescriptive.

3. Data Feed Snapshot / Datasheet Schema
   - Create a local datasheet-like record for feed snapshots.
   - Include data source label, generation time, coverage, fields, transformations, freshness, limitations, missingness notes, privacy notes, and intended research use.
   - Never require live external providers.

4. Model Artifact Governance
   - Create a model artifact card or governance record schema.
   - Include model id, model name, category, version, lifecycle status, intended use, prohibited use, input assumptions, output type, evaluation summary, caveats, source references, artifact URI, lineage, owner/reviewer fields, review status, tags/aliases, and research-only notice.
   - Reuse or extend lib/quant_model_snapshot_schema.py and lib/quant_model_registry.py where appropriate.
   - Kronos/TensorTrade/QuantDinger references must be represented as metadata-only placeholders unless already represented by the current code.

5. Simulation Result Artifact
   - Store deterministic local result summaries and diagnostics.
   - Include scenario id, model artifact id, input snapshot id, metrics, warnings, limitations, generated_at, provenance, and research-only notices.
   - Do not run external model inference.

6. Private Store and Redacted Export
   - Add a private JSON or SQLite-backed store using existing project patterns.
   - Suggested module names:
     - lib/actionless_simulation_schema.py
     - lib/actionless_simulation_store.py
     - lib/actionless_simulation_index.py
     - lib/model_artifact_governance.py
   - Store private artifacts under data/private or the existing private research workspace pattern.
   - Export redacted case bundles without private paths, .env values, secrets, or absolute local paths.

7. Workflow Actions
   - Add action-less workflow actions through the existing local action router pattern.
   - Suggested module:
     - lib/actionless_simulation_workflow.py
   - Integrate with lib/options_lab_workflow_actions.py only as needed.
   - Suggested actions:
     - CREATE_SIMULATION_CASE
     - UPDATE_SIMULATION_CASE
     - SAVE_SCENARIO_SET
     - SAVE_DATA_FEED_SNAPSHOT
     - SAVE_MODEL_ARTIFACT_CARD
     - SAVE_SIMULATION_RESULT
     - BUILD_SIMULATION_CASE_INDEX
     - SEARCH_SIMULATION_CASES
     - SAVE_SIMULATION_REVIEW_ITEM
     - UPDATE_SIMULATION_REVIEW_STATUS
     - EXPORT_SIMULATION_CASE_REDACTED
     - ATTACH_SIMULATION_TO_REPORT
     - ATTACH_SIMULATION_TO_STRATEGY_COMMIT
   - Every action must be local, deterministic, safe-id validated, and action-less.

8. Options Lab / Research Workspace Integration
   - Extend the existing Options Lab page payload with Goal 13A simulation and model-governance sections.
   - Keep this compatible with existing layout payload conventions.
   - Include summary cards/panels for simulation cases, selected simulation case, scenario sets, feed datasheets, model artifact cards, review state, and redacted export actions.
   - Do not build a marketing page.
   - Do not introduce brittle UI-only behavior if tests can validate the payload shape.

9. Report and Strategy-as-Git Attachments
   - Add bridge helpers to attach simulation case summaries and model governance records to existing reports and StrategyCommit artifacts.
   - Reuse lib/research_artifact_store.py and lib/options_strategy_commit_bridge.py patterns.
   - Attach only redacted, research-only, action-less payloads.

10. Release Hygiene
   - Update release hygiene checks so Goal 13A private artifacts, generated simulation cases, model artifacts, caches, weights, checkpoints, external ZIPs, and local private data are not packaged.
   - Preserve the Goal 12E manifest sanitation guarantees:
     - no absolute local paths
     - no .env
     - no private data
     - no external reference ZIPs
     - deterministic LF JSON output where applicable

SUGGESTED IMPLEMENTATION ORDER

1. Baseline audit
   - Inspect file inventory using rg --files.
   - Read Goal 12E/13 docs and relevant lib/tests.
   - Inspect external (2).zip using Python zipfile or safe extraction to a temporary location.
   - Inspect all external LICENSE, NOTICE, COPYING, COPYRIGHT, package metadata, and README license statements before adapting logic.
   - Use web search for governance references.

2. Goal 13A spec docs
   - Create docs/GOAL_13A_SPEC.md.
   - Create docs/GOAL_13A_EXTERNAL_REFERENCE_RESEARCH_REPORT.md.
   - Create docs/GOAL_13A_EXTERNAL_LICENSE_AUDIT.md.
   - Create docs/GOAL_13A_MODEL_ARTIFACT_GOVERNANCE.md.

3. Schema and validators
   - Add action-less simulation schemas and validation helpers.
   - Add tests for safe ids, path safety, required fields, redaction, status values, and forbidden action language.

4. Private store and index
   - Add save/load/list/search/redacted-export behavior.
   - Add tests for private storage location, no absolute paths in export, and deterministic summaries.

5. Model artifact governance
   - Add model card/datasheet/registry-style governance helpers.
   - Reuse existing quant model snapshot structures when sensible.
   - Add tests for lifecycle status, prohibited use, caveats, lineage, aliases/tags, and metadata-only external placeholders.

6. Workflow actions
   - Add local action router actions.
   - Integrate with existing Options Lab workflow action router.
   - Add tests for all actions and invalid payloads.

7. Options Lab payload integration
   - Extend page layout payload.
   - Add tests that payload sections exist and do not leak private paths or action language.

8. Report and StrategyCommit bridge
   - Attach redacted simulation artifacts to reports and strategy commits.
   - Add tests for attachment shape and research-only notices.

9. Release hygiene and docs
   - Add or update tests to ensure generated/private/model files are excluded from release.
   - Write security, test coverage, release hygiene, and final reports.

10. Packaging and validation
   - Clean generated release artifacts safely.
   - Build the Goal 13A release ZIP.
   - Inspect ZIP contents and manifest.

ACCEPTANCE CRITERIA

Goal 13A is complete only when all of the following are true:

- The repo contains a documented Action-less Simulation Case System.
- The system has schemas, validators, private persistence, indexing/search, redacted export, workflow actions, and Options Lab payload integration.
- Model Artifact Governance is implemented with model-card, datasheet, registry, lifecycle, lineage, caveat, and review-state concepts.
- All Goal 13A data remains local/private by default.
- All exported data is redacted and research-only.
- No trading execution path exists.
- External project logic is used only after license review, with project-native reimplementation preferred.
- No external source code is copied unless the exact file license permits it, notices/attribution are retained, the license audit documents it, and the copied portion is minimal and compatible.
- No external runtime/model dependency is introduced for Goal 13A.
- No model weights, checkpoints, private generated artifacts, .env files, external ZIPs, or absolute local paths are packaged.
- Existing Goal 12D/12E tests still pass.
- New Goal 13A tests cover the feature, release boundaries, and external license/copyright boundaries.
- The final release ZIP is rebuilt and inspected.

TEST REQUIREMENTS
Add focused tests. Suggested files:

- tests/test_goal13a_actionless_simulation_schema.py
- tests/test_goal13a_actionless_simulation_store.py
- tests/test_goal13a_actionless_simulation_index.py
- tests/test_goal13a_model_artifact_governance.py
- tests/test_goal13a_simulation_workflow_actions.py
- tests/test_goal13a_options_lab_payload.py
- tests/test_goal13a_report_strategy_commit_bridge.py
- tests/test_goal13a_release_hygiene.py
- tests/test_goal13a_external_reference_boundaries.py
- tests/test_goal13a_external_license_audit.py

Required validation commands:

```powershell
python -m compileall -q app.py lib pages scripts tests
python scripts/run_smoke_tests.py
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest --collect-only
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -q
```

Also run focused Goal 13A tests while building:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -q tests/test_goal13a_*.py
```

Release hygiene and package validation should include:

```powershell
python scripts/cleanup_release_artifacts.py --dry-run
python scripts/cleanup_release_artifacts.py
python scripts/build_release_zip.py
```

After packaging, inspect:

- ZIP entry count.
- release_manifest.json inside the ZIP.
- No .env entries.
- No data/private entries.
- No external ZIP entries.
- No model weights/checkpoints.
- No absolute paths.
- Goal 13A docs are included.
- Goal 13A tests are included unless the release policy excludes tests consistently.

DOCUMENTATION DELIVERABLES
Create or update:

- docs/GOAL_13A_SPEC.md
- docs/GOAL_13A_EXTERNAL_REFERENCE_RESEARCH_REPORT.md
- docs/GOAL_13A_EXTERNAL_LICENSE_AUDIT.md
- docs/GOAL_13A_MODEL_ARTIFACT_GOVERNANCE.md
- docs/GOAL_13A_SECURITY_AUDIT.md
- docs/GOAL_13A_TEST_COVERAGE_REPORT.md
- docs/GOAL_13A_RELEASE_HYGIENE_REPORT.md
- docs/GOAL_13A_FINAL_REPORT.md

The final report must include:

- What was implemented.
- What external references were used at concept level, logic level, or clean-room reimplementation level.
- What external implementation logic was studied and how it was reimplemented.
- License/copyright audit summary and any attribution/notice obligations.
- What web governance references were used.
- What was explicitly not implemented.
- Tests run and exact results.
- Release ZIP path.
- Release manifest summary.
- Go/no-go decision.

REGRESSION GUARDRAILS

- Preserve existing Goal 12E case store, case index, surface review queue, quant model lab, report inbox, and StrategyCommit behavior.
- Preserve .env locally and never package it.
- Do not rewrite unrelated files.
- Do not remove user changes.
- Do not change release package semantics except to add Goal 13A files and strengthen hygiene.
- If existing files are dirty, inspect and work with them.

FINAL RESPONSE EXPECTATION
When complete, report succinctly:

- Goal 13A implementation status.
- Key modules and docs added/updated.
- Tests run and pass/fail summary.
- Release ZIP path.
- Any residual risk or intentional exclusions.

Do not claim completion unless implementation, verification, packaging, and artifact inspection are actually done.
````
