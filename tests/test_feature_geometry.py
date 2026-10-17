"""Tests for frame-level geometric possession features."""

import pytest

from football_intelligence.features.geometry import (
    extract_geometric_features,
    pitch_distance_m,
)
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
def metadata() -> MatchMetadata:
    return MatchMetadata(
        match_id="synthetic-match",
        home_team="Home",
        away_team="Away",
        fps=25.0,
        total_frames=100,
        pitch_length_m=100.0,
        pitch_width_m=60.0,
    )


def make_player(
    slot: int,
    team: TeamSide,
    x: float,
    y: float,
    speed: float | None = None,
) -> PlayerObservation:
    return PlayerObservation(
        track_slot=slot,
        team=team,
        position=PitchPosition(x=x, y=y),
        speed_mps=speed,
    )


def test_pitch_distance_in_metres(
    metadata: MatchMetadata,
) -> None:
    distance = pitch_distance_m(
        PitchPosition(x=0.0, y=0.0),
        PitchPosition(x=0.03, y=0.04),
        metadata,
    )

    assert distance == pytest.approx((3.0**2 + 2.4**2) ** 0.5)


def test_home_player_closer(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="synthetic-match",
        source=RecordingSource.SYNTHETIC,
        frame=0,
        ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
        players=[
            make_player(1, TeamSide.HOME, 0.51, 0.5, 3.0),
            make_player(2, TeamSide.AWAY, 0.6, 0.5, 2.0),
        ],
    )

    features = extract_geometric_features(frame, metadata)

    assert features.ball_visible
    assert features.nearest_home_distance_m == pytest.approx(1.0)
    assert features.nearest_away_distance_m == pytest.approx(10.0)
    assert features.distance_advantage_m == pytest.approx(9.0)
    assert features.nearest_home_speed_mps == 3.0
    assert features.nearest_away_speed_mps == 2.0


def test_away_player_closer(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="synthetic-match",
        source=RecordingSource.SYNTHETIC,
        frame=1,
        ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
        players=[
            make_player(1, TeamSide.HOME, 0.7, 0.5),
            make_player(2, TeamSide.AWAY, 0.51, 0.5),
        ],
    )

    features = extract_geometric_features(frame, metadata)

    assert features.distance_advantage_m == pytest.approx(-19.0)


def test_nearest_of_multiple_players(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="synthetic-match",
        source=RecordingSource.SYNTHETIC,
        frame=2,
        ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
        players=[
            make_player(1, TeamSide.HOME, 0.8, 0.5, 5.0),
            make_player(2, TeamSide.HOME, 0.52, 0.5, 1.5),
            make_player(3, TeamSide.AWAY, 0.6, 0.5, 2.0),
        ],
    )

    features = extract_geometric_features(frame, metadata)

    assert features.home_players_visible == 2
    assert features.away_players_visible == 1
    assert features.nearest_home_distance_m == pytest.approx(2.0)
    assert features.nearest_home_speed_mps == 1.5


def test_missing_ball_produces_missing_distances(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="synthetic-match",
        source=RecordingSource.SYNTHETIC,
        frame=3,
        players=[
            make_player(1, TeamSide.HOME, 0.3, 0.4),
        ],
    )

    features = extract_geometric_features(frame, metadata)

    assert not features.ball_visible
    assert features.home_players_visible == 1
    assert features.nearest_home_distance_m is None
    assert features.nearest_away_distance_m is None
    assert features.distance_advantage_m is None


def test_missing_team_does_not_invent_distance(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="synthetic-match",
        source=RecordingSource.SYNTHETIC,
        frame=4,
        ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
        players=[
            make_player(1, TeamSide.HOME, 0.51, 0.5),
        ],
    )

    features = extract_geometric_features(frame, metadata)

    assert features.nearest_home_distance_m == pytest.approx(1.0)
    assert features.nearest_away_distance_m is None
    assert features.distance_advantage_m is None


def test_match_mismatch_rejected(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="another-match",
        source=RecordingSource.SYNTHETIC,
        frame=0,
    )

    with pytest.raises(ValueError, match="do not match"):
        extract_geometric_features(frame, metadata)


def test_frame_outside_match_rejected(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="synthetic-match",
        source=RecordingSource.SYNTHETIC,
        frame=100,
    )

    with pytest.raises(ValueError, match="frame bounds"):
        extract_geometric_features(frame, metadata)


def test_player_with_missing_position_excluded(
    metadata: MatchMetadata,
) -> None:
    frame = TrackingFrame(
        match_id="synthetic-match",
        source=RecordingSource.SYNTHETIC,
        frame=5,
        ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
        players=[
            PlayerObservation(
                track_slot=1,
                team=TeamSide.HOME,
                position=None,
            ),
            make_player(2, TeamSide.AWAY, 0.6, 0.5),
        ],
    )

    features = extract_geometric_features(frame, metadata)

    assert features.home_players_visible == 0
    assert features.away_players_visible == 1
    assert features.nearest_home_distance_m is None
