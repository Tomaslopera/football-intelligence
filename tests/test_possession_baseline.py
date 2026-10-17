"""Deterministic possession baseline and spell extraction checks."""

import pytest

from football_intelligence.possession.baseline import ProximityBaselineConfig, predict_proximity
from football_intelligence.possession.contracts import FramePrediction, PossessionState
from football_intelligence.possession.features import ProximityFeatures
from football_intelligence.possession.spells import extract_spells


def features(home: float | None, away: float | None) -> ProximityFeatures:
    return ProximityFeatures(
        match_id="demo", frame=0, ball_available=home is not None or away is not None,
        home_observed_count=int(home is not None), away_observed_count=int(away is not None),
        home_min_distance_m=home, away_min_distance_m=away,
        proximity_margin_m=away - home if away is not None and home is not None else None,
        ball_speed_mps=None,
    )


@pytest.mark.parametrize(("home", "away", "state"), [
    (1.0, 3.0, PossessionState.HOME),
    (3.0, 1.0, PossessionState.AWAY),
    (1.0, 1.2, PossessionState.UNKNOWN),
    (None, 1.0, PossessionState.UNKNOWN),
    (4.0, 5.0, PossessionState.UNKNOWN),
])
def test_proximity_baseline(home: float | None, away: float | None, state: PossessionState) -> None:
    assert predict_proximity(features(home, away)).state == state


def test_config_validation() -> None:
    with pytest.raises(ValueError):
        ProximityBaselineConfig(max_control_distance_m=0)


def test_extract_spells_respects_unknown_and_gaps() -> None:
    sequence = [
        FramePrediction(match_id="demo", frame=i, state=state)
        for i, state in [(0, "H"), (1, "H"), (2, "X"), (3, "A"), (5, "A"), (6, "D")]
    ]
    spells = extract_spells(sequence)
    assert [(s.state, s.start_frame, s.end_frame) for s in spells] == [
        (PossessionState.HOME, 0, 2),
        (PossessionState.AWAY, 3, 4),
        (PossessionState.AWAY, 5, 6),
    ]


def test_unsorted_frames_rejected() -> None:
    sequence = [
        FramePrediction(match_id="demo", frame=2, state="H"),
        FramePrediction(match_id="demo", frame=1, state="H"),
    ]
    with pytest.raises(ValueError, match="strictly increasing"):
        extract_spells(sequence)
