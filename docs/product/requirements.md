# Product Requirements — Football Intelligence Platform

**Status:** Draft v0.1 · Priority convention: **P0** required for competition, **P1** required for portfolio MVP, **P2** optional extension.

## Functional requirements
| ID | Priority | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-01 | P0 | Reproduce official scorer and reference baselines | Official evaluation runs in clean documented environment |
| FR-02 | P0 | Ingest tactical tracking, tagging, and homography | All available records loaded with source/time provenance and schema checks |
| FR-03 | P0 | Validate temporal alignment and data quality | Frame coverage, discontinuities, missing ball, invalid values reported |
| FR-04 | P0 | Engineer spatial and temporal features | Deterministic versioned feature artifacts from fixed input/config |
| FR-05 | P0 | Predict one of H/A/D/X per video frame | Exactly 199,319 frame-indexed predictions including ungraded frames |
| FR-06 | P0 | Decode coherent possession spells | Intervals calculated from predictions with consistent boundary semantics |
| FR-07 | P0 | Evaluate candidate algorithms | Official public scorer results plus interpretable diagnostics |
| FR-08 | P0 | Export official competition CSV | Header `frame,label`, frames 0..199318, valid labels, validator passes |
| FR-09 | P0 | Reproduce competition results | Pinned code/dependencies/config, seeded algorithms, documented command and output hash |
| FR-10 | P1 | List available public-demo matches | User can select a permitted match |
| FR-11 | P1 | Browse possession timeline | Select intervals and navigate by frame/time |
| FR-12 | P1 | Render interactive 2D tactical replay | Play/pause, scrub, variable speed, ball/players for permitted dataset |
| FR-13 | P1 | Display prediction evidence/metadata | State, model version, confidence if available, and data-quality indicators |
| FR-14 | P1 | Provide match summaries | Team possession shares and spell/transition statistics calculated from predictions |
| FR-15 | P1 | Provide model comparison UI | Show evaluation context, metric names, benchmark results, limitations |
| FR-16 | P1 | Deploy safe public demo | No competition-protected video, tracking exports, or reconstructive derivatives |
| FR-17 | P2 | Engineering console | Show pipeline runs, errors, quality metrics, and inference artifacts |
| FR-18 | P2 | Advanced tactical overlays | Movement trails, density, pressure proxies with explainable definitions |

## Nonfunctional requirements
| ID | Requirement | Verification |
|---|---|---|
| NFR-01 | Reproducibility | Rebuild CSV and compare hash under documented runtime |
| NFR-02 | Correctness | Boundary, state transition, alignment, and export validation tests |
| NFR-03 | Modular architecture | AI pipeline executes without frontend, API, DB, or cloud services |
| NFR-04 | Maintainability | Typed public interfaces, unit tests, linting, formatter, ADRs |
| NFR-05 | Security/privacy | Secrets excluded; restricted data not checked in or published |
| NFR-06 | Observability | Job run metadata, duration, warnings, input fingerprints, error logs |
| NFR-07 | Performance | Benchmark whole-match batch runtime before choosing a numerical target |
| NFR-08 | Usability | Interactive replay has smooth controls on target desktop hardware; establish frame-rate budget after prototype |
| NFR-09 | Data provenance | Every derived artifact maps to source, config, and processing code version |
| NFR-10 | Cost control | Set actual hosted budget before deploying; batch inference offline |

## Competition invariants
- Labels are exactly `H`, `A`, `D`, `X`. `X` is an abstention, not a fourth scored ground-truth class.
- The tactical video frame index is the authoritative submission index; broadcast video has a different timeline.
- **199,319** rows; `frame` runs **0 through 199318** with no gaps.
- Public 5-minute ground truth has **7,500 graded frames**, **17 possessions**; it is not a sufficient stand-alone test for generalized model quality.
- The official board ranks on `spellF1`; `macroF1` is also reported.
- Labels must be algorithmically generated; do not hand-correct the submitted CSV.

## Interfaces and contracts (proposed, not yet implemented)
- CLI: `ingest`, `features`, `predict`, `evaluate`, `export-submission` — final executable syntax defined during implementation.
- Prediction record: `match_id`, `frame`, `label`, `model_version`, optional `confidence`, `run_id`.
- Spell: `match_id`, `start_frame` inclusive, `end_frame` exclusive, team (`H` or `A`), `run_id`.
- API (future): `GET /matches`, `GET /matches/{id}/summary`, `GET /matches/{id}/spells`, `GET /matches/{id}/replay?start_frame=...&end_frame=...`.

## Out of scope / legal boundary
Competition data use is governed by enrollment terms. Do not redistribute clips, frame-level tracking or derived exports reconstructing the dataset. Do not upload restricted data/extracts to third-party hosted/cloud LLMs. Check permissions before any cloud processing; use synthetic/permitted assets in CI and public demos.

## Definition of done
A requirement is complete only when code, test/validation evidence, and documentation exist; mark unimplemented features as planned, never as delivered.
