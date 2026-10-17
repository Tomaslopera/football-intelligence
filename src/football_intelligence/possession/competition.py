"""Competition CSV export for possession predictions.

The official submission contains exactly two columns:
frame,label

Competition scoring remains the responsibility of the
official Metrica evaluator.
"""

import csv
from collections.abc import Iterable
from pathlib import Path

from football_intelligence.domain import PossessionPrediction
from football_intelligence.possession.alignment import (
    PredictionContext,
    validate_prediction_sequence,
)
from football_intelligence.tracking.models import RecordingSource


def write_submission_csv(
    predictions: Iterable[PossessionPrediction],
    context: PredictionContext,
    output_path: Path,
) -> Path:
    """Write a complete tactical-frame possession submission.

    Enforce:
    - Tactical reference timeline.
    - Correct match frame bounds.
    - One prediction per frame, starting at zero.
    - Consistent model version.
    - Official frame,label CSV structure.

    This validates format, not prediction accuracy.
    """
    if context.source != RecordingSource.TACTICAL:
        raise ValueError("Competition submissions require the tactical timeline")

    validated = validate_prediction_sequence(
        predictions,
        context,
        require_contiguous=True,
    )

    # Materialize before writing so incomplete sequences do not
    # replace an existing submission file.
    records = list(validated)
    expected_frames = context.match.total_frames

    if records and records[0].frame != 0:
        raise ValueError("Submission must start at frame zero")

    if len(records) != expected_frames:
        raise ValueError(
            "Submission must cover the entire match: "
            f"expected {expected_frames} frames, "
            f"received {len(records)}"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame", "label"])

        for prediction in records:
            writer.writerow(
                [
                    prediction.frame,
                    prediction.label.value,
                ]
            )

    return output_path
