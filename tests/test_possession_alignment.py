"""Synthetic tests for possession prediction alignment."""

import pytest
from pydantic import ValidationError

from football_intelligence.domain import (
    PossessionPrediction,
    PossessionState,
)
from football_intelligence.possession.alignment import (
    PredictionContext,
    validate_prediction_sequence,
)
from football_intelligence.tracking.models import (
    MatchMetadata,
    RecordingSource,
)


@pytest.fixture
def context() -> PredictionContext:
    return PredictionContext(
        match=MatchMetadata(
            match_id="synthetic-match",
            home_team="Home",
            away_team="Away",
            fps=25.0,
            total_frames=100,
            pitch_length_m=105.0,
            pitch_width_m=68.0,
        ),
        source=RecordingSource.SYNTHETIC,
        model_version="baseline-v1",
    )


def prediction(
    frame: int,
    *,
    label: PossessionState = PossessionState.HOME,
    version: str = "baseline-v1",
) -> PossessionPrediction:
    return PossessionPrediction(
        frame=frame,
        label=label,
        model_version=version,
    )


def test_valid_prediction_sequence(
    context: PredictionContext,
) -> None:
    predictions = [
        prediction(0, label=PossessionState.HOME),
        prediction(1, label=PossessionState.AWAY),
        prediction(2, label=PossessionState.DEAD_BALL),
        prediction(3, label=PossessionState.UNKNOWN),
    ]

    validated = list(
        validate_prediction_sequence(
            predictions,
            context,
            require_contiguous=True,
        )
    )

    assert validated == predictions
    assert [item.label.value for item in validated] == ["H", "A", "D", "X"]


def test_last_valid_frame(
    context: PredictionContext,
) -> None:
    validated = list(
        validate_prediction_sequence(
            [prediction(99)],
            context,
        )
    )

    assert validated[0].frame == 99


def test_frame_outside_match(
    context: PredictionContext,
) -> None:
    with pytest.raises(ValueError, match="frame bounds"):
        list(
            validate_prediction_sequence(
                [prediction(100)],
                context,
            )
        )


def test_model_version_mismatch(
    context: PredictionContext,
) -> None:
    with pytest.raises(ValueError, match="version mismatch"):
        list(
            validate_prediction_sequence(
                [prediction(10, version="other-model")],
                context,
            )
        )


def test_duplicate_frames_rejected(
    context: PredictionContext,
) -> None:
    predictions = [prediction(10), prediction(10)]

    with pytest.raises(ValueError, match="strictly increasing"):
        list(validate_prediction_sequence(predictions, context))


def test_out_of_order_frames_rejected(
    context: PredictionContext,
) -> None:
    predictions = [prediction(20), prediction(19)]

    with pytest.raises(ValueError, match="strictly increasing"):
        list(validate_prediction_sequence(predictions, context))


def test_gaps_allowed_for_partial_predictions(
    context: PredictionContext,
) -> None:
    predictions = [prediction(10), prediction(15)]

    validated = list(validate_prediction_sequence(predictions, context))

    assert len(validated) == 2


def test_gaps_rejected_when_contiguous_required(
    context: PredictionContext,
) -> None:
    predictions = [prediction(10), prediction(15)]

    with pytest.raises(ValueError, match="frame gap"):
        list(
            validate_prediction_sequence(
                predictions,
                context,
                require_contiguous=True,
            )
        )


def test_empty_sequence_is_valid(
    context: PredictionContext,
) -> None:
    assert list(validate_prediction_sequence([], context)) == []


def test_invalid_context_model_version(
    context: PredictionContext,
) -> None:
    with pytest.raises(ValidationError):
        PredictionContext(
            match=context.match,
            source=RecordingSource.SYNTHETIC,
            model_version="",
        )


def test_generator_input(
    context: PredictionContext,
) -> None:
    predictions = (prediction(index) for index in range(20, 25))

    validated = list(
        validate_prediction_sequence(
            predictions,
            context,
            require_contiguous=True,
        )
    )

    assert [item.frame for item in validated] == [20, 21, 22, 23, 24]


def test_context_preserves_tracking_identity(
    context: PredictionContext,
) -> None:
    assert context.match.match_id == "synthetic-match"
    assert context.source == RecordingSource.SYNTHETIC
    assert context.match.fps == 25.0
