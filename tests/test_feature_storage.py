"""Tests for versioned football feature Parquet storage."""

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from football_intelligence.features.geometry import GeometricFeatures
from football_intelligence.features.storage import (
    FEATURE_SCHEMA_VERSION,
    read_feature_parquet,
    write_feature_parquet,
)
from football_intelligence.features.temporal import TemporalFeatures
from football_intelligence.tracking.models import RecordingSource


def make_feature(
    frame: int,
    *,
    match_id: str = "synthetic-match",
    ball_visible: bool = True,
) -> TemporalFeatures:
    geometric = GeometricFeatures(
        match_id=match_id,
        frame=frame,
        ball_visible=ball_visible,
        home_players_visible=1,
        away_players_visible=1,
        nearest_home_distance_m=1.0 if ball_visible else None,
        nearest_away_distance_m=3.0 if ball_visible else None,
        nearest_home_speed_mps=2.0,
        nearest_away_speed_mps=3.0,
        distance_advantage_m=2.0 if ball_visible else None,
    )

    return TemporalFeatures(
        geometric=geometric,
        ball_displacement_m=0.5 if ball_visible else None,
        ball_speed_estimate_mps=12.5 if ball_visible else None,
        home_mean_speed_mps=2.0,
        away_mean_speed_mps=3.0,
        ball_missing_streak_frames=0 if ball_visible else 1,
        distance_advantage_change_m=0.1 if ball_visible else None,
    )


def test_feature_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "features.parquet"

    write_feature_parquet(
        [make_feature(0), make_feature(1)],
        RecordingSource.SYNTHETIC,
        path,
    )

    rows = read_feature_parquet(path)

    assert len(rows) == 2
    assert rows[0].frame == 0
    assert rows[0].match_id == "synthetic-match"
    assert rows[0].source == RecordingSource.SYNTHETIC
    assert rows[0].nearest_home_distance_m == 1.0
    assert rows[0].distance_advantage_m == 2.0
    assert rows[1].ball_speed_estimate_mps == 12.5


def test_missing_values_survive_round_trip(
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    write_feature_parquet(
        [make_feature(0, ball_visible=False)],
        RecordingSource.SYNTHETIC,
        path,
    )

    row = read_feature_parquet(path)[0]

    assert not row.ball_visible
    assert row.nearest_home_distance_m is None
    assert row.ball_displacement_m is None
    assert row.ball_speed_estimate_mps is None
    assert row.ball_missing_streak_frames == 1


def test_versioned_schema_metadata(
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    write_feature_parquet(
        [make_feature(0)],
        RecordingSource.SYNTHETIC,
        path,
    )

    metadata = pq.read_schema(path).metadata

    assert metadata is not None
    assert metadata[b"feature_schema_version"] == (FEATURE_SCHEMA_VERSION.encode())
    assert metadata[b"temporal_mode"] == b"causal"


def test_generator_input(tmp_path: Path) -> None:
    path = tmp_path / "features.parquet"

    features = (make_feature(index) for index in range(3))

    write_feature_parquet(
        features,
        RecordingSource.SYNTHETIC,
        path,
    )

    assert [row.frame for row in read_feature_parquet(path)] == [
        0,
        1,
        2,
    ]


def test_gaps_are_allowed(tmp_path: Path) -> None:
    path = tmp_path / "features.parquet"

    write_feature_parquet(
        [make_feature(0), make_feature(5)],
        RecordingSource.SYNTHETIC,
        path,
    )

    assert [row.frame for row in read_feature_parquet(path)] == [
        0,
        5,
    ]


def test_duplicate_frames_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        write_feature_parquet(
            [make_feature(1), make_feature(1)],
            RecordingSource.SYNTHETIC,
            tmp_path / "features.parquet",
        )


def test_out_of_order_frames_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        write_feature_parquet(
            [make_feature(3), make_feature(2)],
            RecordingSource.SYNTHETIC,
            tmp_path / "features.parquet",
        )


def test_mixed_matches_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="multiple matches"):
        write_feature_parquet(
            [
                make_feature(0),
                make_feature(1, match_id="other-match"),
            ],
            RecordingSource.SYNTHETIC,
            tmp_path / "features.parquet",
        )


def test_empty_dataset_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        write_feature_parquet(
            [],
            RecordingSource.SYNTHETIC,
            tmp_path / "features.parquet",
        )


def test_wrong_schema_version_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    write_feature_parquet(
        [make_feature(0)],
        RecordingSource.SYNTHETIC,
        path,
    )

    table = pq.read_table(path)
    changed = table.replace_schema_metadata(
        {
            b"feature_schema_version": b"999.0",
            b"temporal_mode": b"causal",
        }
    )

    pq.write_table(changed, path)

    with pytest.raises(ValueError, match="feature schema"):
        read_feature_parquet(path)


def test_rejects_corrupted_frame_order(
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    write_feature_parquet(
        [make_feature(0), make_feature(1)],
        RecordingSource.SYNTHETIC,
        path,
    )

    table = pq.read_table(path)
    reversed_table = table.take([1, 0])
    pq.write_table(reversed_table, path)

    with pytest.raises(ValueError, match="strictly increasing"):
        read_feature_parquet(path)
