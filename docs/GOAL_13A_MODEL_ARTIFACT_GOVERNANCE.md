# Goal 13A Model Artifact Governance

Generated: 2026-06-15

## Objective

Goal 13A adds metadata-only model artifact governance records for local research. A model artifact card describes an artifact, its lineage, caveats, review state, and intended research use. It does not load, train, evaluate, serve, or run a model.

## Model Card Fields

- `model_artifact_id`: safe local identifier.
- `model_name`: display label.
- `category`: existing quant model category or metadata-only placeholder category.
- `version`: local version string.
- `lifecycle_status`: one of proposed, experimental, review_required, approved_for_research, deprecated, archived.
- `intended_use`: research-only diagnostic use.
- `prohibited_use`: execution, advice, broker, order, autonomous, deployment, and external inference prohibitions.
- `input_assumptions`: expected local inputs and caveats.
- `output_type`: diagnostic, scenario_summary, metadata_card, or similar non-prescriptive output.
- `evaluation_summary`: supplied or deterministic evaluation notes.
- `caveats`: limitations and known non-goals.
- `source_references`: local docs or concept references.
- `artifact_uri`: metadata pointer only, never a local absolute path or model-weight file.
- `lineage`: source case, feed snapshot, scenario, or prior artifact references.
- `owner` and `reviewer`: local governance labels.
- `review_status`: new, queued, under_review, needs_revision, reviewed, archived.
- `tags` and `aliases`: registry-style labels inspired by model registry concepts.
- `research_only`, `metadata_only`, `no_runtime`, and `notice`: mandatory safety markers.

## Datasheet Fields

Data feed snapshots use datasheet-like records with source label, generation time, coverage, fields, transformations, freshness, limitations, missingness notes, privacy notes, and intended research use. These records can describe user-supplied or local snapshots without requiring live external providers.

## Registry Concepts

Goal 13A borrows the model registry concepts of name, version, aliases, tags, lineage, metadata, and lifecycle status. The local implementation intentionally omits production stages, serving, deployment, traffic aliases, and managed registry backends.

## External Placeholder Policy

External references such as Kronos and TensorTrade may appear only as metadata-only placeholders:

- `kronos_metadata_placeholder`: foundation-model governance card with no weights, checkpoint, inference, or external runtime.
- `tensortrade_actionless_placeholder`: simulation architecture card with action execution removed.
- `quantdinger_review_placeholder`: review and lifecycle governance card with broker/API execution removed.

These placeholders document provenance and caveats. They do not enable forecast claims, recommendations, model execution, broker calls, or autonomous behavior.
