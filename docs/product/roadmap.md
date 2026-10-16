# Delivery Roadmap — Football Intelligence Platform

**Status:** Proposed plan (not a report of completed work). **Start:** Oct 15, 2026. **Competition deadline:** Nov 17, 2026.

## Milestone 0 — Foundation (Oct 15–19)
**Deliver:** pinned official challenge baseline; independent `uv` package; initial possession domain types; pytest, Ruff, mypy; GitHub Actions; architecture/product docs.

**Observed progress as of Oct 15:** official baseline executed; independent `uv` project created; three domain tests and local lint/format/type checks passed; CI file exists. **Still verify:** GitHub-hosted CI green, docs committed, remote push.

**Exit gate:** `uv sync --locked`, `uv run pytest`, Ruff, mypy all pass on a clean clone; official scorer reproduced separately; docs reviewed.

## Milestone 1 — Data foundation (Oct 20–26)
**Dependency:** competition assets released to enrolled participants under terms.

**Tasks:** inspect provided data; implement official-frame alignment; record missing ball/team tracking; build synthetic fixtures; create validated canonical frame entities and Parquet partitions; write integration tests.

**Exit gate:** stable schema, quality report, successful frame alignment and dataset reproducibility. Public CI uses synthetic fixtures only.

## Milestone 2 — Possession intelligence (Oct 27–Nov 9)
**Tasks:** reference baseline -> geometry rules -> structural ML (e.g. LightGBM) -> temporal decoding (e.g. HMM/semi-Markov); compare dead-ball performance and boundary timing; ablation and error analysis; log experiments and seeds.

**Exit gate:** chosen candidate has repeatable evaluation; hypotheses documented; no overfitting assertions from 17 public possessions. Neural model only if justified by time/data.

## Milestone 3 — Competition release (Nov 10–17)
**Tasks:** freeze code and model configs; full tactical-frame inference; create submission CSV; run official validator; rerun from clean environment; hash artifacts; finalize technical report; audit repo for protected files; attempt submission under organizer terms.

**Exit gate:** 199,319 valid rows, exact regeneration, public code and short technical report. Note: <3-member teams are not eligible for Innovation Challenge/Final Pitch per repository; solo submission treatment should be confirmed.

## Milestone 4 — Product MVP (after Nov 17)
**Tasks:** design UI tokens; implement matches API and read-only model outputs; build match overview, possession timeline, 2D pitch player animation; use licensed/synthetic demo data; publish model results with truthful evaluation context.

**Exit gate:** local vertical slice can explore a match and replay predictions; no restricted match content leaks.

## Milestone 5 — Cloud / flagship portfolio (after product MVP)
**Tasks:** Docker, managed deployment, Terraform if appropriate, CI/CD, structured logs/health checks, model lab, engineering console, accessibility and performance profiling, video demo and case study.

**Exit gate:** public URL, repeatable deployment, monitored services, concise architecture and experiment documentation.

## Dependency map
`Foundation → Data ingestion → Features → Possession engine → Submission`.

`Validated demo data → Read-only API → Timeline/Replay → Public deployment`.

The product track may prototype against synthetic data before the official assets arrive. It must not block competition completion.

## Risk register
| Risk | Impact | Mitigation |
|---|---|---|
| Challenge data release/access delayed | Model work starts later | Complete baseline, contracts, synthetic test data first |
| Only 17 public possessions | Misleading model selection | Confidence intervals, controlled errors, ablations, conservative claims |
| Ball absent ~41% of graded frames | Poor transition predictions | Context features, quality flags, temporal models |
| Cloud/public-data restrictions | Portfolio cannot show actual match | Synthetic or independently licensed demonstration |
| Solo schedule pressure | Missed submission | Competition-first critical path; defer UI/cloud |
| Complex stack too early | Slow iteration | Monorepo, modular boundaries, no premature services |

## Weekly review ritual
Record: completed outputs, failing checks, benchmark scores with dataset scope, next critical path, blockers, decisions changed. Update roadmap dates as evidence appears.
