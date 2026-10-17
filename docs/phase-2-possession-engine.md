# Phase 2 — Possession Intelligence Engine

Status: **implementation in progress on a feature branch; not yet verified by CI**.

## Goal

Build a local, reproducible possession prediction engine that keeps competition labels H/A/D/X. Initially use synthetic tracking only. Phase 1.5 real Metrica ingestion is **not verified** and remains open.

## Implemented in this branch

- Strict frame-prediction and half-open H/A spell contracts.
- Deterministic nearest-team distance features scaled using MatchMetadata pitch dimensions.
- A deliberately limited proximity baseline with unknown-state fallback (no invented dead-ball classification).
- Spell extraction that splits at D/X, gaps, and team changes.
- Synthetic unit tests for these contracts.

These are preliminary engineering components, not an official competition submission or scorer.

## Next steps (not yet implemented)

1. Verify branch tests, Ruff, mypy, and GitHub Actions.
2. Add Parquet feature serialization and end-to-end synthetic fixtures.
3. Build configurable temporal smoothing with D/X boundary safety.
4. Verify official spellF1 evaluator semantics and use it as the primary evaluation criterion.
5. Implement local experiment manifests, seeded comparisons, and provenance checks.
6. Add scikit-learn logistic regression then LightGBM once representative authorized labeled data is available.
7. Explore HMM/Viterbi temporal decoding and consider GRU/TCN/GNN only after evidence warrants it.
8. Validate on authorized real match data only after Phase 1.5 verification.

## Model rationale

Proximity is an interpretable, no-training reference. A tree-based classifier can learn nonlinear spatial and movement relationships from verified labels, while a temporal decoder can reduce spurious state changes. Neural sequence and graph models remain research candidates, not assumptions of superiority.

## Verification

Run `uv sync && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy .` locally. Do not mark complete until tests, linting, typing and CI pass.

No new cloud resources or ML dependencies are required for these initial modules. Restricted real tracking and derived data must not be placed in public Git.
