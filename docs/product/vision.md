# Product Vision — Football Intelligence Platform

**Status:** Draft v0.1 · **Owner:** Solo developer · **Working title:** Football Intelligence Platform (not final brand) · **Updated:** 2026-10-15

## Problem
Automatic football tracking can be noisy, incomplete, and hard to interpret. A tracking feed alone does not reliably tell analysts which team *controls* the ball at each instant. Simple nearest-player heuristics fragment possessions and fail around occlusions, turnovers, and stoppages.

## Product vision
Build a reproducible football-possession intelligence engine and a premium interactive web experience for exploring **what the model predicted, when possession changed, and what evidence supports the prediction**.

## Audiences
1. **Competition evaluator:** needs a fully reproducible `frame,label` submission for More Than a Hack 2027.
2. **Football analyst / curious visitor:** needs clear match statistics, timeline navigation, and a 2D tactical replay.
3. **Engineer / technical reviewer:** needs transparent evaluation, artifacts, source code, architecture, and reliability evidence.

## Product promise
- **Predict:** produce possession predictions over an entire match.
- **Explore:** navigate possessions, stoppages, and transitions as time intervals.
- **Explain:** inspect model version, quality metrics, and input evidence without overclaiming certainty.
- **Replay:** animate tracked positions on a 2D pitch, using data legally permitted for the audience.

## Experience principles
- Dark, restrained, premium sports-analysis UI; information density without clutter.
- Pitch and timeline are primary navigation surfaces; charts support investigation.
- Distinguish **prediction** from **ground truth** and **model confidence** from certainty.
- Fast read-only exploration: inference happens offline, not per page view.
- Public demos never require or expose protected competition assets.

## Competition deliverable versus portfolio deliverable
| Track | Deliverable | Deadline / cadence |
|---|---|---|
| Competition | Valid 199,319-row prediction CSV, public reproducible code, technical report | Nov 17, 2026 |
| Portfolio | Deployed web app, replay studio, analytics, model lab, CI/CD, architecture case study | Iterative after competition |

The competition model is independently executable; the product consumes its outputs. Solo development does not imply guaranteed competition eligibility: organizer rules state teams under three cannot participate in the Innovation Challenge/Final Pitch. We may attempt a submission separately.

## Success criteria
**Competition:** pass the official submission validator, reproduce identical output from pinned code/config/data, report `spellF1` (primary) and `macroF1`, and aim to improve on the published full-match baseline (`spellF1` 0.2433) without claiming unmeasured gains.

**Engineering:** local setup from README, pinned dependencies (`uv.lock`), type/lint/unit/integration checks, clear data contracts, logged experiments, and reliable batch execution.

**Product:** visitor can pick a legally demonstrable match, scrub a possession timeline, watch a 2D replay, inspect predicted state and model provenance, and view aggregate statistics.

## Explicit non-goals for the first release
- Live match streaming or low-latency online inference.
- Player re-identification and reliable individual-player scouting analytics.
- Reimplementing tracking, object detection, or video calibration as a prerequisite.
- Microservices, Kafka, Kubernetes, or distributed Spark merely for complexity.
- Hosting licensed challenge videos/tracking in a publicly accessible application.

## Open decisions
- Final product name and visual identity.
- Legal source of the public demonstration dataset.
- Cloud provider and deployment budget; AWS is currently a preference, not an implementation.
- Which advanced ML approach generalizes best.

## Reference
- Challenge: https://github.com/metrica-sports/more-than-a-hack-2027
- Follow `RULES.md`, `DATA.md`, `EVALUATION.md`, and `SUBMISSION.md` as authoritative competition contracts.
