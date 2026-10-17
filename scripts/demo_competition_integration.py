"""Demonstrate compatibility with the Metrica possession format.

Requires the official challenge repository as a separate local
checkout. Uses public reference labels and synthetic predictions.

This is an integration demonstration, not a trained model.
"""

import argparse
from pathlib import Path

from football_intelligence.domain import (
    PossessionPrediction,
    PossessionState,
)
from football_intelligence.possession.alignment import PredictionContext
from football_intelligence.possession.competition import (
    write_submission_csv,
)
from football_intelligence.possession.reference import (
    BAR_ATH_PUBLIC_GRADED_RANGES,
    BAR_ATH_TOTAL_FRAMES,
    read_reference_csv,
)
from football_intelligence.tracking.models import (
    MatchMetadata,
    RecordingSource,
)

# Artificial predictions to verify file formatting only.
DEMO_LABELS = (
    PossessionState.HOME,
    PossessionState.AWAY,
    PossessionState.DEAD_BALL,
    PossessionState.UNKNOWN,
)

EXPECTED_PUBLIC_COUNTS = {
    PossessionState.HOME: 3454,
    PossessionState.AWAY: 2577,
    PossessionState.DEAD_BALL: 1469,
}


def generate_demo_predictions():
    """Yield one synthetic prediction for each tactical frame."""
    for frame in range(BAR_ATH_TOTAL_FRAMES):
        label = DEMO_LABELS[(frame // 250) % len(DEMO_LABELS)]

        yield PossessionPrediction(
            frame=frame,
            label=label,
            model_version="synthetic-format-check-v1",
        )


def build_context() -> PredictionContext:
    """Describe the official match's prediction timeline."""
    return PredictionContext(
        match=MatchMetadata(
            match_id="BAR-ATH",
            home_team="Barcelona",
            away_team="Athletic Club",
            fps=25.0,
            total_frames=BAR_ATH_TOTAL_FRAMES,
            pitch_length_m=105.0,
            pitch_width_m=68.0,
        ),
        source=RecordingSource.TACTICAL,
        model_version="synthetic-format-check-v1",
    )


def verify_public_reference(path: Path) -> None:
    """Verify public reference coverage and known label counts."""
    reference = read_reference_csv(
        path,
        expected_frames=BAR_ATH_TOTAL_FRAMES,
        graded_ranges=BAR_ATH_PUBLIC_GRADED_RANGES,
    )

    assert reference.total_frames == BAR_ATH_TOTAL_FRAMES
    assert reference.graded_frames == 7_500

    counts = {
        label: sum(1 for value in reference.labels if value == label)
        for label in EXPECTED_PUBLIC_COUNTS
    }

    if counts != EXPECTED_PUBLIC_COUNTS:
        raise ValueError(
            f"Public reference label counts do not match published metadata: {counts}"
        )

    print("\nPublic reference verified:")
    print(f"  Total frames: {reference.total_frames}")
    print(f"  Published labels: {reference.graded_frames}")

    for label, count in counts.items():
        print(f"  {label.value}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and inspect a synthetic submission"
    )

    parser.add_argument(
        "--official-repo",
        type=Path,
        required=True,
        help="Path to the local Metrica challenge repository",
    )

    args = parser.parse_args()

    official_repo = args.official_repo.resolve()

    reference_path = (
        official_repo / "evaluation" / "gt" / "BAR-ATH_possession_gt_public.csv"
    )

    validator_path = official_repo / "evaluation" / "validate_submission.py"

    evaluator_path = official_repo / "evaluation" / "run_evaluation.py"

    for path in (
        reference_path,
        validator_path,
        evaluator_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    output_dir = Path("datasets/generated/competition-integration").resolve()

    submission_path = output_dir / "synthetic_submission.csv"

    print("Generating complete synthetic submission...")

    write_submission_csv(
        generate_demo_predictions(),
        build_context(),
        submission_path,
    )

    print(f"Created: {submission_path}")

    verify_public_reference(reference_path)

    print("\nNext steps:")
    print("Run the official submission validator:")
    print(f'python "{validator_path}" "{submission_path}"')

    print("\nRun the official public evaluator:")
    print(f'python "{evaluator_path}" --results "{output_dir}" --gt public')


if __name__ == "__main__":
    main()
