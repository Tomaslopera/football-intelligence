"""Parquet storage for model-independent football features.

Feature datasets contain no possession targets. They can be reused
across different model families and experiment configurations.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import Field

from football_intelligence.features.temporal import TemporalFeatures
from football_intelligence.tracking.models import RecordingSource

FEATURE_SCHEMA_VERSION = "1.0"

FEATURE_FIELDS: list[Field] = [
    pa.field("match_id", pa.string(), nullable=False),
    pa.field("source", pa.string(), nullable=False),
    pa.field("frame", pa.int64(), nullable=False),
    pa.field("ball_visible", pa.bool_(), nullable=False),
    pa.field("home_players_visible", pa.int64(), nullable=False),
    pa.field("away_players_visible", pa.int64(), nullable=False),
    pa.field("nearest_home_distance_m", pa.float64()),
    pa.field("nearest_away_distance_m", pa.float64()),
    pa.field("nearest_home_speed_mps", pa.float64()),
    pa.field("nearest_away_speed_mps", pa.float64()),
    pa.field("distance_advantage_m", pa.float64()),
    pa.field("ball_displacement_m", pa.float64()),
    pa.field("ball_speed_estimate_mps", pa.float64()),
    pa.field("home_mean_speed_mps", pa.float64()),
    pa.field("away_mean_speed_mps", pa.float64()),
    pa.field("ball_missing_streak_frames", pa.int64(), nullable=False),
    pa.field("distance_advantage_change_m", pa.float64()),
]

FEATURE_SCHEMA = pa.schema(
    FEATURE_FIELDS,
    metadata={
        b"feature_schema_version": FEATURE_SCHEMA_VERSION.encode(),
        b"temporal_mode": b"causal",
    },
)


@dataclass(frozen=True)
class FeatureRow:
    """One model-independent feature vector at a video frame."""

    match_id: str
    source: RecordingSource
    frame: int
    ball_visible: bool
    home_players_visible: int
    away_players_visible: int
    nearest_home_distance_m: float | None
    nearest_away_distance_m: float | None
    nearest_home_speed_mps: float | None
    nearest_away_speed_mps: float | None
    distance_advantage_m: float | None
    ball_displacement_m: float | None
    ball_speed_estimate_mps: float | None
    home_mean_speed_mps: float | None
    away_mean_speed_mps: float | None
    ball_missing_streak_frames: int
    distance_advantage_change_m: float | None


def _to_feature_row(
    item: TemporalFeatures,
    source: RecordingSource,
) -> FeatureRow:
    """Flatten geometric and temporal feature values."""
    geometric = item.geometric

    return FeatureRow(
        match_id=geometric.match_id,
        source=source,
        frame=geometric.frame,
        ball_visible=geometric.ball_visible,
        home_players_visible=geometric.home_players_visible,
        away_players_visible=geometric.away_players_visible,
        nearest_home_distance_m=geometric.nearest_home_distance_m,
        nearest_away_distance_m=geometric.nearest_away_distance_m,
        nearest_home_speed_mps=geometric.nearest_home_speed_mps,
        nearest_away_speed_mps=geometric.nearest_away_speed_mps,
        distance_advantage_m=geometric.distance_advantage_m,
        ball_displacement_m=item.ball_displacement_m,
        ball_speed_estimate_mps=item.ball_speed_estimate_mps,
        home_mean_speed_mps=item.home_mean_speed_mps,
        away_mean_speed_mps=item.away_mean_speed_mps,
        ball_missing_streak_frames=item.ball_missing_streak_frames,
        distance_advantage_change_m=item.distance_advantage_change_m,
    )


def _validate_rows(rows: list[FeatureRow]) -> None:
    """Enforce one match, source, and increasing frame sequence."""
    if not rows:
        raise ValueError("Feature dataset cannot be empty")

    first = rows[0]
    previous_frame = -1

    for row in rows:
        if row.match_id != first.match_id:
            raise ValueError("Feature dataset contains multiple matches")

        if row.source != first.source:
            raise ValueError("Feature dataset contains multiple recording sources")

        if row.frame <= previous_frame:
            raise ValueError("Feature frames must be strictly increasing")

        previous_frame = row.frame


def write_feature_parquet(
    features: Iterable[TemporalFeatures],
    source: RecordingSource,
    path: Path,
) -> Path:
    """Write validated temporal features to versioned Parquet.

    The caller supplies the recording source associated with the
    feature sequence. Use the source from the canonical input frames.
    """
    rows = [_to_feature_row(feature, source) for feature in features]

    _validate_rows(rows)

    # Convert enums to their stable string representation.
    records = [
        {
            **row.__dict__,
            "source": row.source.value,
        }
        for row in rows
    ]

    table = pa.Table.from_pylist(
        records,
        schema=FEATURE_SCHEMA,
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pq.write_table(
        table,
        path,
        compression="zstd",
    )

    return path


def read_feature_parquet(path: Path) -> list[FeatureRow]:
    """Read a feature dataset with strict schema-version validation."""
    table = pq.read_table(path)

    if not table.schema.equals(
        FEATURE_SCHEMA,
        check_metadata=True,
    ):
        raise ValueError("Unsupported or incompatible feature schema")

    rows = [
        FeatureRow(
            **{
                **record,
                "source": RecordingSource(record["source"]),
            }
        )
        for record in table.to_pylist()
    ]

    _validate_rows(rows)

    return rows
