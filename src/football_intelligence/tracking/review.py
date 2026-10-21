"""Aggregate-only local review of an existing tracking/feature audit.

Read-only DuckDB computations never export observation rows. Missing-interval
boundaries are reported explicitly; they are not possession labels.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import duckdb
import pyarrow.parquet as pq

from football_intelligence.features.storage import FEATURE_SCHEMA
from football_intelligence.tracking.lineage import file_sha256
from football_intelligence.tracking.storage import FRAME_SCHEMA, PLAYER_SCHEMA


def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    result = connection.execute(sql)
    names = [item[0] for item in result.description]
    return [dict(zip(names, row, strict=True)) for row in result.fetchall()]


def review_processed_audit(directory: Path) -> dict[str, Any]:
    """Independently recompute features and summarize anomalies locally."""
    audit = json.loads((directory / "audit.json").read_text())
    fingerprint_checks = {
        name: file_sha256(directory / "tracking" / name)
        == audit["lineage"]["files"][name]["sha256"]
        for name in ("frames.parquet", "players.parquet")
    }
    fingerprint_checks["features"] = (
        file_sha256(directory / "features/features-v1.0.parquet")
        == audit["feature_sha256"]
    )
    schemas_match = all(
        pq.read_schema(path).equals(schema, check_metadata=True)
        for path, schema in (
            (directory / "tracking/frames.parquet", FRAME_SCHEMA),
            (directory / "tracking/players.parquet", PLAYER_SCHEMA),
            (directory / "features/features-v1.0.parquet", FEATURE_SCHEMA),
        )
    )
    metadata = audit["metadata"]
    length = float(metadata["pitch_length_m"])
    width = float(metadata["pitch_width_m"])
    fps = float(metadata["fps"])
    # Use validated numeric metadata in SQL, never provider strings.
    if not all(0 < value < float("inf") for value in (length, width, fps)):
        raise ValueError("Invalid physical metadata")
    with (
        TemporaryDirectory(prefix="football-review-") as temporary,
        duckdb.connect(":memory:") as connection,
    ):
        connection.execute("SET memory_limit = '512MB'")
        connection.execute("SET threads = 2")
        connection.execute("SET temp_directory = ?", [temporary])
        connection.execute("CREATE MACRO hypot(x, y) AS SQRT(x*x + y*y)")
        connection.read_parquet(str(directory / "tracking/frames.parquet")).create_view(
            "frames"
        )
        connection.read_parquet(
            str(directory / "tracking/players.parquet")
        ).create_view("players")
        connection.read_parquet(
            str(directory / "features/features-v1.0.parquet")
        ).create_view("features")
        connection.execute(f"""
            CREATE VIEW motion AS
            SELECT *,
                CASE WHEN frame = previous_frame + 1 THEN
                    HYPOT((ball_x - previous_x) * {length},
                          (ball_y - previous_y) * {width}) END AS displacement,
                ball_x IS NOT NULL AND ball_y IS NOT NULL AS visible
            FROM (
                SELECT *,
                    LAG(frame) OVER w AS previous_frame,
                    LAG(ball_x) OVER w AS previous_x,
                    LAG(ball_y) OVER w AS previous_y,
                    LAG(ball_x, 2) OVER w AS previous_2_x,
                    LEAD(ball_x) OVER w AS next_x,
                    LEAD(ball_y) OVER w AS next_y,
                    LEAD(frame) OVER w AS next_frame
                FROM frames
                WINDOW w AS (PARTITION BY match_id, source ORDER BY frame)
            )
        """)
        connection.execute(f"""
            CREATE VIEW distances AS
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY match_id, source, frame, team
                ORDER BY distance NULLS LAST, observation_order
            ) AS nearest_rank
            FROM (
                SELECT p.*, f.ball_x, f.ball_y,
                    HYPOT((p.x - f.ball_x) * {length},
                          (p.y - f.ball_y) * {width}) AS distance
                FROM (SELECT *, ROW_NUMBER() OVER () AS observation_order FROM players) p
                JOIN frames f USING (match_id, source, frame)
                WHERE p.x IS NOT NULL AND p.y IS NOT NULL
            )
        """)
        connection.execute("""
            CREATE VIEW geometry AS
            SELECT f.*,
                COALESCE(p.home_players_visible, 0) AS home_players_visible,
                COALESCE(p.away_players_visible, 0) AS away_players_visible,
                p.home_mean_speed_mps, p.away_mean_speed_mps,
                p.nearest_home_distance_m, p.nearest_away_distance_m,
                p.nearest_home_speed_mps, p.nearest_away_speed_mps,
                p.nearest_away_distance_m - p.nearest_home_distance_m AS distance_advantage_m
            FROM motion f LEFT JOIN (
                SELECT match_id, source, frame,
                    COUNT(*) FILTER (WHERE team='H') AS home_players_visible,
                    COUNT(*) FILTER (WHERE team='A') AS away_players_visible,
                    AVG(speed_mps) FILTER (WHERE team='H') AS home_mean_speed_mps,
                    AVG(speed_mps) FILTER (WHERE team='A') AS away_mean_speed_mps,
                    MIN(distance) FILTER (WHERE team='H') AS nearest_home_distance_m,
                    MIN(distance) FILTER (WHERE team='A') AS nearest_away_distance_m,
                    MAX(speed_mps) FILTER (WHERE team='H' AND nearest_rank=1
                        AND distance IS NOT NULL) AS nearest_home_speed_mps,
                    MAX(speed_mps) FILTER (WHERE team='A' AND nearest_rank=1
                        AND distance IS NOT NULL) AS nearest_away_speed_mps
                FROM distances GROUP BY match_id, source, frame
            ) p USING (match_id, source, frame)
        """)
        connection.execute(f"""
            CREATE TEMP TABLE expected AS
            SELECT *, visible AS ball_visible,
                displacement AS ball_displacement_m,
                displacement * {fps} AS ball_speed_estimate_mps,
                CASE WHEN visible THEN 0 ELSE
                    COUNT(*) FILTER (WHERE NOT visible) OVER (
                        PARTITION BY match_id, source, streak_group ORDER BY frame
                    ) END AS ball_missing_streak_frames,
                CASE WHEN frame = previous_frame + 1 THEN
                    distance_advantage_m - LAG(distance_advantage_m) OVER (
                        PARTITION BY match_id, source ORDER BY frame
                    ) END AS distance_advantage_change_m
            FROM (
                SELECT *, SUM(CASE WHEN visible OR previous_frame IS NULL
                    OR frame != previous_frame + 1 THEN 1 ELSE 0 END) OVER (
                        PARTITION BY match_id, source ORDER BY frame
                    ) AS streak_group
                FROM geometry
            )
        """)
        identities = _rows(
            connection,
            """
            SELECT (SELECT COUNT(*) FROM frames) AS tracking_frames,
                (SELECT COUNT(*) FROM features) AS feature_frames,
                (SELECT COUNT(*) FROM (SELECT DISTINCT match_id, source, frame FROM features))
                    AS distinct_feature_keys,
                (SELECT COUNT(*) FROM frames t ANTI JOIN features f
                    USING (match_id, source, frame)) AS missing_feature_keys,
                (SELECT COUNT(*) FROM features f ANTI JOIN frames t
                    USING (match_id, source, frame)) AS extra_feature_keys
        """,
        )[0]
        mismatches: dict[str, int] = {}
        for field in FEATURE_SCHEMA:
            name = field.name
            if name in {"match_id", "source", "frame"}:
                continue
            if str(field.type) == "double":
                condition = f"""(e.{name} IS NULL) != (f.{name} IS NULL)
                    OR (e.{name} IS NOT NULL AND f.{name} IS NOT NULL AND
                    (NOT ISFINITE(f.{name}) OR ABS(e.{name} - f.{name}) > 1e-8))"""
            else:
                condition = f"e.{name} IS DISTINCT FROM f.{name}"
            mismatches[name] = _rows(
                connection,
                f"""
                SELECT COUNT(*) FILTER (WHERE {condition}) AS n
                FROM expected e JOIN features f USING (match_id, source, frame)
            """,
            )[0]["n"]
        anomalies = _rows(
            connection,
            f"""
            SELECT COUNT(*) AS above_50_mps,
                COUNT(*) FILTER (WHERE frame != previous_frame+1
                    OR previous_x IS NULL OR NOT visible) AS invalid_motion_context,
                COUNT(*) FILTER (WHERE previous_2_x IS NULL) AS near_previous_missing,
                COUNT(*) FILTER (WHERE next_x IS NULL) AS next_ball_missing,
                COUNT(*) FILTER (WHERE ball_x NOT BETWEEN 0 AND 1 OR ball_y NOT BETWEEN 0 AND 1
                    OR previous_x NOT BETWEEN 0 AND 1 OR previous_y NOT BETWEEN 0 AND 1) AS out_of_bounds_endpoint,
                COUNT(*) FILTER (WHERE next_frame=frame+1 AND
                    HYPOT((next_x-ball_x)*{length}, (next_y-ball_y)*{width})*{fps}>50
                    AND HYPOT((next_x-previous_x)*{length}, (next_y-previous_y)*{width})*{fps}/2<=15)
                    AS jump_and_return_candidates,
                MIN(displacement) AS min_displacement_m,
                MEDIAN(displacement) AS median_displacement_m,
                MAX(displacement) AS max_displacement_m
            FROM motion WHERE displacement*{fps}>50
        """,
        )[0]
        high_runs = _rows(
            connection,
            f"""
            WITH high AS (
                SELECT match_id, source, frame,
                    frame-ROW_NUMBER() OVER (PARTITION BY match_id,source ORDER BY frame) AS run
                FROM motion WHERE displacement*{fps}>50
            ), runs AS (
                SELECT COUNT(*) AS n FROM high GROUP BY match_id,source,run
            )
            SELECT COUNT(*) AS runs, MEDIAN(n) AS median_run_frames,
                MAX(n) AS longest_run_frames,
                COUNT(*) FILTER (WHERE n=1) AS single_frame_runs,
                COALESCE(SUM(n) FILTER (WHERE n>={fps}),0) AS frames_in_runs_at_least_one_second
            FROM runs
        """,
        )[0]
        intervals = _rows(
            connection,
            f"""
            SELECT MIN(frame) AS start_frame, MAX(frame)+1 AS end_frame_exclusive,
                COUNT(*) AS frames, COUNT(*)/{fps} AS seconds,
                AVG(home_players_visible+away_players_visible) AS mean_visible_players,
                MIN(home_players_visible+away_players_visible) AS min_visible_players,
                MAX(home_players_visible+away_players_visible) AS max_visible_players
            FROM expected WHERE NOT visible
            GROUP BY match_id, source, streak_group
            ORDER BY frames DESC, start_frame LIMIT 10
        """,
        )
        bounds = _rows(
            connection,
            """
            SELECT
                (SELECT COUNT(*) FROM frames WHERE ball_x NOT BETWEEN 0 AND 1
                    OR ball_y NOT BETWEEN 0 AND 1) AS ball_out_of_bounds,
                (SELECT COUNT(*) FROM players WHERE x NOT BETWEEN 0 AND 1
                    OR y NOT BETWEEN 0 AND 1) AS player_out_of_bounds,
                (SELECT COUNT(*) FROM features f JOIN frames t USING (match_id,source,frame)
                    WHERE (ball_x NOT BETWEEN 0 AND 1 OR ball_y NOT BETWEEN 0 AND 1)
                    AND f.ball_visible) AS out_of_bounds_ball_retained_in_features
        """,
        )[0]
        speeds = _rows(
            connection,
            f"""
            WITH steps AS (
                SELECT *, LAG(frame) OVER w AS previous_frame,
                    LAG(x) OVER w AS previous_x, LAG(y) OVER w AS previous_y
                FROM players
                WINDOW w AS (PARTITION BY match_id, source, track_slot ORDER BY frame)
            ), compared AS (
                SELECT *, HYPOT((x-previous_x)*{length}, (y-previous_y)*{width})*{fps}
                    AS displacement_speed FROM steps WHERE frame=previous_frame+1
            )
            SELECT COUNT(speed_mps) AS speed_observations,
                MEDIAN(speed_mps) AS reported_median_mps, MAX(speed_mps) AS reported_max_mps,
                MEDIAN(displacement_speed) AS displacement_median_mps,
                MEDIAN(displacement_speed/speed_mps) FILTER (WHERE speed_mps>=0.1
                    AND displacement_speed BETWEEN 0.1 AND 15) AS motion_to_reported_ratio,
                MEDIAN(ABS(displacement_speed-speed_mps)) FILTER (WHERE displacement_speed<=15)
                    AS median_absolute_error_current_scale,
                MEDIAN(ABS(displacement_speed-speed_mps*3.6)) FILTER (WHERE displacement_speed<=15)
                    AS median_absolute_error_times_3_6,
                COUNT(*) FILTER (WHERE displacement_speed>15) AS suspicious_slot_motion_steps
            FROM compared
        """,
        )[0]
    aligned = (
        identities["tracking_frames"]
        == identities["feature_frames"]
        == identities["distinct_feature_keys"]
        and not identities["missing_feature_keys"]
        and not identities["extra_feature_keys"]
        and not any(mismatches.values())
    )
    return {
        "input_fingerprints_match_audit": fingerprint_checks,
        "parquet_schemas_match": schemas_match,
        "feature_consistency_passed": aligned,
        "alignment": identities,
        "feature_mismatch_counts": mismatches,
        "ball_speed_anomalies": anomalies,
        "high_speed_runs": high_runs,
        "longest_missing_intervals": intervals,
        "bounds": bounds,
        "player_speed_diagnostics": speeds,
        "interpretation": "Slot motion and jump-return tests are diagnostics, not identities or ground truth",
    }
