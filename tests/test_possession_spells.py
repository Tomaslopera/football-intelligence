"""Tests for contiguous possession-state extraction."""

import pytest

from football_intelligence.domain import (
    PossessionPrediction,
    PossessionState,
)
from football_intelligence.possession.spells import (
    PossessionSegment,
    extract_possession_segments,
)


def prediction(
    frame: int,
    label: PossessionState,
    model_version: str = "test-v1",
) -> PossessionPrediction:
    return PossessionPrediction(
        frame=frame,
        label=label,
        model_version=model_version,
    )


def test_empty_predictions() -> None:
    assert extract_possession_segments([]) == []


def test_continuous_home_possession() -> None:
    predictions = [prediction(frame, PossessionState.HOME) for frame in range(5)]

    segments = extract_possession_segments(predictions)

    assert segments == [
        PossessionSegment(
            start_frame=0,
            end_frame=5,
            label=PossessionState.HOME,
        )
    ]

    assert segments[0].duration_frames == 5
    assert segments[0].duration_seconds(25.0) == 0.2


def test_label_changes_create_segments() -> None:
    predictions = [
        prediction(0, PossessionState.HOME),
        prediction(1, PossessionState.HOME),
        prediction(2, PossessionState.AWAY),
        prediction(3, PossessionState.DEAD_BALL),
        prediction(4, PossessionState.UNKNOWN),
    ]

    segments = extract_possession_segments(predictions)

    assert [segment.label for segment in segments] == [
        PossessionState.HOME,
        PossessionState.AWAY,
        PossessionState.DEAD_BALL,
        PossessionState.UNKNOWN,
    ]

    assert [segment.duration_frames for segment in segments] == [
        2,
        1,
        1,
        1,
    ]


def test_missing_frames_break_segments() -> None:
    predictions = [
        prediction(10, PossessionState.HOME),
        prediction(11, PossessionState.HOME),
        prediction(15, PossessionState.HOME),
    ]

    segments = extract_possession_segments(predictions)

    assert segments == [
        PossessionSegment(10, 12, PossessionState.HOME),
        PossessionSegment(15, 16, PossessionState.HOME),
    ]


def test_duplicate_frames_rejected() -> None:
    predictions = [
        prediction(1, PossessionState.HOME),
        prediction(1, PossessionState.AWAY),
    ]

    with pytest.raises(ValueError, match="strictly increasing"):
        extract_possession_segments(predictions)


def test_out_of_order_frames_rejected() -> None:
    predictions = [
        prediction(5, PossessionState.HOME),
        prediction(4, PossessionState.HOME),
    ]

    with pytest.raises(ValueError, match="strictly increasing"):
        extract_possession_segments(predictions)


def test_mixed_model_versions_rejected() -> None:
    predictions = [
        prediction(0, PossessionState.HOME, "model-a"),
        prediction(1, PossessionState.HOME, "model-b"),
    ]

    with pytest.raises(ValueError, match="same model version"):
        extract_possession_segments(predictions)


def test_invalid_segment_boundaries() -> None:
    with pytest.raises(ValueError, match="exceed"):
        PossessionSegment(
            start_frame=5,
            end_frame=5,
            label=PossessionState.HOME,
        )

    with pytest.raises(ValueError, match="non-negative"):
        PossessionSegment(
            start_frame=-1,
            end_frame=5,
            label=PossessionState.HOME,
        )


def test_invalid_fps() -> None:
    segment = PossessionSegment(
        start_frame=0,
        end_frame=10,
        label=PossessionState.HOME,
    )

    with pytest.raises(ValueError, match="FPS"):
        segment.duration_seconds(0)

    with pytest.raises(ValueError, match="FPS"):
        segment.duration_seconds(float("nan"))
