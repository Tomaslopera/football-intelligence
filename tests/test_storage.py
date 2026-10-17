import pytest

from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
)
from football_intelligence.tracking.models import (
    RecordingSource,
    TeamSide,
    TrackingFrame,
)
from football_intelligence.tracking.storage import (
    read_tracking_parquet,
    write_tracking_parquet,
)
from football_intelligence.tracking.synthetic import (
    generate_tracking_table,
)


@pytest.fixture
def sample_frames():
    table = generate_tracking_table(n_frames=10)

    return list(
        iter_tracking_frames(
            table,
            match_id="SYNTHETIC-001",
            source=RecordingSource.SYNTHETIC,
            slot_teams={
                1: TeamSide.HOME,
                2: TeamSide.AWAY,
            },
        )
    )


def test_parquet_round_trip(sample_frames, tmp_path):
    write_tracking_parquet(sample_frames, tmp_path)

    restored = read_tracking_parquet(tmp_path)

    assert restored == sample_frames


def test_parquet_files_created(sample_frames, tmp_path):
    frames_path, players_path = write_tracking_parquet(sample_frames, tmp_path)

    assert frames_path.exists()
    assert players_path.exists()


def test_missing_ball_survives_storage(sample_frames, tmp_path):
    write_tracking_parquet(sample_frames, tmp_path)

    restored = read_tracking_parquet(tmp_path)

    assert restored[0].ball.position is None
    assert restored[1].ball.position is not None


def test_empty_tracking_dataset(tmp_path):
    write_tracking_parquet([], tmp_path)

    assert read_tracking_parquet(tmp_path) == []


def test_duplicate_frame_rejected(tmp_path):
    frame = TrackingFrame(
        match_id="TEST",
        source=RecordingSource.SYNTHETIC,
        frame=0,
    )

    with pytest.raises(ValueError, match="Duplicate"):
        write_tracking_parquet(
            [frame, frame],
            tmp_path,
        )
