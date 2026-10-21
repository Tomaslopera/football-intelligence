# Metrica integration engineering audit — 2026-10-20

## Final tactical quality review — current checkpoint

The user completed the full local tactical audit at
`datasets/processed/metrica/BAR-ATH/tactical-real-full-01/audit.json`.
The agent reviewed sanitized aggregates and executed read-only local DuckDB
diagnostics over processed Parquet, returning aggregates and missing-interval
boundaries only. No raw EPTS records or video were opened by the agent.
The corrected full dataset is now `tactical-real-full-02`; use it for future
work. `tactical-real-full-01` is preserved as the original ingestion record
with incorrectly scaled player speeds. Historical checkpoints below are
superseded by the resolved source contract and corrected artifact evidence.

### Acceptance decisions

| Gate | Decision | Evidence or blocker |
|---|---|---|
| Full tactical ingestion/storage | PASS locally | 199,319 source/stored frames; canonical 0–199318; no gaps, duplicates or orphans |
| Feature implementation and real canonical consistency | PASS locally | Every feature independently recomputed from persisted canonical inputs; zero mismatches |
| Phase 1.5 final closure | PASS locally | Full source ingestion verified; documented source-unit correction applied to new canonical artifacts with provenance |
| Phase 2.1 final closure | PASS locally | Corrected canonical tracking regenerated through causal feature pipeline; independent recomputation has zero mismatches |
| GitHub CI for pending changes | UNVERIFIED | No commit/push or CI execution performed |
| Phase 2.2 readiness | READY to begin planning/experimentation | Use corrected `tactical-real-full-02`; no model training performed |

These decisions distinguish an implementation passing its contracts from
proof that the provider's declared unit is physically correct. No model was
developed, selected or trained.

### Resolved source-speed convention and corrected artifacts

The official [challenge DATA.md at the reviewed commit](https://github.com/metrica-sports/more-than-a-hack-2027/blob/3de6b60aeabd2475d95879a651d38b72bc4fba00/DATA.md#automatic-tracking-data-atd)
explicitly defines the Kloppy EPTS player-speed columns as **m/s**. The same
statement was verified in the current upstream public documentation. This
authoritative evidence, together with the measured factor-of-3.6 discrepancy,
resolves the conflict with the XML `kph` declaration for this export.
The earlier review should have reconciled this existing documentation before
requiring further provider confirmation.

`audit_metrica()` now selects the documented m/s source contract when the
caller explicitly identifies match `BAR-ATH` and source `tactical`. The
generic loader still converts genuine kph exports by 3.6. It also supports
an explicit `speed_unit_override` plus required evidence for documented
exceptions. No unit is inferred from observed speeds or track-slot numbers.
Lineage retains `source=kph`, `effective_source=m/s`, `canonical=m/s`, and
the official evidence link. Ordinary explicit m/s exports remain unchanged.

The agent rebuilt the full processed dataset locally without opening raw
EPTS files: old canonical player speeds were multiplied by 3.6 to undo the
previous conversion, then the existing canonical reader, causal feature
pipeline and quality checks ran again. This is a **rebuild from validated
canonical data**, not a new raw-source ingestion run. A synthetic regression
proves that the rebuild equals a direct source load with the documented unit
override. Upstream audit and file fingerprints bind the correction to the
already validated full source run. Reapplying the same effective unit is
rejected; original files and `tactical-real-full-01` are unchanged.

Corrected evidence in `tactical-real-full-02/audit.json` and
`tactical-real-full-02/quality-review.json`:

- 199,319 frames, 0–199318; all original counts, missingness and coordinate
  diagnostics preserved; frame Parquet copied byte-for-byte.
- Player fields other than `speed_mps` verified unchanged batch by batch.
- Corrected consecutive-step reported-speed median **1.33548 m/s**, maximum
  **11.29383 m/s**; motion/reported ratio **1.00348** (the speed >=0.1 filter
  includes a different set after correction).
- Median absolute motion disagreement **0.10382 m/s**; multiplying corrected
  speeds by 3.6 would worsen it to **3.46618 m/s**.
- All 14 feature columns independently match corrected canonical tracking
  within 1e-8 with null-aware comparison, on all 199,319 distinct keys.
- Tracking/feature schemas and fingerprints pass. The 15 m/s reported-speed
  threshold remains unchanged; zero reported-speed threshold flags.
- Rebuild plus verification completed in **20.08 seconds**. Original source
  ingestion remains the user's roughly 71-second / 8.76-GiB measured run.

Reproduce a direct raw-source audit locally using the original command and a
fresh output directory: `BAR-ATH`/`tactical` now selects the documented
contract automatically. For other callers of `load_metrica_epts()`, pass
`speed_unit_override="m/s"` and the evidence URL for this particular export.
The raw EPTS pair has not been reopened by the agent.

The derived correction was executed as:

```bash
uv run python scripts/rebuild_metrica_speed_units.py \
  --previous datasets/processed/metrica/BAR-ATH/tactical-real-full-01 \
  --output datasets/processed/metrica/BAR-ATH/tactical-real-full-02 \
  --effective-unit m/s \
  --evidence 'https://github.com/metrica-sports/more-than-a-hack-2027/blob/3de6b60aeabd2475d95879a651d38b72bc4fba00/DATA.md#automatic-tracking-data-atd — documents Kloppy EPTS speed columns in m/s; supported by measured motion/reported ratio 3.60216'
```

The original low-speed dataset is retained for provenance and should not feed
Phase 2.2. Ball-motion outliers, missing-ball intervals and out-of-bounds
coordinates are unchanged, documented source-quality limitations rather
than feature implementation failures. Local phases are accepted with these
limitations; GitHub CI remains a separate unverified gate.

Final source-correction checks: `uv run ruff format --check .` (68 files),
`uv run ruff check .`, `uv run mypy src/` (25 source files) all pass;
`uv run pytest -v` passes **157 tests in 1.54 s**. Seven added regression
cases cover the documented match/source policy, required override evidence,
genuine-kph default preservation, direct-ingestion/rebuild equivalence,
original-run preservation and rejection of duplicate correction.
`git diff --check -- src scripts tests docs` passes. No changes are staged.

### Verified full-run measurements

- Source and processed frames: **199,319**, canonical **0–199318**.
- Ball visible: **113,488**; missing: **85,831**; coverage **56.9379%**.
- Positioned player observations: **3,782,421**. Stored missing positions:
  zero; this does not mean all players/slots were always observed. Ingestion
  omits slots with neither position nor speed.
- Frame gaps, duplicate frames, duplicate player observations and orphans: zero.
- Out-of-bounds positions retained: **4,964 ball**, **43,911 player**.
- Original run: **70.8503 s**, peak process RSS **8,966.66 MiB = 8.7565 GiB**.
- Tracking and feature file fingerprints match the original audit; schemas
  match the explicit contracts, including feature schema 1.0/causal metadata.

### Initial player-speed investigation — resolved above

Kloppy 3.19.1's EPTS reader/deserializer, coordinate transformer and DataFrame
exporter preserve reported speed numbers. Synthetic dependency guards again
confirm that 36/72 with either XML unit stays 36/72 in Kloppy. The adapter
divides by 3.6 exactly once for declared `kph`; ingestion, storage and features
do not apply another conversion. Existing regressions verify both `kph` and
`m/s`, zeros/nulls, downstream features and the 15 m/s quality threshold.

However, **the real input's unit declaration is suspect**. Across 3,412,119
consecutive same-slot steps with reported speeds, stored median speed is
0.37097 m/s and maximum 3.13717 m/s. Across all consecutive same-slot
position steps (including those without reported speed), median derived speed
is 1.27798 m/s. For steps with stored speed >=0.1 m/s and displacement speed
0.1–15 m/s, median motion/reported ratio is **3.60216**. For steps with
displacement speed <=15 m/s, median absolute disagreement is **0.97675 m/s**
at the stored scale versus **0.10382 m/s** after multiplying stored speeds
by 3.6. This strongly suggests the source numbers may already represent m/s
despite `kph` metadata. It is **not proof of an extra Kloppy conversion**.

Same-slot motion is a diagnostic, not persistent identity or ground truth;
2,751 consecutive slot steps exceed 15 m/s and may contain tracking jumps.
Smoothing or reporting offsets could also affect comparisons. No scale was
silently corrected during the initial investigation. The official DATA.md
statement subsequently supplied the authoritative source evidence, and the
explicit correction is recorded above. Zero reported-speed threshold flags
in the original run alone did not resolve the discrepancy.

### Ball-speed anomalies

All **1,151 estimates >50 m/s** are independently reproduced from adjacent,
visible canonical ball positions at 25 FPS: **zero invalid/gapped motion
contexts**. They imply displacements from **2.00019 to 5.34742 m** per frame
(median **2.40206 m**), maximum estimate **133.68548 m/s**.

- **87 contiguous runs**, median 13 frames (0.52 s), longest 29 (1.16 s).
- No single-frame runs; 55 anomalous frames belong to runs at least one second.
- Three anomaly frames have missing ball tracking two frames earlier;
  none has a missing next observation. Missing endpoints are never bridged.
- 69 estimates involve an out-of-bounds endpoint.
- Zero jump-and-return candidates under the explicit diagnostic: next step
  also >50 m/s while the two-step previous-to-next average is <=15 m/s.

These are sustained fast source-coordinate trajectories, not a feature gap
or FPS-conversion bug. The aggregates do not establish physical ball speed
or a unique cause such as a tracking jump, calibration error or airborne
projection. No video/source adjudication was performed. Keep the estimates,
nulls and outliers as diagnostics; no clipping, interpolation or removal.

### Longest missing-ball intervals

Intervals are canonical, start-inclusive/end-exclusive. Player counts are
observed slots with positions, not known individuals.

| Interval | Frames | Seconds | Mean visible players | Min–max | Public timeline context |
|---|---:|---:|---:|---:|---|
| [190630,199319) | 8,689 | 347.56 | 14.36 | 2–35 | After published final whistle (190197) |
| [157546,163083) | 5,537 | 221.48 | 15.95 | 4–24 | Within published second-half bounds |
| [5108,10643) | 5,535 | 221.40 | 14.54 | 6–31 | Before published first kickoff (11185) |
| [0,4192) | 4,192 | 167.68 | 9.53 | 4–19 | Before first kickoff |
| [58081,61547) | 3,466 | 138.64 | 12.10 | 4–23 | Within published first-half bounds |

The longest streak is a post-match coverage issue, not a tracking frame gap.
Large within-half missing intervals remain relevant for later inference;
neither interval boundaries nor phase membership establish possession/dead ball.
All missing-streak values match independent recomputation.

### Feature and out-of-bounds preservation

Read-only DuckDB recomputation covers ball visibility, both team counts,
nearest distances and associated speeds, distance advantage and its change,
ball displacement/speed, both team means and missing streaks. All **14**
columns match at every joined frame (floating tolerance **1e-8**, null-aware).
There are 199,319 distinct feature keys and zero missing/extra keys. All
4,964 out-of-bounds ball observations remain visible to feature extraction;
all player coordinates are retained in canonical Parquet and included in
independent geometry computations. Synthetic regressions cover retained
out-of-bounds ball/player positions and detect deliberately corrupted features.

### Memory decision and changes

**Defer a production memory rewrite.** The full local offline job completed
in about 71 s; no failure or concrete resource limit was supplied. Record
8.76 GiB as a substantial limitation: one job at a time, adequate local RAM
required, unsuitable for request-time processing or small serverless runtimes.
Optimize before concurrent/multi-match workloads or upon measured memory
pressure. No claim is made that 8.76 GiB is acceptable on every machine.

No confirmed production transformation bug was found in this review, so
none was changed. Added `tracking/review.py`,
`scripts/review_metrica_quality.py`, `scripts/check_metrica_speed_sample.py`
and synthetic tests. The reviewer uses DuckDB's 512 MB buffer budget and
private temporary spill space; that is not a total-process memory guarantee.
The source-comparison helper is provided for user-run local execution and
has only been executed against synthetic EPTS by the agent.

Current verification completed:

- `uv run ruff format --check .`: passed, 65 files formatted.
- `uv run ruff check .`: passed.
- `uv run mypy src/`: passed, 24 source files.
- `uv run pytest -v`: **150 passed in 1.40 s**, including three new review tests.
- `git diff --check -- src scripts tests docs`: passed; no staged changes.

The review regressions cover independent feature recomputation, deliberate
feature/null corruption detection, fingerprint changes, retained out-of-bounds
ball/player observations, missing intervals and a synthetic user-run direct
Kloppy/adapter/stored speed comparison. Existing dependency/unit tests were
rerun. GitHub CI is a separate unexecuted gate.

Artifacts added locally:

- `datasets/processed/metrica/BAR-ATH/tactical-real-full-01/quality-review-01.json`
  (initial aggregate review).
- `datasets/processed/metrica/BAR-ATH/tactical-real-full-01/quality-review-02.json`
  (adds verified schemas/fingerprints and anomalous-run aggregation).

Reproduce the processed-data review with a new output filename:

```bash
uv run python scripts/review_metrica_quality.py \
  --audit-directory datasets/processed/metrica/BAR-ATH/tactical-real-full-01 \
  --output datasets/processed/metrica/BAR-ATH/tactical-real-full-01/quality-review-03.json
```

To compare real direct-Kloppy, adapter and stored sample speeds locally without
sharing rows (pending; **not executed on real inputs by the agent**):

```bash
uv run python scripts/check_metrica_speed_sample.py \
  --metadata datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.xml \
  --tracking datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.txt \
  --audit-directory datasets/processed/metrica/BAR-ATH/tactical-real-full-01 \
  --limit 12000 \
  --output datasets/processed/metrica/BAR-ATH/tactical-real-full-01/source-speed-check-01.json
```

That check compares declared-unit conversion and stored values. Even zero
mismatches cannot prove that the provider declared the correct physical unit.
Physical scale is now resolved through the documented source contract above.
No staging, commits, pushes,
cloud work, broadcast synchronization or video processing were performed.

## Historical initial outcome and evidence boundary

**Repository-only audit. Phase 1.5 remains incomplete; Phase 2.2 is not yet
ready for real-data experimentation.** No ML training was performed.

The separate official checkout's `RULES.md` says enrollment terms govern
match-data permissions and are not restated in the repository. Those terms
were unavailable. Following the task's explicit fallback, no licensed XML,
TXT, homography, Smart Tagging, MP4, or restricted derived data was opened
or processed. No actual dataset presence, metadata, team assignments, frame
counts, real quality statistics or real performance measurements are claimed.
No raw records were sent to hosted AI services.

This report documents implemented local verification tooling and synthetic
evidence. Run the commands below yourself after confirming local processing
permissions. Do not paste source records or private failure traces into a
hosted agent conversation.

## Repository baseline and reviewed architecture

- Branch: `main`. Pre-existing changes: `.gitignore` and `.DS_Store`.
  Both were preserved without edits by this audit.
- `git check-ignore` confirms `datasets/raw/`, `datasets/processed/` and
  `datasets/generated/` are ignored. `git ls-files datasets` returned no
  tracked dataset files. Ignore rules do not prevent deliberate forced adds.
- Read `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, `system.md`, `data-flow.md`,
  feature documentation, and the tracking, feature and possession modules.
- Existing entry points: `tracking.synthetic.generate_tracking_table`,
  `tracking.metrica.load_metrica_epts`, `tracking.ingestion.iter_tracking_frames`,
  `tracking.alignment` validators, `tracking.storage` Parquet read/write,
  `tracking.analytics.tracking_summary`, `tracking.quality.analyze_tracking_quality`,
  `tracking.lineage` fingerprint/report functions, `features.pipeline.build_feature_dataset`,
  and `possession.competition.write_submission_csv`.
- Reviewed all four feature modules and possession alignment, segments,
  competition export and reference masks. Reviewed synthetic storage, quality,
  feature and competition scripts plus their tests.
- Architecture remains a Python modular monolith with independent local
  batch processing. No cloud services, frameworks or dependencies were added.

Documentation discrepancies: architecture tables still marked implemented
storage, quality, features and possession functionality as planned; the
context used an older dataset directory name. Updated these descriptions
and linked the current audit checkpoint. Real integration remains unverified.

## Public official evidence, not real-file measurements

### Speed-unit compatibility correction

Subsequent local inspection reported by the user found `normalized` position
units and **`kph` speed units in the real tactical XML**. This contradicts the
earlier assumption that source speeds are always m/s. The agent has not opened
the licensed XML or rerun the real audit; this finding comes from the user's
real-data run.

Code inspection of locked Kloppy **3.19.1** confirms that its EPTS
`reader.read_raw_data()` parses floats, `MetricaEPTSTrackingDataDeserializer`
copies the `_s` value into `PlayerData.speed`, `DatasetTransformer` preserves
that speed, and `FrameToDictTransformer` exports it unchanged. Controlled
synthetic EPTS tests confirm raw speeds 36 and 72 remain 36 and 72 in Kloppy's
DataFrame under both `kph` and `m/s` XML units.

`load_metrica_epts()` now resolves units from the XML and converts `kph`
speed columns by dividing by **3.6**, after column normalization and before
canonical ingestion. The `m/s` path passes through unchanged. Both metadata
inspection and loading reject unknown, missing or conflicting declarations
for a declared speed channel. No speed channel is permitted only when there
are no observed speed values. The audit lineage records source and canonical
speed units. Canonical models, Parquet values, nearest-player/team-speed
features and quality thresholds remain in **m/s**. Derived ball speed remains
physical displacement times FPS. This does not add source ball-speed parsing
that Kloppy's EPTS deserializer currently omits.

Regressions cover dependency behavior (to flag future double conversion),
36/72 kph → 10/20 m/s, unchanged 10/20 m/s, missing and zero speeds, repeated
sample/full loads, source immutability, feature/Parquet round trips and the
15 m/s quality threshold. The real 100-frame rerun is still pending. Run it
locally into a fresh output directory:

```bash
uv run python scripts/audit_metrica.py \
  --metadata datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.xml \
  --tracking datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.txt \
  --source tactical --limit 100 --expected-frames 199319 \
  --output "datasets/processed/metrica/BAR-ATH/tactical-sample-speed-fix-$(date +%Y%m%dT%H%M%S)"
```

Speed-fix verification: `uv run pytest tests/test_metrica.py
tests/test_metrica_audit.py -v` passed 33 tests. Final
`uv run ruff format --check .`, `uv run ruff check .`, and
`uv run mypy src/` passed; `uv run pytest -v` passed all 147 tests in 1.34 s.
No raw assets were modified and no commit or push was performed.

Reviewed the separate local challenge checkout at
`../more-than-a-hack-2027`, commit
`3de6b60aeabd2475d95879a651d38b72bc4fba00`: `RULES.md`, `DATA.md`,
`starter/load_atd.py`, submission validator and public evaluator.
This audit did not fetch or verify a newer upstream revision.

| Item | Official checkout states | This audit independently measured |
|---|---|---|
| Tactical frames / FPS | 199,319 / 25 | Not measured on real assets |
| Tactical ATD frame range | 1–199,319 | Not measured on real assets |
| Canonical conversion | ATD minus one | Existing tests and synthetic EPTS pass |
| Pitch | XML 105 × 68 m; `games.py` 105.3 × 68 m | Synthetic XML only; runner uses XML, records dimensions |
| Tactical slots / ball visibility | 46 / 56.9% | Not measured on real assets |
| Broadcast frames / slots / visibility | 164,488 / 51 / 50.5% | Not measured on real assets |
| Public reference | 199,319 rows; 7,500 published labels | Verified against public CSV |

The public reference reader verified H=3,454, A=2,577, D=1,469 in
`[11185,18685)`. Outside the published window, `X` becomes unavailable
ground truth (`None`, grading mask false). These are distinct from algorithm
predictions of unknown possession. The 7,500 published frames differ from
the official full-match evaluation's 158,857 graded half frames.

Public documentation identifies Barcelona as home and Athletic as away.
Actual slot-to-team membership remains unknown until source XML is inspected
locally. The new metadata reader uses `Score.idLocalTeam/idVisitingTeam`,
`Teams.Team.id`, and `Players.Player.teamId`. It never uses slot ranges,
shirt numbers, player names, or XML team ordering to assign a side.
Slots remain channels, not persistent player identities.

## Findings and changes

| File | Change and reason |
|---|---|
| `scripts/inspect_metrica.py` | Removed raw table and frame-row printing; added sample limit and aggregate missing counts; console failures contain exception type only |
| `tracking/metrica.py` | Added typed `MetricaMetadata` and explicit XML metadata resolver; reject absent/ambiguous team evidence, unsupported IDs or units; existing DataFrame loader interface unchanged |
| `tracking/audit.py` | New local orchestration using existing canonical/storage/quality/features components; full prefix continuity scan, source/stored counts, exact tracking round trip, schemas, feature alignment, distributions, fingerprints, timing and peak RSS |
| `scripts/audit_metrica.py` | Sample/full CLI; requires a fresh output beneath ignored processed data, rejects output containing inputs, prints no records, retains failure details locally |
| `tests/epts_fixture.py` | Hand-authored three-frame XML/TXT generator, two interleaved team slots, reversed team order, missing ball and missing player position |
| `tests/test_metrica.py` | Actual Kloppy parsing of synthetic EPTS, sample limits, explicit mapping, and five unsupported/ambiguous metadata regressions |
| `tests/test_metrica_audit.py` | Sample/full orchestration for tactical/broadcast identity, counts, physical distances, nulls, immutable inputs, output collision, frame gaps/duplicates, XML truncation, inspection output and ignore protections |

Concrete pre-existing defect: the inspector printed restricted source rows.
The existing adapter/ingestion/storage/feature path passed the new synthetic
EPTS test; no real-data parsing defect is asserted. Two integration hazards
are now guarded: Kloppy can infer side from team order without Score metadata,
and can stop at the final XML format boundary before consuming trailing TXT
records. The latter was reproduced using a synthetic shortened XML boundary.

No performance rewrite was made. Current ingestion materializes Pandas row
dictionaries, storage builds all frame/player dictionaries, deserialization
builds complete Python object collections, and feature storage materializes
rows. The audit deliberately measures that implementation, including round
trips, rather than claiming bounded memory. Full-match memory remains a risk.

## Executed verification

The first baseline attempts could not access uv's cache under the filesystem
sandbox; they were rerun with approved cache access. This was an environment
failure, not a test or data failure.

| Command | Result |
|---|---|
| `uv run ruff format --check .` | Baseline: 56 files already formatted |
| `uv run ruff check .` | Baseline passed |
| `uv run mypy src/` | Baseline: 22 source files passed |
| `uv run pytest -v` | Baseline: 118 passed |
| Final `uv run ruff format --check .` | Passed: 61 files already formatted |
| Final `uv run ruff check .` | Passed |
| Final `uv run mypy src/` | Passed: 23 source files |
| Final `uv run pytest -v` | Passed: 136 tests in 0.98 s |
| `git diff --check -- src scripts tests docs` | Passed for audit changes |
| `uv run pytest tests/test_metrica.py tests/test_metrica_audit.py -q` | Focused: 22 passed before final distance assertions; final full suite also covers these |
| `uv run python scripts/demo_competition_integration.py --official-repo ../more-than-a-hack-2027` | Passed; full-length synthetic submission and public reference counts verified |
| `uv run python ../more-than-a-hack-2027/evaluation/validate_submission.py datasets/generated/competition-integration/synthetic_submission.csv` | Passed: 199,319 rows, frames 0–199,318 |
| `uv run python ../more-than-a-hack-2027/evaluation/run_evaluation.py --results datasets/generated/competition-integration --gt public` | Passed; synthetic integration diagnostic only |

The evaluator produced synthetic spellF1 0.0242. This has no ML performance
meaning; no training, model selection or real tracking alignment was tested.
Generic possession segments remain distinct from official spells; the official
evaluator is the authority on spell scoring and unknown-label filling.

Whole-tree `git diff --check` reports trailing whitespace on `.gitignore:24`
from the pre-existing user change. It was preserved. Nothing is staged.

Development-only failures were corrected before delivery: the new synthetic
fixture initially omitted Kloppy-required period metadata; the new audit's
NumPy check initially included a timedelta column. The fixture now supplies
a period, and numeric conversion is explicit. No pre-existing quality-suite
failure or licensed-data failure was observed.

## Synthetic audit statistics and artifacts

A persistent synthetic run used the hand-authored EPTS generator and called
`audit_metrica(..., limit=None, expected_frames=3)` directly. Results:

- 3 canonical frames, range 0–2; ball visible on 2/3 frames (66.67%).
- 5 positioned player observations; one stored player with missing position.
- No gaps, duplicates, orphans, out-of-bounds coordinates or suspicious speeds.
- Nearest-team distances available on 2 frames; ball motion estimates missing
  on all 3 because missing ball tracking interrupts consecutive observations.
- Elapsed 0.0374 s; process lifetime peak RSS about 152.34 MiB on macOS.
  This includes interpreter/library startup and is not a full-match estimate.

Artifacts, local and ignored:

- `datasets/generated/repository-audit-2026-10-20/synthetic.xml`
- `datasets/generated/repository-audit-2026-10-20/synthetic.txt`
- `datasets/generated/repository-audit-2026-10-20/synthetic-tactical/audit.json`
- Same synthetic audit directory: `tracking/{frames,players}.parquet`,
  `features/features-v1.0.parquet`, `quality/quality.{json,md}`.
- `datasets/generated/competition-integration/synthetic_submission.csv`.
- The official evaluator also writes its own `evaluation/scoreboard.csv` and
  `evaluation/reports/` under the separate challenge checkout. These contain
  public-reference/synthetic evaluation outputs. No commits were made there.

No real-data artifacts were generated under `datasets/processed/`.

## Local execution runbook

Execute from the project root after reviewing enrollment permissions. Keep
assets immutable. Each output directory must be new; use a fresh run name if
it already exists. First inspect the sample report locally. Do not run full
processing until metadata, mapping, units and sample compatibility pass.

```bash
uv run python scripts/audit_metrica.py \
  --metadata datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.xml \
  --tracking datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.txt \
  --source tactical --limit 100 --expected-frames 199319 \
  --output datasets/processed/metrica/BAR-ATH/tactical-sample
```

The sample scans all frame prefixes to verify file continuity but asks Kloppy
to materialize only the first 100 records. The expected count is an explicit
check against the official documentation, never a replacement for counting.

```bash
/usr/bin/time -l uv run python scripts/audit_metrica.py \
  --metadata datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.xml \
  --tracking datasets/raw/metrica/BAR-ATH/tactical/BAR-ATH_tactical_atd.txt \
  --source tactical --full --expected-frames 199319 \
  --output datasets/processed/metrica/BAR-ATH/tactical
```

`/usr/bin/time -l` is macOS-specific; the audit also records elapsed time and
process peak RSS itself. Full processing retains the existing memory-heavy
implementation. Monitor memory locally; a killed process may leave partial
outputs without `audit.json`. Only `audit.json` with status `passed` indicates
completion; it does not mean all spatial diagnostics are physically plausible.

Expected local outputs:

```text
datasets/processed/metrica/BAR-ATH/tactical/
  tracking/frames.parquet
  tracking/players.parquet
  features/features-v1.0.parquet
  quality/quality.json
  quality/quality.md
  audit.json
```

The JSON includes source count, processed range, source missingness, explicit
mapping, dimensions/FPS, quality statistics, feature availability and
min/median/p99/max distributions, stage timings, process peak RSS, source and
tracking SHA-256 fingerprints and a feature fingerprint. Supply optional
`--git-commit <reviewed-commit>` for commit provenance. It defaults to null;
pending uncommitted code must also be preserved separately for reproducibility.

After tactical success, inspect broadcast independently:

```bash
uv run python scripts/audit_metrica.py \
  --metadata datasets/raw/metrica/BAR-ATH/broadcast/BAR-ATH_broadcast_atd.xml \
  --tracking datasets/raw/metrica/BAR-ATH/broadcast/BAR-ATH_broadcast_atd.txt \
  --source broadcast --limit 100 --expected-frames 164488 \
  --output datasets/processed/metrica/BAR-ATH/broadcast-sample
```

If that sample passes, repeat with `--full` instead of `--limit 100` and output
`datasets/processed/metrica/BAR-ATH/broadcast`. No broadcast MP4 is required.
Reuse the same adapters, canonical models, storage, quality and features;
derive metadata and frame bounds independently. No tactical/broadcast frame
join or synchronization is implemented or implied.

## Remaining acceptance gates and limitations

1. Confirm applicable enrollment terms. Perform actual tactical sample and
   full runs locally, then review source metadata membership and team names.
2. Verify actual 199,319 frames, 25 FPS, dimensions, canonical continuity and
   source/stored counts; compare real schema with the documented conventions.
3. Review real missing ball/player coverage, speed/coordinate outliers and
   feature distributions. Diagnostics preserve outliers; they do not establish
   that the observation is invalid. No interpolation or silent removal occurs.
4. Existing quality reports are dataset-wide. They do not report windowed
   quality or all-absent slot opportunities: ingestion omits slots with neither
   position nor speed, while source missing counts retain their column nulls.
5. Full source-to-table sensor equality is not established: Kloppy's EPTS
   deserializer does not forward reported ball speed into Frame.ball_speed;
   the existing ingestion path only uses ball position. Derived ball speed
   is causal displacement × FPS. Review any additional source sensor columns
   locally; this audit validates supported position/player-speed contracts.
6. Unsupported XML namespaces, identifiers or units fail explicitly rather
   than being guessed or converted. Actual conventions remain unverified.
7. Review memory and elapsed time before justifying any streaming changes.
   Process peak RSS does not isolate each stage. No real scalability evidence
   exists from the three-frame synthetic run.
8. Validate actual tactical video/homography alignment locally; only the
   documented offset and synthetic frame conversion were checked here.
9. Inspect broadcast only after tactical success. No automatic synchronization.
10. Review GitHub CI separately; no CI run, commit, stage, push or deployment
    was performed. Keep raw, processed and generated artifacts out of Git.

Documentation updated: project status/context, architecture system/data-flow,
and this report/runbook. Phase 1.5 closure and Phase 2.2 readiness require the
remaining real-data evidence; synthetic success alone is insufficient.
