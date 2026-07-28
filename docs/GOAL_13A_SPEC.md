# Goal 13A Spec

Generated: 2026-06-15

## Mission

Implement a local, private, research-only Action-less Simulation Case System and Model Artifact Governance layer for the Global Market Analyst Terminal.

Goal 13A deliberately does not implement broker execution, order routing, paper trading, live trading, autonomous trading, reinforcement-learning execution, model training, external model inference, downloaded weights, worker queues, API services, webhooks, or background schedulers.

## Acceptance Criteria

- Simulation cases have deterministic schemas, safe IDs, path traversal guards, local/private persistence, index/search, redacted export, workflow actions, and Options Lab payload integration.
- Scenario sets, data feed datasheets, model artifact cards, simulation results, and review items are represented as local action-less research artifacts.
- Model governance records include intended use, prohibited use, lifecycle status, review state, lineage, aliases/tags, caveats, evaluation summary, source references, and metadata-only artifact pointers.
- Redacted exports remove private paths, absolute local paths, secrets, `.env` values, and generated private storage details.
- Workflow actions remain synchronous and local. They create artifacts, attach redacted summaries, and update review state only.
- Report and StrategyCommit attachments contain research-only redacted payloads and never encode market action instructions.
- Release packaging excludes private data, external ZIPs, generated simulation cases, model weights, checkpoints, local databases, and absolute path metadata.

## Governance References

- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST AIRC AI RMF Core: https://airc.nist.gov/airmf-resources/airmf/
- Model Cards for Model Reporting: https://arxiv.org/abs/1810.03993
- Datasheets for Datasets: https://arxiv.org/abs/1803.09010
- MLflow Model Registry concepts: https://mlflow.org/docs/latest/ml/model-registry/

Goal 13A maps these references into a lightweight local profile:

- Govern: model artifact cards, lifecycle status, review state, prohibited use, source references, release hygiene.
- Map: scenario sets, source context, linked options cases, linked StrategyCommit records, data feed datasheets.
- Measure: deterministic diagnostics, metrics, warnings, limitations, missingness notes, evaluation summaries.
- Manage: redacted export, review queue status updates, attachment bridges, action-less wording checks.

## Vertical Slices

1. Schema and validators
   - Safe IDs, status enums, path guards, research-only notices, action-less text validation.
   - Objects: simulation case, scenario set, data feed snapshot, model artifact card, result artifact, review item.

2. Private store and index
   - JSON files under `data/private/actionless_simulations`.
   - Redacted export bundle with no `case_dir`, absolute path, or private path leakage.
   - Deterministic index and text search.

3. Model artifact governance
   - Reuse existing quant model category vocabulary where appropriate.
   - Add metadata-only cards for external placeholders such as Kronos and TensorTrade without runtime imports or weights.

4. Workflow actions
   - Add local actions for creating/updating cases, saving artifacts, building/searching the index, review updates, export, and attachments.
   - Integrate with the existing Options Lab action router and research workflow safety layer.

5. Payload integration
   - Extend the Options Lab page payload with simulation case summaries, selected redacted case payload, search results, model governance cards, and allowed actions.

6. Release and review gates
   - Add tests for release exclusions, no external runtime dependencies, and no copied source boundary.
   - Build the release ZIP and inspect manifest contents.

## Safety Boundary

Allowed wording includes: research-only, action-less, simulation case, scenario, artifact, diagnostic, governance record, redacted export, review state, and not investment advice.

Forbidden behavior includes: broker execution, order routing, one-click trade, paper or live trading controls, autonomous trading, strategy deployment, portfolio rebalancing instructions, hedging instructions, position sizing recommendations, trade recommendations, RL policy execution, external model inference, downloaded model files, API servers, worker daemons, Redis queues, external service dependencies, and packaged private data.

## Release Boundary

The release ZIP must include Goal 13A source, tests, and docs, but must exclude:

- `.env` and `.env.*` secrets except `.env.example`.
- `data/private`, generated simulation cases, local databases, logs, caches, and `dist`.
- External ZIPs and extracted external reference trees.
- Model weights and checkpoints such as `.pt`, `.pth`, `.ckpt`, `.onnx`, `.safetensors`, `.h5`, and `.joblib`.
- Any manifest field that exposes an absolute local path.
