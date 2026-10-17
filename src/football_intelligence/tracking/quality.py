"""Data quality checks for stored football tracking data."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class QualityConfig:
    """Thresholds for interpreting tracking coordinates and speed."""

    coordinate_min: float = 0.0
    coordinate_max: float = 1.0
    max_player_speed_mps: float = 15.0


@dataclass(frozen=True)
class QualityReport:
    """Measurements of dataset completeness and consistency."""

    total_frames: int
    missing_ball_frames: int
    missing_player_positions: int
    tracked_player_observations: int
    missing_frame_ids: int
    frame_gaps: int
    duplicate_frames: int
    duplicate_player_observations: int
    orphan_player_observations: int
    ball_out_of_bounds: int
    players_out_of_bounds: int
    suspicious_player_speeds: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def ball_coverage_pct(self) -> float:
        if self.total_frames == 0:
            return 0.0

        return (
            100.0 * (self.total_frames - self.missing_ball_frames) / self.total_frames
        )


def _query_row(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    parameters: list[Any],
) -> tuple[Any, ...]:
    """Execute a SQL query that must return one result row."""
    result = connection.execute(sql, parameters).fetchone()

    if result is None:
        raise RuntimeError("Quality query returned no row")

    return result


def analyze_tracking_quality(
    directory: Path,
    config: QualityConfig | None = None,
) -> QualityReport:
    """Inspect tracking Parquet files without modifying them."""
    if config is None:
        config = QualityConfig()

    if config.coordinate_min >= config.coordinate_max:
        raise ValueError("Invalid coordinate boundaries")

    if config.max_player_speed_mps <= 0:
        raise ValueError("Maximum player speed must be positive")

    frames_path = str(directory / "frames.parquet")
    players_path = str(directory / "players.parquet")

    with duckdb.connect(":memory:") as connection:
        frame_stats = _query_row(
            connection,
            """
            SELECT
                COUNT(*),
                COUNT(*) FILTER (
                    WHERE ball_x IS NULL OR ball_y IS NULL
                ),
                COUNT(*) FILTER (
                    WHERE ball_x IS NOT NULL
                      AND ball_y IS NOT NULL
                      AND (
                          ball_x < ? OR ball_x > ?
                          OR ball_y < ? OR ball_y > ?
                      )
                )
            FROM read_parquet(?)
            """,
            [
                config.coordinate_min,
                config.coordinate_max,
                config.coordinate_min,
                config.coordinate_max,
                frames_path,
            ],
        )

        temporal_stats = _query_row(
            connection,
            """
            WITH distinct_frames AS (
                SELECT DISTINCT match_id, source, frame
                FROM read_parquet(?)
            ),
            sequenced AS (
                SELECT
                    frame,
                    LAG(frame) OVER (
                        PARTITION BY match_id, source
                        ORDER BY frame
                    ) AS previous_frame
                FROM distinct_frames
            )
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN previous_frame IS NOT NULL
                        AND frame > previous_frame + 1
                        THEN frame - previous_frame - 1
                        ELSE 0
                    END
                ), 0),
                COUNT(*) FILTER (
                    WHERE previous_frame IS NOT NULL
                    AND frame > previous_frame + 1
                )
            FROM sequenced
            """,
            [frames_path],
        )

        duplicate_frames = _query_row(
            connection,
            """
            SELECT COALESCE(SUM(n - 1), 0)
            FROM (
                SELECT COUNT(*) AS n
                FROM read_parquet(?)
                GROUP BY match_id, source, frame
                HAVING COUNT(*) > 1
            )
            """,
            [frames_path],
        )[0]

        player_stats = _query_row(
            connection,
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE x IS NULL OR y IS NULL
                ),
                COUNT(*) FILTER (
                    WHERE x IS NOT NULL AND y IS NOT NULL
                ),
                COUNT(*) FILTER (
                    WHERE x IS NOT NULL AND y IS NOT NULL
                    AND (
                        x < ? OR x > ?
                        OR y < ? OR y > ?
                    )
                ),
                COUNT(*) FILTER (
                    WHERE speed_mps > ?
                )
            FROM read_parquet(?)
            """,
            [
                config.coordinate_min,
                config.coordinate_max,
                config.coordinate_min,
                config.coordinate_max,
                config.max_player_speed_mps,
                players_path,
            ],
        )

        duplicate_players = _query_row(
            connection,
            """
            SELECT COALESCE(SUM(n - 1), 0)
            FROM (
                SELECT COUNT(*) AS n
                FROM read_parquet(?)
                GROUP BY match_id, source, frame, track_slot
                HAVING COUNT(*) > 1
            )
            """,
            [players_path],
        )[0]

        orphan_players = _query_row(
            connection,
            """
            SELECT COUNT(*)
            FROM read_parquet(?) AS p
            WHERE NOT EXISTS (
                SELECT 1
                FROM read_parquet(?) AS f
                WHERE f.match_id = p.match_id
                  AND f.source = p.source
                  AND f.frame = p.frame
            )
            """,
            [players_path, frames_path],
        )[0]

    return QualityReport(
        total_frames=int(frame_stats[0]),
        missing_ball_frames=int(frame_stats[1]),
        ball_out_of_bounds=int(frame_stats[2]),
        missing_frame_ids=int(temporal_stats[0]),
        frame_gaps=int(temporal_stats[1]),
        duplicate_frames=int(duplicate_frames),
        missing_player_positions=int(player_stats[0]),
        tracked_player_observations=int(player_stats[1]),
        players_out_of_bounds=int(player_stats[2]),
        suspicious_player_speeds=int(player_stats[3]),
        duplicate_player_observations=int(duplicate_players),
        orphan_player_observations=int(orphan_players),
    )
