# ADR-0001 — Modular Monolith with Independent Batch Inference

- **Date:** 2026-10-15
- **Status:** Proposed / accepted for Phase 0 design; revisit if requirements change
- **Deciders:** Solo developer

## Context
We are implementing a solo engineering project with a hard competition deadline (Nov 17, 2026) and an ambitious long-term product goal (interactive football analysis). The official task is offline batch inference over 199,319 frames, not a live streaming service. Clean module boundaries and reproducibility matter; operating many services would consume time without improving the submission.

## Decision
1. Adopt **one Python codebase organized by modules** (`core`, `data`, `features`, `intelligence`, `analytics`) with explicit contracts.
2. Run ingestion/training/prediction/export as **independent local batch CLI processes**.
3. Add **one FastAPI service** and **one Next.js frontend** later, after the competition-critical path is stable.
4. Store analytical data in Parquet; use DuckDB locally. Add PostgreSQL only for application metadata and read-serving requirements.
5. Keep `uv` and committed `uv.lock` for reproducible Python environment setup.
6. Maintain the official scorer as an unmodified, pinned upstream reference.

## Alternatives considered
| Alternative | Rejected / deferred because |
|---|---|
| Microservices from day one | Deployment/observability/network complexity without independent scaling need |
| All logic in notebooks | Weak contracts, testing, reproducibility and production evolution |
| Pure single-script solution | Faster initially but hard to test and extend into product |
| Real-time streaming pipeline | Competition is batch/offline; no low-latency requirement |
| Java/Spring Boot now | Extra language boundary slows competition-critical Python workflows |

## Consequences
**Positive:** faster feedback loops, fewer operational moving parts, simpler local debug/CI, clean transition to visual product.

**Trade-offs:** application modules share a deployment/repository; scaling independently later requires extraction; intentional attention to interfaces to prevent tight coupling.

## Enforced invariants
- Exporter cannot depend on web app, API, database or remote infrastructure.
- Domain contracts do not depend on ML frameworks or HTTP layers.
- Model artifact is versioned; generated predictions have run identity and provenance.
- Public demo data is legally permitted; restricted inputs never flow into public artifacts.

## Revisit triggers
- Realtime inference becomes an actual requirement.
- Separate teams own services or independently scaled workloads emerge.
- Workloads exceed local/single-job compute budget.
- A specific cloud-managed service materially reduces complexity rather than increasing it.

## Validation
Documented clean install, smoke-test offline exporter, tests for domain and frame alignment, self-contained CI on synthetic fixtures; compare runtime/resource use after access to actual data.
