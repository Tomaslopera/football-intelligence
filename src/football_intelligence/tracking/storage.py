"""Parquet storage for canonical tracking observations."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import Field

from football_intelligence.tracking.models import (
    BallObservation,
    PitchPosition,
    PlayerObservation,
    RecordingSource,
    TeamSide,
    TrackingFrame,
)

FRAME_FIELDS: list[Field] = [
    pa.field("match_id", pa.string()),
    pa.field("source", pa.string()),
    pa.field("frame", pa.int64()),
    pa.field("ball_x", pa.float64()),
    pa.field("ball_y", pa.float64()),
    pa.field("ball_speed_mps", pa.float64()),
]

PLAYER_FIELDS: list[Field] = [
    pa.field("match_id", pa.string()),
    pa.field("source", pa.string()),
    pa.field("frame", pa.int64()),
    pa.field("track_slot", pa.int64()),
    pa.field("team", pa.string()),
    pa.field("x", pa.float64()),
    pa.field("y", pa.float64()),
    pa.field("speed_mps", pa.float64()),
]

FRAME_SCHEMA = pa.schema(FRAME_FIELDS)
PLAYER_SCHEMA = pa.schema(PLAYER_FIELDS)


def _position_values(
    position: PitchPosition | None,
) -> tuple[float | None, float | None]:
    if position is None:
        return None, None

    return position.x, position.y


def _restore_position(
    x: float | None,
    y: float | None,
) -> PitchPosition | None:
    """Restore a position from nullable Parquet coordinates."""
    if x is None and y is None:
        return None

    if x is None or y is None:
        raise ValueError("Incomplete stored position: one coordinate is missing")

    return PitchPosition(x=x, y=y)


def write_tracking_parquet(
    frames: list[TrackingFrame],
    directory: Path,
) -> tuple[Path, Path]:
    """Persist tracking frames and player observations."""
    directory.mkdir(parents=True, exist_ok=True)

    frame_rows = []
    player_rows = []
    seen_frames = set()

    for frame in frames:
        key = (frame.match_id, frame.source, frame.frame)

        if key in seen_frames:
            raise ValueError(f"Duplicate tracking frame: {key}")

        seen_frames.add(key)

        ball_x, ball_y = _position_values(frame.ball.position)

        frame_rows.append(
            {
                "match_id": frame.match_id,
                "source": frame.source.value,
                "frame": frame.frame,
                "ball_x": ball_x,
                "ball_y": ball_y,
                "ball_speed_mps": frame.ball.speed_mps,
            }
        )

        for player in frame.players:
            x, y = _position_values(player.position)

            player_rows.append(
                {
                    "match_id": frame.match_id,
                    "source": frame.source.value,
                    "frame": frame.frame,
                    "track_slot": player.track_slot,
                    "team": player.team.value,
                    "x": x,
                    "y": y,
                    "speed_mps": player.speed_mps,
                }
            )

    frames_path = directory / "frames.parquet"
    players_path = directory / "players.parquet"

    pq.write_table(
        pa.Table.from_pylist(frame_rows, schema=FRAME_SCHEMA),
        frames_path,
        compression="zstd",
    )

    pq.write_table(
        pa.Table.from_pylist(player_rows, schema=PLAYER_SCHEMA),
        players_path,
        compression="zstd",
    )

    return frames_path, players_path


def read_tracking_parquet(
    directory: Path,
) -> list[TrackingFrame]:
    """Reconstruct canonical objects from the two Parquet files."""
    frame_rows = pq.read_table(directory / "frames.parquet").to_pylist()

    player_rows = pq.read_table(directory / "players.parquet").to_pylist()

    players_by_frame: dict[
        tuple[str, str, int],
        list[PlayerObservation],
    ] = {}

    for row in player_rows:
        key = (
            row["match_id"],
            row["source"],
            row["frame"],
        )

        players_by_frame.setdefault(key, []).append(
            PlayerObservation(
                track_slot=row["track_slot"],
                team=TeamSide(row["team"]),
                position=_restore_position(
                    row["x"],
                    row["y"],
                ),
                speed_mps=row["speed_mps"],
            )
        )

    frames = []
    seen_frames = set()

    for row in frame_rows:
        key = (
            row["match_id"],
            row["source"],
            row["frame"],
        )

        if key in seen_frames:
            raise ValueError(f"Duplicate stored frame: {key}")

        seen_frames.add(key)

        frames.append(
            TrackingFrame(
                match_id=row["match_id"],
                source=RecordingSource(row["source"]),
                frame=row["frame"],
                players=players_by_frame.pop(key, []),
                ball=BallObservation(
                    position=_restore_position(
                        row["ball_x"],
                        row["ball_y"],
                    ),
                    speed_mps=row["ball_speed_mps"],
                ),
            )
        )

    if players_by_frame:
        raise ValueError("Player observations reference unknown frames")

    return frames
