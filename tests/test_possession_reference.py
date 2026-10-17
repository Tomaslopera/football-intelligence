"""Tests for public possession reference loading."""

import csv
from pathlib import Path

import pytest

from football_intelligence.domain import PossessionState
from football_intelligence.possession.reference import (
    BAR_ATH_PUBLIC_GRADED_RANGES,
    BAR_ATH_TOTAL_FRAMES,
    read_reference_csv,
)


def write_reference(
    path: Path,
    labels: list[str],
) -> None:
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame", "label"])

        for frame, label in enumerate(labels):
            writer.writerow([frame, label])


def test_public_reference_metadata() -> None:
    assert BAR_ATH_TOTAL_FRAMES == 199_319
    assert BAR_ATH_PUBLIC_GRADED_RANGES == ((11_185, 18_685),)

    start, end = BAR_ATH_PUBLIC_GRADED_RANGES[0]

    assert end - start == 7_500


def test_loads_grading_mask(tmp_path: Path) -> None:
    path = tmp_path / "reference.csv"

    write_reference(
        path,
        ["X", "H", "A", "D", "X"],
    )

    reference = read_reference_csv(
        path,
        expected_frames=5,
        graded_ranges=[(1, 4)],
    )

    assert reference.total_frames == 5
    assert reference.graded_frames == 3

    assert reference.graded == (
        False,
        True,
        True,
        True,
        False,
    )

    assert reference.labels == (
        None,
        PossessionState.HOME,
        PossessionState.AWAY,
        PossessionState.DEAD_BALL,
        None,
    )


def test_rejects_missing_published_label(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    write_reference(path, ["X", "H", "X", "D"])

    with pytest.raises(
        ValueError,
        match="Missing published label",
    ):
        read_reference_csv(
            path,
            expected_frames=4,
            graded_ranges=[(1, 4)],
        )


def test_rejects_label_outside_published_window(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    write_reference(path, ["H", "H", "A", "X"])

    with pytest.raises(
        ValueError,
        match="outside graded range",
    ):
        read_reference_csv(
            path,
            expected_frames=4,
            graded_ranges=[(1, 3)],
        )


def test_rejects_missing_frames(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    write_reference(path, ["X", "H", "A"])

    with pytest.raises(
        ValueError,
        match="incorrect frame count",
    ):
        read_reference_csv(
            path,
            expected_frames=4,
            graded_ranges=[(1, 3)],
        )


def test_rejects_frame_misalignment(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    path.write_text(
        "frame,label\n0,X\n2,H\n3,A\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Frame alignment error",
    ):
        read_reference_csv(
            path,
            expected_frames=3,
            graded_ranges=[(1, 3)],
        )


def test_rejects_invalid_labels(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    write_reference(path, ["X", "INVALID", "A"])

    with pytest.raises(
        ValueError,
        match="Invalid reference label",
    ):
        read_reference_csv(
            path,
            expected_frames=3,
            graded_ranges=[(1, 3)],
        )


def test_rejects_overlapping_ranges(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    write_reference(path, ["H", "A", "D", "H"])

    with pytest.raises(
        ValueError,
        match="Invalid or overlapping",
    ):
        read_reference_csv(
            path,
            expected_frames=4,
            graded_ranges=[
                (0, 3),
                (2, 4),
            ],
        )


def test_rejects_extra_frames(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    write_reference(path, ["H", "A", "D"])

    with pytest.raises(
        ValueError,
        match="too many frames",
    ):
        read_reference_csv(
            path,
            expected_frames=2,
            graded_ranges=[(0, 2)],
        )


def test_accepts_multiple_published_windows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.csv"

    write_reference(
        path,
        ["H", "A", "X", "D", "H"],
    )

    reference = read_reference_csv(
        path,
        expected_frames=5,
        graded_ranges=[
            (0, 2),
            (3, 5),
        ],
    )

    assert reference.graded_frames == 4
    assert reference.labels[2] is None
    assert reference.labels[3] == PossessionState.DEAD_BALL
