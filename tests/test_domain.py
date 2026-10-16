import pytest
from pydantic import ValidationError

from football_intelligence.domain import (
    PossessionPrediction,
    PossessionState,
)


def test_valid_possession_prediction():
    prediction = PossessionPrediction(
        frame=11185,
        label=PossessionState.AWAY,
        model_version="baseline-v0",
        confidence=0.91,
    )

    assert prediction.label == PossessionState.AWAY
    assert prediction.frame == 11185


def test_negative_frame_is_rejected():
    with pytest.raises(ValidationError):
        PossessionPrediction(
            frame=-1,
            label=PossessionState.HOME,
            model_version="baseline-v0",
        )


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValidationError):
        PossessionPrediction(
            frame=100,
            label=PossessionState.HOME,
            model_version="baseline-v0",
            confidence=1.5,
        )
