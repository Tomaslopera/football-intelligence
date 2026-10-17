
# Football Intelligence — Current Status

**Last updated:** 2026-10-17

## Current Position

Phase 1 Data Engineering Foundation is implemented and verified
using synthetic datasets.

Phase 1.5 Metrica integration adapter is implemented but awaits
authorized real-data verification.

Phase 2.0 Possession Foundation is complete. Official Metrica
submission validation and public evaluator integration succeeded.

Phase 2.1 Football Feature Engineering is implemented and locally
tested. Documentation and GitHub Actions verification are pending.

Phase 2.2 ML Experimentation has not started.

Backend, frontend, and cloud deployment have not started.

## Completed and Verified

### Phase 1 — Data Engineering

- Canonical tracking domain models and frame alignment.
- Synthetic tracking ingestion.
- Parquet storage and DuckDB analytical querying.
- Data quality checks and lineage.
- Preparation of the Metrica EPTS adapter.

### Phase 2.0 — Possession Foundation

- Canonical possession prediction contracts.
- Prediction sequence alignment and validation.
- Contiguous possession-state segment extraction.
- Official competition CSV export.
- Public ground-truth reader and grading mask.
- Synthetic full-match submission demonstration.
- Successful official Metrica submission validation.
- Successful official public evaluator execution.

Synthetic evaluation scores are integration diagnostics,
not evidence of trained-model performance.

### Phase 2.1 — Feature Engineering

Locally verified:

- Spatial distances in meters.
- Nearest home and away player features.
- Ball visibility and player coverage features.
- Causal ball displacement and derived speed.
- Team mean reported speeds.
- Missing-ball streaks.
- Temporal distance-advantage changes.
- Versioned PyArrow/Parquet feature datasets.
- Feature schema validation and nullable values.
- End-to-end synthetic tracking-to-Parquet pipeline.
- DuckDB feature queries.

Pending before milestone closure:

- Documentation synchronization.
- Final repository quality checks.
- Git commit and push.
- Successful GitHub Actions verification.

Technical documentation:
`docs/ai/feature-engineering.md`

## Active Dependencies

- Authorized real Metrica tracking data access.
- Verification of real EPTS ingestion.
- Official team/track-slot metadata mapping.
- Real-match feature quality inspection.
- Governance and redistribution review for derived data.
- Public-safe dataset and showcase strategy.

Real-data integration remains open independently of the
synthetic-data milestones.

## Next Priority — Phase 2.2 ML Experimentation

Plan and implement a reproducible experimentation foundation.

Initial goals:

- Training and evaluation dataset contracts.
- Explicit target-label availability and grading masks.
- Data leakage prevention.
- Feature-set configurations and ablations.
- Reproducible experiment manifests.
- Heuristic baseline models.
- Classical probabilistic models.
- Gradient-boosted models.
- Temporal modeling and postprocessing experiments.
- Evaluation using the official competition scorer.

No final model family has been selected.

The public five-minute ground truth is suitable for integration
diagnostics, not reliable model selection.

Training on restricted assets requires permitted data access.
No private ground truth is available.

## Architecture Decisions

- Python-first modular architecture.
- Independently executable data, AI, and API responsibilities.
- Modular monolith initially.
- Next.js / React / TypeScript frontend.
- AWS Lambda preferred for the initial Python API.
- Supabase Free PostgreSQL for application and experiment metadata.
- Parquet and DuckDB for high-volume analytical datasets.
- Local model training and batch inference initially.
- Precomputed predictions preferred for the initial public product.
- On-demand model containers only if technically justified.
- No always-running model server by default.
- Terraform for infrastructure as code.
- GitHub Actions for CI/CD.
- Cost minimization is a primary requirement.
- No exact monthly cloud budget has been confirmed.
- Restricted tracking data must not be redistributed.

## Open Decisions

- Final product branding.
- Specific AWS and frontend hosting provider.
- Lambda responsibility boundaries.
- Pitch rendering technology.
- Model framework and experiment-tracking implementation.
- Exact monthly cloud budget.
- Public-safe showcase data source.
- Final model family and feature combinations.

## Completion Rules

A milestone is complete only after relevant implementation,
tests, documentation, and integration verification pass.

Local verification and successful GitHub CI are distinct
completion conditions.

Keep project documentation synchronized with implemented code.
