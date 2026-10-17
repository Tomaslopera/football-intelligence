"""Run a local data quality report against synthetic tracking data."""

import os
from pathlib import Path

from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
)
from football_intelligence.tracking.lineage import (
    create_lineage_manifest,
    write_quality_reports,
)
from football_intelligence.tracking.models import (
    RecordingSource,
    TeamSide,
)
from football_intelligence.tracking.quality import (
    QualityConfig,
    analyze_tracking_quality,
)
from football_intelligence.tracking.storage import (
    write_tracking_parquet,
)
from football_intelligence.tracking.synthetic import (
    generate_tracking_table,
)


def main() -> None:
    table = generate_tracking_table(n_frames=100)

    frames = list(
        iter_tracking_frames(
            table,
            match_id="DEMO-QUALITY-001",
            source=RecordingSource.SYNTHETIC,
            slot_teams={
                1: TeamSide.HOME,
                2: TeamSide.AWAY,
            },
        )
    )

    dataset_dir = Path("datasets/generated/quality-demo")
    reports_dir = Path("datasets/generated/quality-reports")

    write_tracking_parquet(frames, dataset_dir)

    config = QualityConfig()

    report = analyze_tracking_quality(dataset_dir, config)

    manifest = create_lineage_manifest(
        dataset_dir,
        source_description="Deterministic synthetic tracking demo",
        config=config,
        git_commit=os.environ.get("GITHUB_SHA"),
    )

    json_path, markdown_path = write_quality_reports(
        report,
        manifest,
        reports_dir,
    )

    print(f"Frames analyzed: {report.total_frames}")
    print(f"Ball coverage: {report.ball_coverage_pct:.2f}%")
    print(f"Missing frame IDs: {report.missing_frame_ids}")
    print(
        f"Spatial anomalies: {report.ball_out_of_bounds + report.players_out_of_bounds}"
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


if __name__ == "__main__":
    main()
