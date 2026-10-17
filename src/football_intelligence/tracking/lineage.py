"""Dataset fingerprints and quality report generation."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from football_intelligence.tracking.quality import (
    QualityConfig,
    QualityReport,
)

SCHEMA_VERSION = "1.0"


def file_sha256(path: Path) -> str:
    """Calculate a file fingerprint without loading it all at once."""
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def create_lineage_manifest(
    directory: Path,
    *,
    source_description: str,
    config: QualityConfig,
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Identify the exact Parquet inputs and quality configuration."""
    files = {}

    for name in ("frames.parquet", "players.parquet"):
        path = directory / name

        files[name] = {
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_description": source_description,
        "git_commit": git_commit,
        "quality_config": asdict(config),
        "files": files,
    }


def write_quality_reports(
    report: QualityReport,
    manifest: dict[str, Any],
    output_directory: Path,
) -> tuple[Path, Path]:
    """Write machine-readable JSON and human-readable Markdown."""
    output_directory.mkdir(parents=True, exist_ok=True)

    json_path = output_directory / "quality.json"
    markdown_path = output_directory / "quality.md"

    payload = {
        "quality": {
            **report.to_dict(),
            "ball_coverage_pct": report.ball_coverage_pct,
        },
        "lineage": manifest,
    }

    json_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = f"""# Tracking Data Quality Report

## Coverage

| Metric | Value |
|---|---:|
| Total frames | {report.total_frames} |
| Ball coverage | {report.ball_coverage_pct:.2f}% |
| Missing ball frames | {report.missing_ball_frames} |
| Tracked player observations | {report.tracked_player_observations} |
| Missing player positions | {report.missing_player_positions} |

## Temporal integrity

| Metric | Value |
|---|---:|
| Missing frame IDs | {report.missing_frame_ids} |
| Frame gaps | {report.frame_gaps} |
| Duplicate frames | {report.duplicate_frames} |
| Duplicate player observations | {report.duplicate_player_observations} |
| Orphan player observations | {report.orphan_player_observations} |

## Spatial diagnostics

| Metric | Value |
|---|---:|
| Ball out of bounds | {report.ball_out_of_bounds} |
| Players out of bounds | {report.players_out_of_bounds} |
| Suspicious player speeds | {report.suspicious_player_speeds} |

## Lineage

- Schema version: {manifest["schema_version"]}
- Source: {manifest["source_description"]}
- Git commit: {manifest["git_commit"] or "not recorded"}
- Manifest created (UTC): {manifest["created_at_utc"]}

### Input fingerprints

| File | SHA-256 |
|---|---|
| frames.parquet | {manifest["files"]["frames.parquet"]["sha256"]} |
| players.parquet | {manifest["files"]["players.parquet"]["sha256"]} |

Quality findings are diagnostic and do not modify source data.
"""

    markdown_path.write_text(markdown, encoding="utf-8")

    return json_path, markdown_path
