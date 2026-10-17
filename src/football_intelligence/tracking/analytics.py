"""SQL analytics over Parquet tracking datasets."""

from pathlib import Path

import duckdb


def tracking_summary(
    directory: Path,
) -> dict[str, int]:
    """Compute basic tracking coverage statistics."""
    frames_path = str(directory / "frames.parquet")
    players_path = str(directory / "players.parquet")

    with duckdb.connect(":memory:") as connection:
        frame_result = connection.execute(
            """
            SELECT
                COUNT(*) AS total_frames,
                COUNT(ball_x) AS ball_visible
            FROM read_parquet(?)
            """,
            [frames_path],
        ).fetchone()

        if frame_result is None:
            raise RuntimeError("DuckDB returned no frame summary")

        total_frames = int(frame_result[0])
        ball_visible = int(frame_result[1])

        player_result = connection.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?)
            WHERE x IS NOT NULL AND y IS NOT NULL
            """,
            [players_path],
        ).fetchone()

        if player_result is None:
            raise RuntimeError("DuckDB returned no player summary")

        tracked_players = int(player_result[0])

    return {
        "total_frames": total_frames,
        "ball_visible_frames": ball_visible,
        "missing_ball_frames": total_frames - ball_visible,
        "tracked_player_observations": tracked_players,
    }
