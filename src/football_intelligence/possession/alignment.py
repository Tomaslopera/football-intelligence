"""Validate possession predictions against canonical match metadata.

This module does not implement inference or competition scoring.
It validates predictions produced by any future possession model.
"""

from collections.abc import Iterable, Iterator

from pydantic import BaseModel, ConfigDict, Field

from football_intelligence.domain import PossessionPrediction
from football_intelligence.tracking.models import (
    MatchMetadata,
    RecordingSource,
)


class PredictionContext(BaseModel):
    """Identity and metadata for a prediction sequence.

    MatchMetadata is reused from the canonical tracking layer.
    The recording source distinguishes tactical, broadcast,
    and synthetic tracking timelines.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    match: MatchMetadata
    source: RecordingSource
    model_version: str = Field(min_length=1)


def validate_prediction_sequence(
    predictions: Iterable[PossessionPrediction],
    context: PredictionContext,
    *,
    require_contiguous: bool = False,
) -> Iterator[PossessionPrediction]:
    """Validate predictions without materializing the sequence.

    Checks:
    - Frame numbers belong to the match.
    - Frames are strictly increasing.
    - Every prediction uses the expected model version.
    - Optional contiguous-frame enforcement.

    Validated predictions are yielded in their original order.

    This supports chunked processing and does not require
    loading a full match into memory.

    A sequence may cover a subset of the match. Full-match
    coverage is a separate artifact/submission validation.
    """
    previous_frame: int | None = None

    for prediction in predictions:
        if prediction.frame >= context.match.total_frames:
            raise ValueError(
                f"Prediction frame {prediction.frame} exceeds "
                f"match frame bounds [0, "
                f"{context.match.total_frames})"
            )

        if prediction.model_version != context.model_version:
            raise ValueError(
                "Prediction model version mismatch: "
                f"expected {context.model_version!r}, "
                f"received {prediction.model_version!r}"
            )

        if previous_frame is not None:
            if prediction.frame <= previous_frame:
                raise ValueError("Prediction frames must be strictly increasing")

            if require_contiguous and prediction.frame != previous_frame + 1:
                raise ValueError(
                    "Prediction sequence contains a frame gap: "
                    f"{previous_frame} -> {prediction.frame}"
                )

        previous_frame = prediction.frame
        yield prediction
