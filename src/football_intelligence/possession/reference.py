"""Read public possession reference labels with explicit grading coverage.

The reference dataset distinguishes published labels from unavailable
ground truth. It does not implement competition scoring.
"""

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from football_intelligence.domain import PossessionState

# Official public Barcelona vs Athletic Club reference metadata.
BAR_ATH_TOTAL_FRAMES = 199_319
BAR_ATH_PUBLIC_GRADED_RANGES = ((11_185, 18_685),)

FrameRange = tuple[int, int]


@dataclass(frozen=True)
class ReferenceDataset:
    """Frame-aligned reference labels and their availability."""

    labels: tuple[PossessionState | None, ...]
    graded: tuple[bool, ...]

    def __post_init__(self) -> None:
        if len(self.labels) != len(self.graded):
            raise ValueError("Reference labels and grading mask lengths differ")

        for label, is_graded in zip(
            self.labels,
            self.graded,
            strict=True,
        ):
            if is_graded and label is None:
                raise ValueError("A graded frame must have a reference label")

            if not is_graded and label is not None:
                raise ValueError("Ungraded frames must not contain reference labels")

    @property
    def total_frames(self) -> int:
        return len(self.labels)

    @property
    def graded_frames(self) -> int:
        return sum(self.graded)


def _validate_graded_ranges(
    ranges: Sequence[FrameRange],
    total_frames: int,
) -> None:
    """Validate sorted, non-overlapping, half-open frame ranges."""
    previous_end = 0

    for start, end in ranges:
        if start < previous_end or start < 0 or end <= start or end > total_frames:
            raise ValueError(f"Invalid or overlapping graded range: ({start}, {end})")

        previous_end = end


def read_reference_csv(
    path: Path,
    *,
    expected_frames: int,
    graded_ranges: Sequence[FrameRange],
) -> ReferenceDataset:
    """Read reference labels using explicit published grading ranges.

    Each range is [start, end), with the end frame excluded.

    X outside graded ranges is treated as unavailable ground truth.
    X inside a graded range is rejected by this public-label reader.
    """
    if expected_frames <= 0:
        raise ValueError("Expected frame count must be positive")

    _validate_graded_ranges(
        graded_ranges,
        expected_frames,
    )

    graded = [False] * expected_frames

    for start, end in graded_ranges:
        for frame in range(start, end):
            graded[frame] = True

    labels: list[PossessionState | None] = []

    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as stream:
        reader = csv.reader(stream)

        header = next(reader, None)

        if header is None or [column.strip().lower() for column in header] != [
            "frame",
            "label",
        ]:
            raise ValueError("Reference CSV must have frame,label columns")

        for expected_frame, row in enumerate(reader):
            if expected_frame >= expected_frames:
                raise ValueError("Reference CSV has too many frames")

            if len(row) != 2:
                raise ValueError(f"Invalid CSV row at frame {expected_frame}")

            frame_text, label_text = row

            try:
                frame = int(frame_text.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid frame ID: {frame_text!r}") from exc

            if frame != expected_frame:
                raise ValueError(
                    f"Frame alignment error: expected "
                    f"{expected_frame}, received {frame}"
                )

            try:
                label = PossessionState(label_text.strip().upper())
            except ValueError as exc:
                raise ValueError(f"Invalid reference label at frame {frame}") from exc

            if graded[frame]:
                if label == PossessionState.UNKNOWN:
                    raise ValueError(f"Missing published label at frame {frame}")

                labels.append(label)
            else:
                if label != PossessionState.UNKNOWN:
                    raise ValueError(
                        f"Unexpected reference label outside "
                        f"graded range at frame {frame}"
                    )

                labels.append(None)

    if len(labels) != expected_frames:
        raise ValueError(
            "Reference CSV has incorrect frame count: "
            f"expected {expected_frames}, received {len(labels)}"
        )

    return ReferenceDataset(
        labels=tuple(labels),
        graded=tuple(graded),
    )
