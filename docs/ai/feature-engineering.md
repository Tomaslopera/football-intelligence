# Football Feature Engineering — Phase 2.1

**Status:** Implemented and tested with synthetic data and the full real tactical
recording. Independent recomputation matches all 14 feature columns on 199,319
frames. Phase 2.1 passes local acceptance using corrected
`tactical-real-full-02`; GitHub CI for the pending changes is unverified.

## Real tactical quality checkpoint

The local full run (`tactical-real-full-01`) has 56.94% ball coverage and
3,782,421 positioned player observations. Versioned feature schemas, keys,
nulls and all geometric/causal values match independent SQL recomputation
within 1e-8. Tracking and feature fingerprints still match the original audit.

The 1,151 ball-speed estimates above 50 m/s are reproduced from adjacent
visible positions, not missing-frame bridging. They form 87 sustained runs;
their physical cause is unverified, and values remain untouched. Missing-ball
streak [190630,199319) lasts 8,689 frames (347.56 s), after the published final
whistle. Other long within-half missing intervals remain an inference concern.
Out-of-bounds observations (4,964 ball and 43,911 player) are retained.

The initial dataset's reported-speed scale was low by 3.6. The official
challenge DATA.md explicitly defines Kloppy EPTS speeds as m/s, resolving the
conflict with this export's XML kph declaration. The BAR-ATH tactical source
contract now records that correction and preserves source speed numbers.
Generic genuine-kph sources still divide by 3.6. Existing speed features and
the 15 m/s quality threshold retain their canonical definitions.

Use `tactical-real-full-02`, rebuilt from validated canonical input with
upstream fingerprints and then regenerated through the causal feature
pipeline. It has a reported-speed median 1.33548 m/s, maximum 11.29383 m/s,
and motion/reported ratio 1.00348. All 14 feature columns match independent
recomputation. Preserve `tactical-real-full-01` for provenance, not model input.

The 70.85 s / 8.76 GiB full audit is acceptable as a completed offline local
verification with a documented memory limitation, not a serving workload.
No feature algorithm or original raw source asset was modified. The new
derived artifact corrects only the reported-player-speed scale and rebuilds
features with recorded official-source evidence.
See [complete evidence and acceptance decisions](../research/metrica-integration-audit.md).

## 1. Purpose

Phase 2.1 introduces a model-independent feature engineering pipeline for football possession inference.

It transforms canonical tracking observations into reproducible, structured feature datasets that can support multiple modeling approaches.

The phase does not select, train, or evaluate a possession prediction model.

The initial feature set is a baseline for experimentation, not a claim that these are the optimal football possession features.

## 2. Architecture

The feature pipeline extends the existing Data Engineering foundation.

```text
Synthetic Metrica-shaped tracking table
    |
    v
iter_tracking_frames()
    |
    v
Canonical TrackingFrame objects
    |
    v
extract_geometric_features()
    |
    v
extract_temporal_features()
    |
    v
FeatureRow
    |
    v
Versioned Parquet feature dataset
    |
    +--> DuckDB analytical queries
    |
    +--> Future ML experiment datasets
```

Primary implementation files:

- `src/football_intelligence/features/geometry.py`
- `src/football_intelligence/features/temporal.py`
- `src/football_intelligence/features/storage.py`
- `src/football_intelligence/features/pipeline.py`

The pipeline is independently executable and separate from future API request handling.

EPTS source speed units are resolved upstream in `load_metrica_epts()`.
Kloppy 3.19.1 preserves source speed numbers: declared `kph` is divided by
3.6 once at that adapter boundary, while `m/s` passes through unchanged.
The real tactical XML's `kph` declaration was reported by the user; the
documented BAR-ATH tactical exception treats the numbers as m/s and records
both declared and effective units. Features receive canonical m/s values
and perform no additional conversion.
Ball speed estimated from displacement and FPS is already in m/s.

## 3. Geometric Features

The geometric extractor accepts a canonical `TrackingFrame` and `MatchMetadata`.

Coordinates are normalized to the pitch and must be converted into physical distances using pitch dimensions.

For positions `(x1, y1)` and `(x2, y2)`:

```text
dx_m = (x1 - x2) * pitch_length_m
dy_m = (y1 - y2) * pitch_width_m

distance_m = sqrt(dx_m² + dy_m²)
```

### Feature definitions

| Feature | Definition | Unit |
|---|---|---|
| `ball_visible` | Whether the current frame contains a ball position | Boolean |
| `home_players_visible` | Home-team observations with valid positions | Count |
| `away_players_visible` | Away-team observations with valid positions | Count |
| `nearest_home_distance_m` | Minimum ball-to-visible-home-player distance | Meters |
| `nearest_away_distance_m` | Minimum ball-to-visible-away-player distance | Meters |
| `nearest_home_speed_mps` | Reported speed of the nearest visible home player | m/s |
| `nearest_away_speed_mps` | Reported speed of the nearest visible away player | m/s |
| `distance_advantage_m` | Away nearest-player distance minus home nearest-player distance | Meters |

### Interpretation

A positive `distance_advantage_m` means the nearest observed home player is closer to the ball.

A negative value means the nearest observed away player is closer.

Zero means equal measured distance.

This feature is not a possession label. Being closest to the ball does not establish control of the ball.

Distances are computed from the available tracking observations, not inferred player identities.

### Missing data

When the ball position is unavailable:

- Nearest-player distances are `None`.
- Nearest-player speeds are `None`.
- Distance advantage is `None`.
- Visible player counts remain available.

When a team has no player with an available position, its nearest-player distance is `None`.

No missing distance is replaced with zero.

## 4. Causal Temporal Features

Temporal features are computed in chronological frame order.

The initial implementation is causal: the output for frame `t` depends only on frame `t` and preceding observations.

No future frames are used.

### Feature definitions

| Feature | Definition | Unit |
|---|---|---|
| `ball_displacement_m` | Ball distance traveled between consecutive visible-frame positions | Meters |
| `ball_speed_estimate_mps` | Consecutive-frame displacement multiplied by FPS | m/s |
| `home_mean_speed_mps` | Mean reported speed of visible home players with available speed | m/s |
| `away_mean_speed_mps` | Mean reported speed of visible away players with available speed | m/s |
| `ball_missing_streak_frames` | Number of consecutive observed frames without a detected ball | Frames |
| `distance_advantage_change_m` | Current distance advantage minus preceding-frame advantage | Meters |

### Ball motion

For consecutive frames:

```text
ball_speed_estimate_mps =
    ball_displacement_m * fps
```

The speed estimate is derived from position differences. It is not necessarily equivalent to a directly measured ball speed.

Ball motion is unavailable when:

- The current ball position is missing.
- The preceding ball position is missing.
- The sequence contains a frame gap.
- There is no preceding frame.

The pipeline does not interpolate across missing observations.

### Missing-ball streak

The missing-ball streak increases for each consecutive frame without an available ball position.

It resets to zero when the ball reappears.

A frame gap also resets the observed streak; the missingness of skipped frames is not inferred.

### Player movement limitations

Metrica tracking slots are not stable player identities.

Therefore, the initial implementation does not calculate player acceleration or velocity changes by comparing the same track-slot identifier across frames.

Team mean speeds are based on available speed observations in the current frame.

## 5. Feature Dataset Contract

The storage layer flattens geometric and temporal outputs into `FeatureRow` records.

Each record represents one frame of one match and recording source.

The logical identity is:

```text
(match_id, source, frame)
```

The initial Parquet schema includes:

- Frame identity and recording source.
- Ball visibility.
- Visible player counts by team.
- Nearest-player distances.
- Nearest-player reported speeds.
- Home-versus-away distance advantage.
- Ball displacement and derived speed.
- Team mean reported speeds.
- Missing-ball streak.
- Change in distance advantage.

Possession ground-truth labels are deliberately excluded from this feature dataset.

### Storage format

The implementation uses:

- Apache Parquet.
- Explicit PyArrow schema.
- Zstandard compression.
- Nullable numerical feature fields.

Current schema metadata:

```text
feature_schema_version = 1.0
temporal_mode = causal
```

Readers validate the expected schema, including metadata.

Schema versioning protects consumers against incompatible physical dataset formats.

It does not yet record full experiment provenance, feature configuration, or data lineage.

### Sequence constraints

A stored feature dataset currently contains one match and one recording source.

Frames must be strictly increasing.

Frame gaps are permitted, but the temporal extractor resets consecutive-frame calculations across gaps.

The current writer collects the feature sequence in memory before writing Parquet. It does not yet provide chunked or atomic dataset publication.

## 6. End-to-End Pipeline

The entry point is:

`build_feature_dataset()`

Module:

`src/football_intelligence/features/pipeline.py`

The pipeline:

1. Accepts canonical tracking frames, match metadata, and recording source.
2. Validates recording-source consistency.
3. Extracts geometric and causal temporal features.
4. Converts the outputs into feature records.
5. Writes a versioned Parquet dataset.

The implementation is intended for local or batch execution, not request-time feature computation.

The source supplied to the feature writer must match the source of the canonical tracking frames.

## 7. Integration Demonstration

Script:

`scripts/demo_features.py`

Command:

```bash
uv run python scripts/demo_features.py
```

The demonstration generates 100 synthetic tracking frames, normalizes them, extracts features, writes Parquet, and queries the output using DuckDB.

Expected deterministic results:

| Measurement | Value |
|---|---:|
| Total feature frames | 100 |
| First frame | 0 |
| Last frame | 99 |
| Ball-visible frames | 80 |
| Missing-ball frames | 20 |
| Frames with nearest-home distance | 80 |
| Frames with computed ball speed | 60 |

Generated output:

`datasets/generated/features-demo/features.parquet`

This artifact is synthetic and must remain excluded from public Git.

## 8. Automated Verification

Tests:

- `tests/test_feature_geometry.py`
- `tests/test_feature_temporal.py`
- `tests/test_feature_storage.py`
- `tests/test_feature_pipeline.py`

The tests cover:

- Coordinate conversion and physical distances.
- Nearest-player selection and home/away direction.
- Missing ball and player observations.
- Ball displacement and causal speed estimates.
- Temporal sequence ordering and source consistency.
- Missing-ball streak reset behavior.
- Parquet serialization and nullable values.
- Schema metadata and incompatible schema rejection.
- End-to-end synthetic tracking-to-Parquet transformation.
- DuckDB integration and feature coverage queries.

Commands:

```bash
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -v
uv run python scripts/demo_features.py
```

The tests use synthetic data and do not demonstrate model predictive quality.

## 9. Data Governance

All raw or restricted competition assets remain local and subject to their license restrictions.

Use:

- `datasets/raw/` for original source assets.
- `datasets/processed/` for derived analytical data.
- `datasets/generated/` for synthetic and generated demonstration artifacts.

These directories must remain excluded from public version control.

The generated feature demo contains synthetic observations.

Real competition-derived feature artifacts must not be published or uploaded to third-party services without verifying authorization.

## 10. Limitations

The initial feature engineering foundation does not yet include:

- Real-match feature extraction verification.
- Stable player-identity tracking.
- Explicit possession-control signals.
- Smart Tagging-based contextual features.
- Spatial pressure or team-shape measurements.
- Ball trajectory interpolation.
- Multi-frame rolling statistics beyond the implemented consecutive-frame comparisons.
- Offline bidirectional features.
- Atomic or partitioned feature dataset publication.
- Full experiment provenance and model-ready training splits.
- Model training, calibration, or model selection.

The current implementation also does not apply physical-pitch outlier filtering before distance calculations. Canonical tracking coordinates may contain finite values outside the normalized pitch range; future feature-quality checks should assess these observations explicitly.

## 11. Next Phase — ML Experimentation

The next stage will introduce reproducible experiment configurations, training-data preparation, model baselines and comparison workflows.

Candidate approaches include:

1. Rule-based and nearest-player baselines.
2. Logistic regression.
3. Gradient-boosted trees.
4. Temporal smoothing and sequence-aware approaches.

Additional feature families and missing-data strategies remain open for experimentation.

Controlled experiments will compare feature sets as well as model families.

The official Metrica evaluator is authoritative for competition metrics, especially `spellF1`.

The published five-minute ground truth contains only 17 possession spells and is intended primarily for integration diagnostics. It should not be used as a reliable model-selection leaderboard.

## 12. Completion Status

The geometric, temporal, storage, and end-to-end feature components have passed local verification.

Phase 2.1 should be marked complete only after:

- Technical documentation is reviewed.
- Project-status documentation is synchronized.
- Full pytest, Ruff, and mypy checks pass.
- The feature demo executes successfully.
- Changes are committed and pushed.
- GitHub Actions succeeds.

Real-data validation remains a separate dependency and is not required to claim completion of the synthetic feature-engineering foundation.
