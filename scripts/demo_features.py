"""Demonstrate synthetic tracking-to-feature Parquet integration."""

from pathlib import Path

import duckdb

from football_intelligence.features.pipeline import (
    build_feature_dataset,
)
from football_intelligence.features.storage import (
    read_feature_parquet,
)
from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
)
from football_intelligence.tracking.models import (
    MatchMetadata,
    RecordingSource,
    TeamSide,
)
from football_intelligence.tracking.synthetic import (
    generate_tracking_table,
)


def main() -> None:
    total_frames = 100

    metadata = MatchMetadata(
        match_id="FEATURE-DEMO-001",
        home_team="Synthetic Home",
        away_team="Synthetic Away",
        fps=25.0,
        total_frames=total_frames,
        pitch_length_m=105.0,
        pitch_width_m=68.0,
    )

    table = generate_tracking_table(
        n_frames=total_frames,
        missing_ball_every=5,
    )

    frames = iter_tracking_frames(
        table,
        match_id=metadata.match_id,
        source=RecordingSource.SYNTHETIC,
        slot_teams={
            1: TeamSide.HOME,
            2: TeamSide.AWAY,
        },
    )

    output_path = Path("datasets/generated/features-demo/features.parquet")

    build_feature_dataset(
        frames,
        metadata,
        RecordingSource.SYNTHETIC,
        output_path,
    )

    feature_rows = read_feature_parquet(output_path)

    print(f"Feature rows: {len(feature_rows)}")
    print(f"First frame: {feature_rows[0].frame}")
    print(f"Last frame: {feature_rows[-1].frame}")

    with duckdb.connect(":memory:") as connection:
        summary = connection.execute(
            """
            SELECT
                COUNT(*) AS total_frames,
                COUNT_IF(ball_visible) AS ball_visible_frames,
                COUNT_IF(NOT ball_visible) AS missing_ball_frames,
                COUNT(nearest_home_distance_m)
                    AS home_distance_available,
                COUNT(ball_speed_estimate_mps)
                    AS ball_speed_available
            FROM read_parquet(?)
            """,
            [str(output_path)],
        ).fetchone()

    if summary is None:
        raise RuntimeError("DuckDB returned no feature summary")

    print("\nDuckDB feature summary:")
    print(f"Total frames: {summary[0]}")
    print(f"Ball visible: {summary[1]}")
    print(f"Ball missing: {summary[2]}")
    print(f"Home distance available: {summary[3]}")
    print(f"Estimated ball speed available: {summary[4]}")

    print(f"\nFeature dataset: {output_path.resolve()}")


if __name__ == "__main__":
    main()
