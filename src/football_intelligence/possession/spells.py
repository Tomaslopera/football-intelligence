"""Extract contiguous possession-state segments.

These are generic runs of possession labels, not necessarily
the possession spells scored by the official evaluator.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from football_intelligence.domain import (
    PossessionPrediction,
    PossessionState,
)


@dataclass(frozen=True)
class PossessionSegment:
    """A continuous run of one possession state."""

    start_frame: int
    end_frame: int  # Exclusive
    label: PossessionState

    def __post_init__(self) -> None:
        if self.start_frame < 0:
            raise ValueError("Start frame must be non-negative")

        if self.end_frame <= self.start_frame:
            raise ValueError("End frame must exceed start frame")

    @property
    def duration_frames(self) -> int:
        """Return the number of frames in the segment."""
        return self.end_frame - self.start_frame

    def duration_seconds(self, fps: float) -> float:
        """Return the segment duration in seconds."""
        if not 0 < fps < float("inf"):
            raise ValueError("FPS must be finite and positive")

        return self.duration_frames / fps


def extract_possession_segments(
    predictions: Sequence[PossessionPrediction],
) -> list[PossessionSegment]:
    """Group ordered predictions into contiguous state segments.

    A new segment starts when:
    - The possession label changes.
    - A frame ID is missing.

    Predictions must have strictly increasing frame IDs
    and use the same model version.
    """
    if not predictions:
        return []

    model_version = predictions[0].model_version
    start_frame = predictions[0].frame
    previous_frame = start_frame
    current_label = predictions[0].label

    segments: list[PossessionSegment] = []

    for prediction in predictions[1:]:
        if prediction.model_version != model_version:
            raise ValueError("All predictions must use the same model version")

        if prediction.frame <= previous_frame:
            raise ValueError("Prediction frames must be strictly increasing")

        label_changed = prediction.label != current_label
        frame_gap = prediction.frame != previous_frame + 1

        if label_changed or frame_gap:
            segments.append(
                PossessionSegment(
                    start_frame=start_frame,
                    end_frame=previous_frame + 1,
                    label=current_label,
                )
            )

            start_frame = prediction.frame
            current_label = prediction.label

        previous_frame = prediction.frame

    segments.append(
        PossessionSegment(
            start_frame=start_frame,
            end_frame=previous_frame + 1,
            label=current_label,
        )
    )

    return segments
