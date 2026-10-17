"""Tests for causal motion and temporal football features."""

import pytest

from football_intelligence.features.temporal import (
    extract_temporal_features,
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


def make_frame(
    frame: int,
    ball_x: float | None,
    *,
    source: RecordingSource = RecordingSource.SYNTHETIC,
    players: list[PlayerObservation] | None = None,
) -> TrackingFrame:
    position = PitchPosition(x=ball_x, y=0.5) if ball_x is not None else None

    return TrackingFrame(
        match_id="synthetic-match",
        source=source,
        frame=frame,
        ball=BallObservation(position=position),
        players=players or [],
    )


def player(
    slot: int,
    team: TeamSide,
    speed: float | None,
    *,
    visible: bool = True,
) -> PlayerObservation:
    return PlayerObservation(
        track_slot=slot,
        team=team,
        position=(PitchPosition(x=0.5, y=0.5) if visible else None),
        speed_mps=speed,
    )


def test_empty_input(metadata: MatchMetadata) -> None:
    assert list(extract_temporal_features([], metadata)) == []


def test_first_frame_has_no_motion_estimate(
    metadata: MatchMetadata,
) -> None:
    results = list(
        extract_temporal_features(
            [make_frame(0, 0.5)],
            metadata,
        )
    )

    assert results[0].ball_displacement_m is None
    assert results[0].ball_speed_estimate_mps is None
    assert results[0].ball_missing_streak_frames == 0


def test_ball_displacement_and_speed(
    metadata: MatchMetadata,
) -> None:
    results = list(
        extract_temporal_features(
            [
                make_frame(0, 0.50),
                make_frame(1, 0.51),
            ],
            metadata,
        )
    )

    assert results[1].ball_displacement_m == pytest.approx(1.0)
    assert results[1].ball_speed_estimate_mps == pytest.approx(25.0)


def test_missing_ball_streak(
    metadata: MatchMetadata,
) -> None:
    frames = [
        make_frame(0, 0.5),
        make_frame(1, None),
        make_frame(2, None),
        make_frame(3, 0.6),
    ]

    results = list(extract_temporal_features(frames, metadata))

    assert [result.ball_missing_streak_frames for result in results] == [0, 1, 2, 0]

    assert results[3].ball_speed_estimate_mps is None


def test_frame_gap_resets_motion(
    metadata: MatchMetadata,
) -> None:
    results = list(
        extract_temporal_features(
            [
                make_frame(0, 0.5),
                make_frame(5, 0.7),
            ],
            metadata,
        )
    )

    assert results[1].ball_displacement_m is None
    assert results[1].ball_speed_estimate_mps is None


def test_frame_gap_resets_missing_streak(
    metadata: MatchMetadata,
) -> None:
    frames = [
        make_frame(0, None),
        make_frame(1, None),
        make_frame(5, None),
    ]

    results = list(extract_temporal_features(frames, metadata))

    assert [value.ball_missing_streak_frames for value in results] == [1, 2, 1]


def test_mean_player_speeds(
    metadata: MatchMetadata,
) -> None:
    frame = make_frame(
        0,
        0.5,
        players=[
            player(1, TeamSide.HOME, 2.0),
            player(2, TeamSide.HOME, 4.0),
            player(3, TeamSide.HOME, 9.0, visible=False),
            player(4, TeamSide.AWAY, 3.0),
            player(5, TeamSide.AWAY, None),
        ],
    )

    result = next(extract_temporal_features([frame], metadata))

    assert result.home_mean_speed_mps == pytest.approx(3.0)
    assert result.away_mean_speed_mps == pytest.approx(3.0)


def test_no_known_player_speeds(
    metadata: MatchMetadata,
) -> None:
    result = next(
        extract_temporal_features(
            [
                make_frame(
                    0,
                    None,
                    players=[
                        player(1, TeamSide.HOME, None),
                    ],
                )
            ],
            metadata,
        )
    )

    assert result.home_mean_speed_mps is None
    assert result.away_mean_speed_mps is None


def test_distance_advantage_change(
    metadata: MatchMetadata,
) -> None:
    players = [
        PlayerObservation(
            track_slot=1,
            team=TeamSide.HOME,
            position=PitchPosition(x=0.4, y=0.5),
        ),
        PlayerObservation(
            track_slot=2,
            team=TeamSide.AWAY,
            position=PitchPosition(x=0.7, y=0.5),
        ),
    ]

    results = list(
        extract_temporal_features(
            [
                make_frame(0, 0.5, players=players),
                make_frame(1, 0.6, players=players),
            ],
            metadata,
        )
    )

    assert results[1].distance_advantage_change_m == pytest.approx(-20.0)


def test_rejects_out_of_order_frames(
    metadata: MatchMetadata,
) -> None:
    frames = [
        make_frame(3, 0.5),
        make_frame(2, 0.6),
    ]

    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        list(extract_temporal_features(frames, metadata))


def test_rejects_mixed_recording_sources(
    metadata: MatchMetadata,
) -> None:
    frames = [
        make_frame(0, 0.5),
        make_frame(
            1,
            0.6,
            source=RecordingSource.BROADCAST,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="one recording source",
    ):
        list(extract_temporal_features(frames, metadata))


def test_generator_input(
    metadata: MatchMetadata,
) -> None:
    frames = (make_frame(index, 0.5) for index in range(5))

    results = list(extract_temporal_features(frames, metadata))

    assert len(results) == 5
    assert results[-1].geometric.frame == 4
