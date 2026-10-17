"""Normalize tracking tables into canonical domain models."""

import math
import re
from collections.abc import Iterator, Mapping
from typing import Any, cast

import pandas as pd

from football_intelligence.tracking.alignment import (
    atd_to_video_frame,
)
from football_intelligence.tracking.models import (
    BallObservation,
    PitchPosition,
    PlayerObservation,
    RecordingSource,
    TeamSide,
    TrackingFrame,
)

SLOT_COLUMN = re.compile(r"^([1-9]\d*)_([xys])$")


def optional_number(value: Any) -> float | None:
    """Convert a missing numerical value to None.

    Reject infinities and non-numeric values rather than hiding them.
    """
    if value is None or pd.isna(value):
        return None

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid tracking number: {value!r}") from exc

    if not math.isfinite(result):
        raise ValueError("Tracking values must be finite")

    return result


def optional_position(
    x: Any,
    y: Any,
) -> PitchPosition | None:
    """Missing coordinates produce a missing observation."""
    px = optional_number(x)
    py = optional_number(y)

    if px is None and py is None:
        return None

    if px is None or py is None:
        raise ValueError("Incomplete position: one coordinate is missing")

    return PitchPosition(x=px, y=py)


def find_track_slots(columns: list[str]) -> list[int]:
    """Discover slots from documented x/y/s column names."""
    slots: set[int] = set()

    for name in columns:
        match = SLOT_COLUMN.fullmatch(name)
        if match:
            slots.add(int(match.group(1)))

    return sorted(slots)


def normalize_record(
    record: Mapping[str, Any],
    *,
    match_id: str,
    source: RecordingSource,
    slot_teams: Mapping[int, TeamSide],
) -> TrackingFrame:
    """Convert one Metrica-shaped row into a TrackingFrame."""
    frame_id = int(record["frame_id"])

    if frame_id != record["frame_id"]:
        raise ValueError("Frame ID must be an integer")

    players = []

    for slot in find_track_slots(list(record)):
        position = optional_position(
            record.get(f"{slot}_x"),
            record.get(f"{slot}_y"),
        )
        speed = optional_number(record.get(f"{slot}_s"))

        if position is None and speed is None:
            continue

        if slot not in slot_teams:
            raise ValueError(f"Missing team mapping for track slot {slot}")

        players.append(
            PlayerObservation(
                track_slot=slot,
                team=slot_teams[slot],
                position=position,
                speed_mps=speed,
            )
        )

    return TrackingFrame(
        match_id=match_id,
        source=source,
        frame=atd_to_video_frame(frame_id),
        players=players,
        ball=BallObservation(
            position=optional_position(
                record.get("ball_x"),
                record.get("ball_y"),
            )
        ),
    )



def iter_tracking_frames(
    table: pd.DataFrame,
    *,
    match_id: str,
    source: RecordingSource,
    slot_teams: Mapping[int, TeamSide],
) -> Iterator[TrackingFrame]:
    """Validate frame order and normalize table records."""
    if "frame_id" not in table.columns:
        raise ValueError("Missing required frame_id column")

    # Ensure all DataFrame column names are strings.
    if not all(isinstance(column, str) for column in table.columns):
        raise ValueError("Tracking DataFrame columns must be strings")

    previous_id = 0

    # Pandas types column keys as Hashable.
    # We validated above that all keys are strings.
    records = cast(
        list[dict[str, Any]],
        table.to_dict(orient="records"),
    )

    for record in records:
        frame_id = record["frame_id"]

        # Require a contiguous one-based sequence.
        if frame_id != previous_id + 1:
            raise ValueError(
                "ATD frame IDs must be sequential, "
                f"expected {previous_id + 1}, got {frame_id}"
            )

        yield normalize_record(
            record,
            match_id=match_id,
            source=source,
            slot_teams=slot_teams,
        )

        previous_id = frame_id

