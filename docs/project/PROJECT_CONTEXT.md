# Football Intelligence — Master Project Context

**Project:** Football Intelligence — Engineering Lab  
**Type:** Independent personal engineering initiative  
**Repository:** football-intelligence  
**Product name:** Not finalized  
**Last planning update:** October 2026

## 1. Mission

Build a production-grade, visually impressive football intelligence platform covering four technical disciplines:

- Software Engineering: backend, frontend, APIs, testing, architecture.
- Data Engineering: ingestion, normalization, quality, lineage, storage, pipelines.
- AI Engineering: feature engineering, possession prediction, model evaluation, experimentation.
- Cloud Engineering: serverless computing, infrastructure as code, CI/CD, deployment, observability, cost management.

The initial use case comes from Metrica Sports / FC Barcelona's More Than a Hack 2027 competition. The competition is a starting point, not the entire product.

The final application should be a real, interactive sports analytics experience suitable for an engineering portfolio.

This project is unrelated to Alegra or the user's separate NYC engineering initiatives.

## 2. Product Vision

Create a premium dark-mode football intelligence platform with five product areas.

### Match Dashboard

Display available matches, teams, summaries, possession metrics, AI results, and links to deeper analysis.

### Tactical Replay

Render a 2D football pitch with animated player and ball tracking, playback controls, frame navigation, temporal overlays, and tactical information.

### Possession Explorer

Visualize predicted and reference possession states, possession spells, transitions, model confidence where available, and selected match sequences.

### AI Model Lab

Compare model versions, experiments, evaluation metrics, baseline performance, and error patterns.

### Engineering Console

Display dataset coverage, quality reports, lineage, pipeline status, model artifacts, and system diagnostics.

The final product name and detailed UI design remain undecided.

## 3. Competition Context

Competition: More Than a Hack 2027 — Metrica Sports / FC Barcelona.

Primary problem: predict possession state for football tracking frames.

States:
- H — Home possession.
- A — Away possession.
- D — Dead ball.
- X — Unknown.

The principal competition ranking metric is spellF1, averaged across possession-spell overlap thresholds.

The referenced Barcelona vs Athletic match contains approximately 199,319 frames at 25 FPS.

Public ground truth includes 7,500 graded frames and 17 reference possessions.

Earlier official baseline research produced approximately 0.4242 spellF1 on the public graded sample using baseline_smooth125.

That score belongs to an existing baseline, not a new model built by this project.

The official competition repository is cloned separately from football-intelligence.

The user registered individually. Eligibility, deadlines, submission constraints, and current data availability require verification against official sources.

At the time of Phase 1.5 preparation, authorized real EPTS match files had not yet been integrated.

## 4. Main Architecture Decisions

### Application structure

Python-first modular monolith with distinct modules for ingestion, analytical storage, data quality, feature engineering, model inference, and application services.

Do not create unnecessary microservices at the source-code level.

Lambda functions can be split into independently deployable services when there is a clear advantage.

### Processing model

Separate:

1. Offline data ingestion and validation.
2. Offline feature engineering and model training.
3. Batch possession inference and evaluation.
4. Web API request handling.
5. Interactive frontend rendering.

The first public product serves precomputed predictions. It does not need a permanently running ML inference server.

### Cloud strategy

Serverless-first and extremely cost-conscious.

AWS ECS/Fargate is NOT part of the preferred initial deployment.

Use AWS Lambda for the Python API, possibly with API Gateway HTTP API.

Use Supabase Free PostgreSQL for application metadata.

Host Next.js statically where compatible with product requirements.

Use object storage for permitted public-safe artifacts only.

Use Terraform and GitHub Actions for cloud infrastructure and automated delivery.

AI containers are optional and should only be introduced for a workload that requires them. Containers should run on demand, not continuously.

Docker is optional for local development and not mandatory for every application component.

No paid infrastructure should be introduced without reviewing costs and alternatives.

The monthly cloud budget has not yet been explicitly finalized.

### Data storage separation

PostgreSQL:
- Teams and matches.
- Dataset metadata.
- Model versions.
- Experiment summaries.
- Quality summaries.
- Processing job metadata.
- Application-level entities.

Parquet:
- Frame observations.
- Player tracking observations.
- High-volume prediction sequences.
- Analytical and model-processing datasets.

DuckDB:
- Analytical querying against Parquet.
- Data quality and feature engineering queries.

Raw files:
- Preserved locally and kept immutable.

Object storage:
- Approved public-safe dataset chunks, model outputs, and other application artifacts.

Avoid putting millions of tracking observations directly into Supabase Free PostgreSQL.

## 5. Target System Data Flow

Authorized source data / synthetic data
→ source loader and adapter
→ canonical tracking models
→ validated tracking observations
→ Parquet storage
→ DuckDB analytics and data quality
→ feature engineering
→ possession model
→ temporal smoothing and evaluation
→ prediction artifacts
→ FastAPI / AWS Lambda
→ Next.js interface.

FastAPI API requests must not rerun entire match inference jobs.

The frontend communicates with the backend through HTTP APIs.

The API reads prepared application metadata and public-safe analytical artifacts.

## 6. Technology Stack

### Already introduced

- Python 3.11+.
- uv package and dependency management.
- Pydantic.
- Pandas and NumPy.
- Kloppy for EPTS integration preparation.
- PyArrow and Parquet.
- DuckDB.
- pytest, pytest-cov, Ruff, and mypy.
- GitHub Actions for CI.
- SHA-256 fingerprinting.
- JSON and Markdown quality reports.

### Planned

- scikit-learn and LightGBM for initial ML work.
- PyTorch if justified by experiments.
- MLflow and Optuna when experiment volume warrants them.
- FastAPI for the backend.
- Next.js, React, TypeScript for the frontend.
- PixiJS or Canvas for tactical visualization, pending choice.
- Supabase Free PostgreSQL for application data.
- AWS Lambda and API Gateway.
- S3 or equivalent object storage when justified.
- Terraform.
- Optional Docker and on-demand model containers.
- Cloud logging, monitoring, and cost controls.

No production cloud deployment has been completed.

## 7. Project Folder Organization

The intended local data organization is:

datasets/
  raw/
    metrica/
      barcelona-athletic/
        tactical/
        video/
        tagging/
  processed/
    metrica/
      barcelona-athletic/
  generated/
    demo/
    quality-demo/
    quality-reports/

The actual provider filenames must be preserved.

Not every illustrated asset type is guaranteed to be present in the official data release.

Important rules:
- datasets/raw/ contains original source files that should not be modified.
- datasets/processed/ contains standardized datasets from real inputs.
- datasets/generated/ contains synthetic demos and generated outputs.
- All three directories must be excluded from public Git.
- Receiving files does not automatically run ingestion.
- Verify the source format, metadata, frame alignment, and team mappings before processing.

## 8. Completed Implementation

### Phase 0 — Engineering Foundation

Created the independent football-intelligence project.

Configured uv, Python packaging, type checking, linting, unit testing, documentation, GitHub repository, and GitHub Actions.

Created initial product vision, requirements, roadmap, architecture, and baseline analysis documentation.

### Phase 1.1 — Canonical Tracking Contracts

Implemented tracking models:
- TrackingFrame.
- PlayerObservation.
- BallObservation.
- PitchPosition.
- Velocity.
- MatchMetadata.
- TeamSide.
- RecordingSource.

Added frame alignment helpers and canonical validation.

Canonical frame identifiers are zero-based; EPTS source frame IDs are one-based.

### Phase 1.2 — Synthetic Tracking Ingestion

Implemented synthetic tracking tables and DataFrame normalization.

Implemented missing numeric value handling, optional coordinate normalization, track-slot discovery, frame sequence validation, and team mapping inputs.

### Phase 1.3 — Analytical Storage

Implemented:
- frames.parquet.
- players.parquet.
- Explicit PyArrow schemas.
- Zstandard compression.
- Writing and reading canonical observations.
- Round-trip tests.
- DuckDB tracking summaries.
- Local demo_storage.py demonstration.

### Phase 1.4 — Data Quality & Lineage

Implemented:
- Ball/player observation coverage metrics.
- Frame gap and missing ID detection.
- Duplicate and orphan diagnostics.
- Out-of-bounds coordinate checks.
- Suspicious player speed thresholds.
- Configurable quality parameters.
- SHA-256 file fingerprints.
- Quality lineage manifests.
- JSON and Markdown reports.
- Synthetic anomaly tests.
- demo_quality.py.

### Phase 1.5 — Metrica EPTS Preparation

Prepared and pushed:
- Kloppy EPTS adapter.
- EPTS file presence validation.
- Track-column normalization.
- Synthetic compatibility tests.
- inspect_metrica.py inspection utility.

Still outstanding:
- Authorized real-file inspection.
- Verified mapping from source track slots to home/away teams.
- Real schema and coordinate validation.
- Full-match ingestion.
- Real-data Parquet output.
- Quality and lineage analysis using the real match.
- Performance and memory profiling.

Phase 1.5 must remain open until real integration has been verified.

## 9. Data Contract Details

Canonical TrackingFrame includes:
- match_id.
- source.
- zero-based frame number.
- player observations.
- ball observation.

Player observations include track_slot, team, optional position, and optional speed.

Ball observations include optional position and optional speed.

Source track slots must not be treated as reliable permanent player identities.

Team assignment must come from verified metadata.

Missing coordinates are represented explicitly; data quality checks are diagnostic rather than silently rewriting suspicious records.

Tactical video is the tracking reference; broadcast video requires independent synchronization if ever used.

The existing ingestion and serialization approach still requires full-match scalability profiling and possible streaming enhancements.

## 10. Remaining Roadmap

### Phase 1.5 — Complete Real Data Integration

Validate the EPTS ingestion pipeline on actual authorized source files.

### Phase 2 — AI Possession Intelligence

Implement:
- Football features: player-ball distance, velocities, spatial geometry, temporal context.
- Baseline and machine learning possession models.
- Temporal smoothing.
- Possession-spell extraction.
- Official metric evaluation and transition analysis.
- Reproducible experiments.
- Prediction artifacts and model versions.

### Phase 3 — Competition Pipeline

Prepare competition-compatible prediction outputs, controlled experiments, model selection, and permitted submission workflow.

This may run concurrently with Phase 2.

### Phase 4 — Backend Engineering

Develop FastAPI modules and Lambda-compatible deployment.

Implement match, frame, possession, quality, and model metadata endpoints.

Connect approved analytical artifacts and Supabase PostgreSQL.

### Phase 5 — Frontend & Visualization

Build the premium Next.js experience.

Implement match overview, animated pitch, possession explorer, AI comparisons, and engineering views.

Use synthetic or appropriately licensed data for public demos.

### Phase 6 — Cloud & DevOps

Implement:
- Static frontend deployment.
- API Gateway and Lambda.
- Supabase PostgreSQL integration.
- Permitted object storage.
- Terraform.
- CI/CD.
- Monitoring and secrets.
- Billing safeguards.
- Optional on-demand model workload containers.

### Phase 7 — Production & Portfolio Polish

Improve performance, security, accessibility, documentation, visual identity, reliability, demo experience, and project presentation.

Phases 3–7 are a working roadmap and can be refined before implementation.

## 11. Public vs Private Data

The project must respect the Metrica competition license.

Do not upload restricted match video, raw tracking, or prohibited detailed derived data to public cloud infrastructure, external hosted AI systems, or GitHub.

Public portfolio deployment must use synthetic or independently licensed data and approved aggregate results.

Keep public demonstration assets separate from private research datasets.

## 12. Current Engineering Status

Completed and pushed:
- Phase 0.
- Phase 1.1.
- Phase 1.2.
- Phase 1.3.
- Phase 1.4.
- Phase 1.5 preparatory adapter.

Not yet completed:
- Full Phase 1.5 verification with real source data.
- Phase 2 AI engine.
- Backend application.
- Frontend application.
- Cloud deployment.

CI for the Phase 1.5 push should be confirmed independently if its result is not already recorded.

## 13. Immediate Next Steps

1. Finalize and maintain this shared project documentation.
2. Begin Phase 2 planning, feature engineering, and evaluation interfaces.
3. Obtain and inspect authorized Metrica data when available.
4. Complete Phase 1.5 real-data integration.
5. Develop backend and frontend contracts around precomputed public-safe artifacts.
6. Confirm a specific target cloud budget before infrastructure provisioning.
7. Keep architecture decisions and current status updated.

## 14. Collaboration Rules

The source repository and documented decisions are the technical source of truth.

All workstreams must distinguish implemented from planned functionality.

New decisions or completed milestones should update PROJECT_STATUS.md and, when appropriate, architecture decision records.

Do not automatically assume progress from another conversation.

Treat the project as a long-term engineering product rather than a short competition script.