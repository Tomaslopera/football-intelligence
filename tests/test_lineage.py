import json

from football_intelligence.tracking.lineage import (
    create_lineage_manifest,
    file_sha256,
    write_quality_reports,
)
from football_intelligence.tracking.quality import (
    QualityConfig,
    analyze_tracking_quality,
)
from football_intelligence.tracking.storage import (
    write_tracking_parquet,
)


def test_file_hash_changes_when_contents_change(tmp_path):
    path = tmp_path / "example.txt"

    path.write_text("original", encoding="utf-8")
    first_hash = file_sha256(path)

    path.write_text("modified", encoding="utf-8")
    second_hash = file_sha256(path)

    assert first_hash != second_hash


def test_manifest_and_reports(tmp_path):
    dataset_dir = tmp_path / "dataset"
    reports_dir = tmp_path / "reports"

    write_tracking_parquet([], dataset_dir)

    config = QualityConfig()
    quality = analyze_tracking_quality(dataset_dir, config)

    manifest = create_lineage_manifest(
        dataset_dir,
        source_description="Synthetic test fixture",
        config=config,
        git_commit="abc123",
    )

    json_path, md_path = write_quality_reports(
        quality,
        manifest,
        reports_dir,
    )

    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["quality"]["total_frames"] == 0
    assert payload["lineage"]["git_commit"] == "abc123"
    assert len(payload["lineage"]["files"]["frames.parquet"]["sha256"]) == 64
    assert "Tracking Data Quality Report" in md_path.read_text(encoding="utf-8")
