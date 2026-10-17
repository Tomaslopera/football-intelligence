"""Phase 2 synthetic contract and proximity tests."""

import pytest
from pydantic import ValidationError

from football_intelligence.possession.contracts import (
    FramePrediction,
    PossessionSpell,
    PossessionState,
)
from football_intelligence.possession.features import extract_proximity_features
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
        match_id="synthetic-demo",
        home_team="Home",
        away_team="Away",
        fps=25,
        total_frames=100,
        pitch_length_m=100,
        pitch_width_m=60,
    )


def test_competition_states_are_exact() -> None:
    assert {s.value for s in PossessionState} == {"H", "A", "D", "X"}
    assert FramePrediction(match_id="demo", frame=0, state="X").state == PossessionState.UNKNOWN
    with pytest.raises(ValidationError):
        FramePrediction(match_id="demo", frame=0, state="N")


def test_possession_spells_are_half_open_and_team_only() -> None:
    spell = PossessionSpell(match_id="demo", state=PossessionState.HOME, start_frame=4, end_frame=9)
    assert spell.duration_frames == 5
    with pytest.raises(ValidationError):
        PossessionSpell(match_id="demo", state=PossessionState.DEAD, start_frame=4, end_frame=9)
    with pytest.raises(ValidationError):
        PossessionSpell(match_id="demo", state=PossessionState.AWAY, start_frame=9, end_frame=9)


def test_proximity_uses_pitch_dimensions(metadata: MatchMetadata) -> None:
    frame = TrackingFrame(
        match_id="synthetic-demo",
        source=RecordingSource.SYNTHETIC,
        frame=0,
        players=[
            PlayerObservation(track_slot=1, team=TeamSide.HOME, position=PitchPosition(x=0.51, y=0.5)),
            PlayerObservation(track_slot=2, team=TeamSide.AWAY, position=PitchPosition(x=0.5, y=0.55)),
        ],
        ball=BallObservation(position=PitchPosition(x=0.5, y=0.5)),
    )
    f = extract_proximity_features(frame, metadata)
    assert f.home_min_distance_m == pytest.approx(1.0)
    assert f.away_min_distance_m == pytest.approx(3.0)
    assert f.proximity_margin_m == pytest.approx(2.0)
    assert (f.home_observed_count, f.away_observed_count) == (1, 1)


def test_missing_ball_preserves_missing_distances(metadata: MatchMetadata) -> None:
    frame = TrackingFrame(match_id="synthetic-demo", source=RecordingSource.SYNTHETIC, frame=1)
    f = extract_proximity_features(frame, metadata)
    assert not f.ball_available
    assert f.home_min_distance_m is None
    assert f.away_min_distance_m is None
    assert f.proximity_margin_m is None


def test_mismatched_match_is_rejected(metadata: MatchMetadata) -> None:
    frame = TrackingFrame(match_id="wrong", source=RecordingSource.SYNTHETIC, frame=0)
    with pytest.raises(ValueError, match="match_id"):
        extract_proximity_features(frame, metadata)
