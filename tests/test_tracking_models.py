import pytest
from pydantic import ValidationError

from football_intelligence.tracking.models import (
    BallObservation,
    MatchMetadata,
    PitchPosition,
    PlayerObservation,
    RecordingSource,
    TeamSide,
    TrackingFrame,
)


@pytest.fixture
def match_metadata():
    return MatchMetadata(
        match_id="BAR-ATH",
        home_team="Barcelona",
        away_team="Athletic Club",
        fps=25,
        total_frames=199_319,
        pitch_length_m=105.3,
        pitch_width_m=68.0,
    )


def test_match_metadata(match_metadata):
    assert match_metadata.fps == 25
    assert match_metadata.total_frames == 199_319


def test_valid_tracking_frame():
    frame = TrackingFrame(
        match_id="BAR-ATH",
        source=RecordingSource.TACTICAL,
        frame=11185,
        players=[
            PlayerObservation(
                track_slot=1,
                team=TeamSide.HOME,
                position=PitchPosition(x=0.4, y=0.6),
                speed_mps=3.2,
            ),
            PlayerObservation(
                track_slot=2,
                team=TeamSide.AWAY,
                position=PitchPosition(x=0.6, y=0.4),
            ),
        ],
        ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
    )

    assert frame.ball_visible
    assert frame.tracked_player_count == 2
    assert frame.timestamp_seconds(25) == 447.4


def test_missing_ball_is_allowed():
    frame = TrackingFrame(
        match_id="BAR-ATH",
        source=RecordingSource.TACTICAL,
        frame=100,
    )

    assert frame.ball_visible is False
    assert frame.tracked_player_count == 0


def test_missing_player_position_is_allowed():
    player = PlayerObservation(
        track_slot=3,
        team=TeamSide.HOME,
        position=None,
    )

    assert player.position is None


def test_duplicate_track_slots_are_rejected():
    with pytest.raises(ValidationError):
        TrackingFrame(
            match_id="BAR-ATH",
            source=RecordingSource.TACTICAL,
            frame=100,
            players=[
                PlayerObservation(
                    track_slot=1,
                    team=TeamSide.HOME,
                ),
                PlayerObservation(
                    track_slot=1,
                    team=TeamSide.AWAY,
                ),
            ],
        )


def test_negative_speed_is_rejected():
    with pytest.raises(ValidationError):
        PlayerObservation(
            track_slot=1,
            team=TeamSide.HOME,
            speed_mps=-2.0,
        )


def test_non_finite_position_is_rejected():
    with pytest.raises(ValidationError):
        PitchPosition(x=float("nan"), y=0.5)


def test_outside_pitch_position_is_preserved():
    position = PitchPosition(x=1.02, y=0.5)

    assert position.x == 1.02
