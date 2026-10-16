# Baseline Analysis — More Than a Hack 2027

**Status:** Observed results from local official evaluation on 2026-10-15.

## Environment and provenance
- Reference project: `https://github.com/metrica-sports/more-than-a-hack-2027`
- Command: `uv run --no-project python evaluation/run_evaluation.py`
- Environment shown in local session: macOS, Python 3.11, `uv`.
- Reference GT: `evaluation/gt/BAR-ATH_possession_gt_public.csv`.
- Output: 199,319 reference frame slots, **7,500 graded public frames**, **21 GT segments**, **17 actual possessions**, mean GT possession duration **14.2 s**.
- **TODO:** pin and record upstream Git commit SHA using `git rev-parse HEAD`, and record exact uv/python versions.

## Public-window scoreboard (observed)
| Model | macroF1 | spellF1 | Predicted possessions | Mean duration, seconds | transF1 (@±25 frames) | Fragmentation |
|---|---:|---:|---:|---:|---:|---:|
| `baseline_smooth125` | 0.5812 | **0.4242** | 16 | 18.5 | 0.1667 | 0.81 |
| `baseline_smooth50` | **0.6207** | 0.3256 | 26 | 10.8 | 0.0816 | 1.43 |
| `baseline_smooth25` | 0.6200 | 0.2868 | 36 | 7.6 | **0.2034** | 1.90 |
| `baseline_raw` | 0.5972 | 0.0378 | 131 | 2.0 | 0.1410 | 6.52 |

These are **public sample** scores only. The official documentation's `0.2433` is the published **full-match baseline**, not the local public-window result, and not a score for our own model.

## Official reference version

Repository:
https://github.com/metrica-sports/more-than-a-hack-2027

Commit: 3de6b60aeabd2475d95879a651d38b72bc4fba00

Evaluation:
uv run --no-project python evaluation/run_evaluation.py

Public-window best baseline:
spellF1 = 0.4242 (smooth125)

## What we learned
**H1 — Sequence coherence is essential.** Raw nearest-player predictions fragment the reference into 131 possessions versus 17 actual. Smoothing 125 frames reduces that to 16 and increases `spellF1` sharply on the public sample.

**H2 — Over-smoothing obscures dead-ball events.** For `smooth125`, `D` F1 is **0.1464**, recall **0.0790**; `raw` has `D` F1 **0.4197**, recall **0.3363**. We should study a dedicated dead-ball signal rather than using identical smoothing rules for all states.

**H3 — Good spell count does not imply good boundary detection.** `smooth125` matches only **7 of 17** true possessions at IoU 0.5; its transition F1 within ±25 frames is **0.1667**. Sequence segmentation remains an open problem.

**H4 — Main metric differs from macroF1.** `smooth50` has slightly higher macroF1 than `smooth25`, but `smooth125` wins the public `spellF1` ranking. Evaluate at possession level first, then inspect per-class diagnostics.

## Known threats to validity
- Only five minutes and 17 possessions; a difference in `spellF1` may be unstable.
- Public and private match windows may have different distributions.
- Choosing parameters only to win the public sample risks overfitting.
- `X` is filled by the official scorer before spell evaluation and counts as a miss for macroF1 on graded frames.

## Hypotheses and planned experiments
| Hypothesis | Planned experiment | Diagnostic |
|---|---|---|
| Separate live/dead classifier helps | Compare dead-ball rules/features vs single-model classifier | `D` precision/recall and spellF1 |
| Spatial dynamics improve control | Add relative ball proximity, velocity, team motion features | Transition timing and team accuracy |
| Temporal decoding beats majority vote | Compare HMM/semi-Markov versus fixed smoothing | spellF1, fragmentation, latency |
| Missing-ball-aware inference is robust | Segment results by ball-observed versus missing windows | Error rates by input availability |
| Smart Tagging contributes signal | Feature ablation with/without tagging | spellF1 and failure modes |

## Next commands and bookkeeping
```bash
# Run inside the official challenge clone:
git rev-parse HEAD
uv --version
uv run --no-project python evaluation/run_evaluation.py --bootstrap 1000
```
Record the bootstrap confidence outputs with the actual command and scope. Do not report them as full-match uncertainty bands. Record any new experiment with code commit, configuration, generated output, and evaluation details.

## Candidate evaluation template
| Run ID | Commit | Feature set | Model | Decoder | Public spellF1 | Public macroF1 | Main failure | Notes |
|---|---|---|---|---|---|---|---|---|
| pending | — | — | — | — | — | — | — | — |

## Supporting official documents
- `CHALLENGE.md`: label and possession semantics.
- `EVALUATION.md`: exact metric definition.
- `DATA.md`: asset alignment and known quality issues.
- `SUBMISSION.md`: strict CSV and reproducibility contract.
- `RULES.md`: algorithms, competition restrictions, data licensing.
