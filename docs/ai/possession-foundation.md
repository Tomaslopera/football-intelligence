## Phase 2 — AI Engineering

### Phase 2.0 — Possession Foundation

**Status: Completed after local tests, documentation and CI verification.**

Implemented:

- Prediction context and sequence validation.
- Possession segment extraction.
- Competition-compatible CSV export.
- Public ground-truth reader and explicit grading mask.
- Synthetic full-match submission generation.
- Official Metrica submission validation.
- Official public evaluator integration.

Official integration verified against the public reference CSV.

The synthetic evaluation score is not considered model performance.

### Phase 2.1 — Football Feature Engineering

**Status: Not started.**

Next objectives:

- Define reproducible feature contracts.
- Calculate player-ball proximity features.
- Calculate team-level spatial features.
- Handle missing tracking observations.
- Persist feature datasets where appropriate.
- Validate features with deterministic synthetic examples.

### Outstanding Dependency

Phase 1.5 remains open pending authorized real Metrica tracking data and successful real-match ingestion.