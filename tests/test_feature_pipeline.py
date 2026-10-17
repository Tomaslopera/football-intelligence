"""End-to-end tests for tracking-to-feature Parquet processing."""

from pathlib import Path

import duckdb
import pytest

from football_intelligence.features.pipeline import (
    build_feature_dataset,
)
from football_intelligence.features.storage import (
    read_feature_parquet,
)
from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
)
from football_intelligence.tracking.models import (
    MatchMetadata,
    RecordingSource,
    TeamSide,
)
from football_intelligence.tracking.synthetic import (
    generate_tracking_table,
)


@pytest.fixture
def metadata() -> MatchMetadata:
    return MatchMetadata(
        match_id="TEST-FEATURES",
        home_team="Home",
        away_team="Away",
        fps=25.0,
        total_frames=20,
        pitch_length_m=105.0,
        pitch_width_m=68.0,
    )


def build_test_frames(
    metadata: MatchMetadata,
):
    table = generate_tracking_table(
        n_frames=20,
        missing_ball_every=5,
    )

    return iter_tracking_frames(
        table,
        match_id=metadata.match_id,
        source=RecordingSource.SYNTHETIC,
        slot_teams={
            1: TeamSide.HOME,
            2: TeamSide.AWAY,
        },
    )


def test_complete_feature_pipeline(
    metadata: MatchMetadata,
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    result = build_feature_dataset(
        build_test_frames(metadata),
        metadata,
        RecordingSource.SYNTHETIC,
        path,
    )

    assert result == path
    assert path.is_file()

    rows = read_feature_parquet(path)

    assert len(rows) == 20
    assert [row.frame for row in rows] == list(range(20))
    assert all(row.match_id == metadata.match_id for row in rows)
    assert all(row.source == RecordingSource.SYNTHETIC for row in rows)


def test_missing_ball_features_are_preserved(
    metadata: MatchMetadata,
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    build_feature_dataset(
        build_test_frames(metadata),
        metadata,
        RecordingSource.SYNTHETIC,
        path,
    )

    rows = read_feature_parquet(path)

    assert not rows[0].ball_visible
    assert rows[0].nearest_home_distance_m is None
    assert rows[0].ball_missing_streak_frames == 1

    assert rows[1].ball_visible
    assert rows[1].ball_missing_streak_frames == 0
    assert rows[1].ball_speed_estimate_mps is None

    assert rows[2].ball_speed_estimate_mps is not None


def test_duckdb_feature_summary(
    metadata: MatchMetadata,
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    build_feature_dataset(
        build_test_frames(metadata),
        metadata,
        RecordingSource.SYNTHETIC,
        path,
    )

    with duckdb.connect(":memory:") as connection:
        result = connection.execute(
            """
            SELECT
                COUNT(*),
                COUNT_IF(ball_visible),
                COUNT_IF(NOT ball_visible),
                COUNT(ball_speed_estimate_mps)
            FROM read_parquet(?)
            """,
            [str(path)],
        ).fetchone()

    assert result == (20, 16, 4, 12)


def test_source_mismatch_rejected(
    metadata: MatchMetadata,
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    with pytest.raises(
        ValueError,
        match="source does not match",
    ):
        build_feature_dataset(
            build_test_frames(metadata),
            metadata,
            RecordingSource.BROADCAST,
            path,
        )

    assert not path.exists()


def test_match_mismatch_rejected(
    metadata: MatchMetadata,
    tmp_path: Path,
) -> None:
    path = tmp_path / "features.parquet"

    wrong_metadata = metadata.model_copy(update={"match_id": "WRONG-MATCH"})

    with pytest.raises(ValueError, match="do not match"):
        build_feature_dataset(
            build_test_frames(metadata),
            wrong_metadata,
            RecordingSource.SYNTHETIC,
            path,
        )

    assert not path.exists()


def test_output_uses_versioned_feature_schema(
    metadata: MatchMetadata,
    tmp_path: Path,
) -> None:
    import pyarrow.parquet as pq

    path = tmp_path / "features.parquet"

    build_feature_dataset(
        build_test_frames(metadata),
        metadata,
        RecordingSource.SYNTHETIC,
        path,
    )

    schema_metadata = pq.read_schema(path).metadata

    assert schema_metadata is not None
    assert schema_metadata[b"feature_schema_version"] == b"1.0"
    assert schema_metadata[b"temporal_mode"] == b"causal"
