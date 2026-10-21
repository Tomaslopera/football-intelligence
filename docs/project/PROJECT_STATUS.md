
# Football Intelligence — Current Status

**Last updated:** 2026-10-20

## Final Tactical Quality Review — Current Checkpoint

The user executed the full tactical EPTS audit locally. The agent reviewed
sanitized aggregates and ran read-only processed-Parquet diagnostics:

- 199,319 source/stored frames, canonical 0–199318; no gaps, duplicates or orphans.
- Ball coverage 56.9379%; 3,782,421 positioned player observations.
- 70.8503 s runtime; 8,966.66 MiB (8.7565 GiB) process peak RSS.
- Original Parquet fingerprints and schemas verified; all 14 feature columns
  independently recomputed with zero mismatches on all 199,319 frame keys.
- 1,151 high ball-speed estimates form 87 runs and do not bridge missing
  observations; outliers are preserved, with physical cause unresolved.
- Longest missing interval [190630,199319) is 347.56 s after final whistle.
- All 4,964 out-of-bounds ball and 43,911 player positions remain retained.

**Phase 1.5: PASS locally. Phase 2.1: PASS locally.** The official challenge
DATA.md explicitly documents Kloppy EPTS speeds in m/s. This resolves the
XML kph mismatch; a documented BAR-ATH tactical source contract now preserves
the source numbers as m/s, while generic genuine-kph inputs still convert.

Use **`datasets/processed/metrica/BAR-ATH/tactical-real-full-02/`**. The agent
rebuilt this full dataset from validated canonical input without reopening
raw EPTS: undid the earlier factor-of-3.6 conversion, regenerated causal
features and quality, and independently verified every feature column and
frame key. Median reported speed is 1.33548 m/s, maximum 11.29383 m/s,
motion/reported ratio 1.00348. Unit evidence, declared/effective units and
upstream fingerprints are recorded. Rebuild/verification took 20.08 s.
Original `tactical-real-full-01` is preserved for provenance and superseded
for downstream use. Synthetic tests prove equivalence to direct corrected
source ingestion, preserve ordinary kph/m/s behavior and prevent reapplying
the same correction. This is not a new agent-run raw ingestion.

The 8.76 GiB memory requirement remains a documented offline limitation;
production optimization is deferred until workload/resource needs justify it.
GitHub CI for pending changes is UNVERIFIED. Phase 2.2 is technically ready
to begin using corrected artifacts; it has not started. No ML training,
staging, commits or pushes were performed.
Final verification: Ruff format/check passed (68 Python files), mypy passed
(25 source files), all **157 tests passed**, and audit-change whitespace
checks passed. Seven added speed-correction cases cover source-contract
selection, override validation, generic kph preservation and corrected
rebuild equivalence to direct synthetic source ingestion.

See [full findings, local commands and decisions](../research/metrica-integration-audit.md).

## Earlier Engineering Audit — Historical Checkpoint

Speed-unit follow-up: the user's real tactical inspection found `kph`, which
the initial metadata guard rejected. Kloppy 3.19.1 preserves source speed
values (code inspection and synthetic EPTS verified). The EPTS adapter now
converts kph to m/s once before canonical ingestion, accepts m/s unchanged,
rejects unknown/ambiguous units, and records unit provenance in audit lineage.
Canonical features and quality thresholds retain m/s semantics. The real
100-frame rerun remains pending under the existing license fallback; see
the audit report for the fresh-output local command.
Speed-fix verification: Ruff format/check and mypy passed; 33 focused tests
and all 147 tests passed.

Repository-only audit completed; licensed tactical and broadcast files were
not opened. The separate challenge checkout's `RULES.md` defers permissions
to enrollment terms, which were unavailable during this audit. This is the
requested fallback when authorization for hosted-agent access is uncertain.

Baseline: Ruff format/check, mypy and 118 tests passed. Added a local EPTS
audit command, explicit metadata mapping with no team-order fallback,
aggregate-only inspection, and synthetic XML/TXT integration regressions.
Final verification: Ruff format/check passed (61 Python files), mypy passed
(23 source files), and all 136 tests passed.
The full synthetic submission and official validator/public evaluator passed
again against challenge commit `3de6b60aeabd2475d95879a651d38b72bc4fba00`.

Phase 1.5 remains open. Phase 2.2 is not ready for real-data experimentation
until local full-match ingestion, mapping, quality, feature and memory results
have been reviewed. No ML training was performed.

See [audit report and local commands](../research/metrica-integration-audit.md).

## Current Position

Phase 1 Data Engineering Foundation is implemented and verified
using synthetic datasets.

Phase 1.5 full tactical integration and documented source-unit correction
pass local acceptance. Corrected full artifacts have been verified.

Phase 2.0 Possession Foundation is complete. Official Metrica
submission validation and public evaluator integration succeeded.

Phase 2.1 is implemented and independently verified against corrected full
real canonical tracking. Local acceptance passes; GitHub CI remains unverified.

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

- Use corrected `tactical-real-full-02` and its recorded source-unit contract.
- Raw source reingestion with the corrected policy remains available as a
  local reproducibility command; the agent used validated derived inputs.
- Governance and redistribution review for derived data.
- Public-safe dataset and showcase strategy.

Real-data numerical integration and documented unit interpretation pass locally.

## Next Priority — Phase 2.2 Planning After Review

Review the local phase closures, source-unit provenance and corrected artifacts.
Then begin Phase 2.2 with explicit label availability, causal features and
the documented source-quality/memory limitations. No models have been trained.

## Subsequent Priority — Phase 2.2 ML Experimentation

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
