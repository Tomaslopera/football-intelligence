"""Local EPTS integration audit using the existing batch components.

Outputs are private research artifacts. This module makes no network calls.
It intentionally retains the current in-memory implementation for profiling.
"""

import json
import resource
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pyarrow.parquet as pq

from football_intelligence.features.pipeline import build_feature_dataset
from football_intelligence.features.storage import FEATURE_SCHEMA, read_feature_parquet
from football_intelligence.tracking.ingestion import (
    find_track_slots,
    iter_tracking_frames,
)
from football_intelligence.tracking.lineage import (
    create_lineage_manifest,
    file_sha256,
    write_quality_reports,
)
from football_intelligence.tracking.metrica import (
    BAR_ATH_TACTICAL_SPEED_EVIDENCE,
    load_metrica_epts,
    read_metrica_metadata,
)
from football_intelligence.tracking.models import RecordingSource
from football_intelligence.tracking.quality import (
    QualityConfig,
    analyze_tracking_quality,
)
from football_intelligence.tracking.storage import (
    FRAME_SCHEMA,
    PLAYER_SCHEMA,
    read_tracking_parquet,
    write_tracking_parquet,
)


def scan_frame_ids(path: Path) -> int:
    """Check every ATD line's frame prefix without retaining observations.

    A full scan also detects trailing rows Kloppy might stop before reading
    when the XML DataFormatSpecification ends prematurely.
    """
    count = 0
    with path.open("rb") as stream:
        for count, line in enumerate(stream, start=1):
            prefix, separator, _ = line.partition(b":")
            try:
                frame = int(prefix)
            except ValueError:
                raise ValueError(f"Invalid ATD frame prefix at line {count}") from None
            if not separator or frame != count:
                raise ValueError(f"Nonsequential ATD frame ID at line {count}")
    if not count:
        raise ValueError("ATD file is empty")
    return count


def _feature_summary(path: Path) -> dict[str, Any]:
    """Aggregate completeness and distributions, without returning frame rows."""
    result: dict[str, Any] = {}
    with duckdb.connect(":memory:") as connection:
        connection.read_parquet(str(path)).create_view("features")
        for field in FEATURE_SCHEMA:
            # Column names come exclusively from our versioned schema.
            name = field.name
            row = connection.execute(
                f'SELECT COUNT(*), COUNT("{name}") FROM features'
            ).fetchone()
            if row is None:
                raise RuntimeError("Missing feature summary")
            result[name] = {"present": int(row[1]), "missing": int(row[0] - row[1])}
            if name.endswith(("_m", "_mps")):
                stats = connection.execute(
                    f'SELECT MIN("{name}"), MEDIAN("{name}"), '
                    f'QUANTILE_CONT("{name}", 0.99), MAX("{name}"), '
                    f'COUNT(*) FILTER (WHERE NOT ISFINITE("{name}")) FROM features'
                ).fetchone()
                if stats is None:
                    raise RuntimeError("Missing feature distribution")
                result[name].update(
                    zip(
                        ("min", "median", "p99", "max", "nonfinite"), stats, strict=True
                    )
                )
        row = connection.execute(
            """SELECT
                COUNT(*) FILTER (WHERE ball_speed_estimate_mps > 50),
                MAX(ball_missing_streak_frames)
            FROM features"""
        ).fetchone()
        if row is None:
            raise RuntimeError("Missing motion diagnostics")
        result["diagnostics"] = {
            "ball_speed_above_50_mps": row[0],
            "max_missing_ball_streak_frames": row[1],
            "speed_threshold_is_diagnostic_only": True,
        }
    return result


def audit_metrica(
    metadata_path: Path,
    tracking_path: Path,
    output: Path,
    *,
    match_id: str,
    source: RecordingSource,
    limit: int | None = 100,
    expected_frames: int | None = None,
    git_commit: str | None = None,
    speed_unit_override: str | None = None,
    speed_unit_evidence: str | None = None,
) -> dict[str, Any]:
    """Audit a sample or full recording; refuse to overwrite previous results.

    The caller must establish permission for local processing. No records
    should be sent to a hosted agent. Failures are saved locally because
    third-party exception messages can contain source observations.
    """
    if source not in {RecordingSource.TACTICAL, RecordingSource.BROADCAST}:
        raise ValueError("An EPTS audit requires a real recording source")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    # The caller selects this source contract by explicit match/source identity.
    # Generic EPTS loading continues to honor declared units. BAR-ATH tactical
    # instead follows the competition's documented m/s contract despite XML kph.
    if (
        match_id == "BAR-ATH"
        and source == RecordingSource.TACTICAL
        and speed_unit_override is None
        and speed_unit_evidence is None
    ):
        speed_unit_override = "m/s"
        speed_unit_evidence = BAR_ATH_TACTICAL_SPEED_EVIDENCE
    output.mkdir(parents=True, exist_ok=False)
    try:
        return _audit_metrica(
            metadata_path,
            tracking_path,
            output,
            match_id=match_id,
            source=source,
            limit=limit,
            expected_frames=expected_frames,
            git_commit=git_commit,
            speed_unit_override=speed_unit_override,
            speed_unit_evidence=speed_unit_evidence,
        )
    except Exception:
        (output / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise


def _audit_metrica(
    metadata_path: Path,
    tracking_path: Path,
    output: Path,
    *,
    match_id: str,
    source: RecordingSource,
    limit: int | None,
    expected_frames: int | None,
    git_commit: str | None,
    speed_unit_override: str | None,
    speed_unit_evidence: str | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    stages: dict[str, float] = {}
    source_count = scan_frame_ids(tracking_path)
    if expected_frames is not None and source_count != expected_frames:
        raise ValueError("Source frame count disagrees with expected frame count")
    metadata = read_metrica_metadata(
        metadata_path,
        match_id=match_id,
        total_frames=source_count,
        speed_unit_override=speed_unit_override,
        speed_unit_evidence=speed_unit_evidence,
    )
    table = load_metrica_epts(
        metadata_path,
        tracking_path,
        limit=limit,
        speed_unit_override=speed_unit_override,
        speed_unit_evidence=speed_unit_evidence,
    )
    expected_loaded = source_count if limit is None else min(limit, source_count)
    if len(table) != expected_loaded:
        raise ValueError("Kloppy returned fewer frames than the source scan")
    slots = find_track_slots(list(table.columns))
    if set(slots) != set(metadata.slot_teams):
        raise ValueError("Parsed columns disagree with source track metadata")
    numeric = table.select_dtypes(include="number")
    nonfinite = int(np.isinf(numeric.to_numpy(dtype=float, na_value=np.nan)).sum())
    if nonfinite:
        raise ValueError("Nonfinite tracking values detected")
    source_ball_count = int((table.ball_x.notna() & table.ball_y.notna()).sum())
    source_player_count = sum(
        int((table[f"{slot}_x"].notna() & table[f"{slot}_y"].notna()).sum())
        for slot in slots
    )
    frames = list(
        iter_tracking_frames(
            table, match_id=match_id, source=source, slot_teams=metadata.slot_teams
        )
    )
    source_missing = {name: int(count) for name, count in table.isna().sum().items()}
    stages["load_and_normalize_seconds"] = time.perf_counter() - started
    del table, numeric
    tracking_dir = output / "tracking"
    stage_start = time.perf_counter()
    paths = write_tracking_parquet(frames, tracking_dir)
    for path, schema in zip(paths, (FRAME_SCHEMA, PLAYER_SCHEMA), strict=True):
        if not pq.read_schema(path).equals(schema, check_metadata=True):
            raise ValueError("Tracking Parquet schema mismatch")
    restored = read_tracking_parquet(tracking_dir)
    if restored != frames:
        raise ValueError("Tracking Parquet round trip changed observations")
    del frames
    stages["tracking_storage_round_trip_seconds"] = time.perf_counter() - stage_start
    config = QualityConfig()
    quality = analyze_tracking_quality(tracking_dir, config)
    if (
        quality.total_frames != expected_loaded
        or quality.total_frames - quality.missing_ball_frames != source_ball_count
        or quality.tracked_player_observations != source_player_count
        or quality.missing_frame_ids
        or quality.duplicate_frames
        or quality.duplicate_player_observations
        or quality.orphan_player_observations
    ):
        raise ValueError("Stored coverage or continuity disagrees with source")
    manifest = create_lineage_manifest(
        tracking_dir,
        source_description="Local EPTS integration audit",
        config=config,
        git_commit=git_commit,
    )
    manifest["source_files"] = {
        path.name: {"sha256": file_sha256(path), "size_bytes": path.stat().st_size}
        for path in (metadata_path, tracking_path)
    }
    manifest["metadata"] = metadata.match.model_dump(mode="json")
    manifest["speed_units"] = {
        "source": metadata.source_speed_unit,
        "canonical": "m/s",
    }
    if speed_unit_override is not None:
        manifest["speed_units"].update(
            {
                "effective_source": metadata.effective_speed_unit,
                "override_evidence": metadata.speed_unit_evidence,
            }
        )
    manifest["slot_teams"] = {
        str(slot): team.value for slot, team in metadata.slot_teams.items()
    }
    manifest["sample_limit"] = limit
    write_quality_reports(quality, manifest, output / "quality")
    feature_path = output / "features" / "features-v1.0.parquet"
    stage_start = time.perf_counter()
    build_feature_dataset(restored, metadata.match, source, feature_path)
    features = read_feature_parquet(feature_path)
    if [row.frame for row in features] != [frame.frame for frame in restored]:
        raise ValueError("Feature frame alignment mismatch")
    feature_summary = _feature_summary(feature_path)
    stages["features_and_verification_seconds"] = time.perf_counter() - stage_start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {
        "status": "passed",
        "scope": "full" if limit is None else "sample",
        "source": source.value,
        "source_frames": source_count,
        "processed_frames": len(restored),
        "canonical_frame_range": [restored[0].frame, restored[-1].frame],
        "source_missing_values": source_missing,
        "quality": {
            **quality.to_dict(),
            "ball_coverage_pct": quality.ball_coverage_pct,
        },
        "feature_summary": feature_summary,
        "metadata": metadata.match.model_dump(mode="json"),
        "slot_teams": manifest["slot_teams"],
        "quality_config": asdict(config),
        "timings": stages,
        "elapsed_seconds": time.perf_counter() - started,
        "peak_process_rss_mib": peak / (1024**2 if sys.platform == "darwin" else 1024),
        "memory_note": "Process lifetime high-water RSS, not a stage allocation measurement",
        "feature_sha256": file_sha256(feature_path),
        "lineage": manifest,
    }
    (output / "audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result
