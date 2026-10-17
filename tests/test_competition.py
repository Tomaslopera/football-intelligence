"""Tests for official competition CSV export."""

import csv
from pathlib import Path

import pytest

from football_intelligence.domain import (
    PossessionPrediction,
    PossessionState,
)
from football_intelligence.possession.alignment import (
    PredictionContext,
)
from football_intelligence.possession.competition import (
    write_submission_csv,
)
from football_intelligence.tracking.models import (
    MatchMetadata,
    RecordingSource,
)


@pytest.fixture
def context() -> PredictionContext:
    return PredictionContext(
        match=MatchMetadata(
            match_id="synthetic-competition",
            home_team="Home",
            away_team="Away",
            fps=25.0,
            total_frames=4,
            pitch_length_m=105.0,
            pitch_width_m=68.0,
        ),
        source=RecordingSource.TACTICAL,
        model_version="baseline-v1",
    )


def prediction(
    frame: int,
    label: PossessionState = PossessionState.HOME,
    version: str = "baseline-v1",
) -> PossessionPrediction:
    return PossessionPrediction(
        frame=frame,
        label=label,
        model_version=version,
    )


def read_rows(path: Path) -> list[list[str]]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:
        return list(csv.reader(stream))


def test_writes_official_csv_format(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    predictions = [
        prediction(0, PossessionState.UNKNOWN),
        prediction(1, PossessionState.HOME),
        prediction(2, PossessionState.AWAY),
        prediction(3, PossessionState.DEAD_BALL),
    ]

    path = write_submission_csv(
        predictions,
        context,
        tmp_path / "submission.csv",
    )

    assert read_rows(path) == [
        ["frame", "label"],
        ["0", "X"],
        ["1", "H"],
        ["2", "A"],
        ["3", "D"],
    ]


def test_generator_input(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    predictions = (prediction(frame) for frame in range(4))

    path = write_submission_csv(
        predictions,
        context,
        tmp_path / "submission.csv",
    )

    assert len(read_rows(path)) == 5


def test_incomplete_submission_rejected(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="entire match",
    ):
        write_submission_csv(
            [prediction(frame) for frame in range(3)],
            context,
            tmp_path / "submission.csv",
        )


def test_wrong_start_frame_rejected(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    predictions = [
        prediction(1),
        prediction(2),
        prediction(3),
    ]

    with pytest.raises(
        ValueError,
        match="frame zero",
    ):
        write_submission_csv(
            predictions,
            context,
            tmp_path / "submission.csv",
        )


def test_frame_gap_rejected(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="frame gap",
    ):
        write_submission_csv(
            [
                prediction(0),
                prediction(1),
                prediction(3),
                prediction(4),
            ],
            context,
            tmp_path / "submission.csv",
        )


def test_wrong_model_version_rejected(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="version mismatch",
    ):
        write_submission_csv(
            [
                prediction(0),
                prediction(1, version="other-model"),
                prediction(2),
                prediction(3),
            ],
            context,
            tmp_path / "submission.csv",
        )


def test_broadcast_source_rejected(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    broadcast_context = context.model_copy(update={"source": RecordingSource.BROADCAST})

    with pytest.raises(
        ValueError,
        match="tactical timeline",
    ):
        write_submission_csv(
            [prediction(frame) for frame in range(4)],
            broadcast_context,
            tmp_path / "submission.csv",
        )


def test_invalid_sequence_does_not_overwrite_file(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    path = tmp_path / "submission.csv"
    path.write_text("existing content", encoding="utf-8")

    with pytest.raises(ValueError, match="entire match"):
        write_submission_csv(
            [prediction(0)],
            context,
            path,
        )

    assert path.read_text(encoding="utf-8") == ("existing content")


def test_empty_submission_rejected(
    context: PredictionContext,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="entire match"):
        write_submission_csv(
            [],
            context,
            tmp_path / "submission.csv",
        )
