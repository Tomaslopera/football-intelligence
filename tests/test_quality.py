from football_intelligence.tracking.models import (
    BallObservation,
    PitchPosition,
    PlayerObservation,
    RecordingSource,
    TeamSide,
    TrackingFrame,
)
from football_intelligence.tracking.quality import (
    QualityConfig,
    analyze_tracking_quality,
)
from football_intelligence.tracking.storage import (
    write_tracking_parquet,
)


def test_quality_detects_missing_frames_and_positions(tmp_path):
    frames = [
        TrackingFrame(
            match_id="TEST",
            source=RecordingSource.SYNTHETIC,
            frame=0,
            ball=BallObservation(position=None),
            players=[
                PlayerObservation(
                    track_slot=1,
                    team=TeamSide.HOME,
                    position=PitchPosition(x=0.4, y=0.5),
                    speed_mps=2.0,
                )
            ],
        ),
        TrackingFrame(
            match_id="TEST",
            source=RecordingSource.SYNTHETIC,
            frame=3,
            ball=BallObservation(position=PitchPosition(x=1.2, y=0.5)),
            players=[
                PlayerObservation(
                    track_slot=1,
                    team=TeamSide.HOME,
                    position=None,
                ),
                PlayerObservation(
                    track_slot=2,
                    team=TeamSide.AWAY,
                    position=PitchPosition(x=-0.2, y=0.5),
                    speed_mps=20.0,
                ),
            ],
        ),
    ]

    write_tracking_parquet(frames, tmp_path)

    report = analyze_tracking_quality(tmp_path)

    assert report.total_frames == 2
    assert report.missing_ball_frames == 1
    assert report.ball_coverage_pct == 50.0
    assert report.frame_gaps == 1
    assert report.missing_frame_ids == 2
    assert report.ball_out_of_bounds == 1
    assert report.players_out_of_bounds == 1
    assert report.suspicious_player_speeds == 1
    assert report.missing_player_positions == 1
    assert report.tracked_player_observations == 2


def test_empty_dataset_quality(tmp_path):
    write_tracking_parquet([], tmp_path)

    report = analyze_tracking_quality(tmp_path)

    assert report.total_frames == 0
    assert report.ball_coverage_pct == 0.0
    assert report.frame_gaps == 0


def test_invalid_quality_config_rejected(tmp_path):
    import pytest

    write_tracking_parquet([], tmp_path)

    with pytest.raises(ValueError, match="boundaries"):
        analyze_tracking_quality(
            tmp_path,
            QualityConfig(
                coordinate_min=1.0,
                coordinate_max=0.0,
            ),
        )


def test_clean_dataset_has_no_structural_anomalies(tmp_path):
    frames = [
        TrackingFrame(
            match_id="CLEAN",
            source=RecordingSource.SYNTHETIC,
            frame=number,
            ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
        )
        for number in range(5)
    ]

    write_tracking_parquet(frames, tmp_path)

    report = analyze_tracking_quality(tmp_path)

    assert report.total_frames == 5
    assert report.ball_coverage_pct == 100.0
    assert report.missing_frame_ids == 0
    assert report.duplicate_frames == 0
    assert report.ball_out_of_bounds == 0
