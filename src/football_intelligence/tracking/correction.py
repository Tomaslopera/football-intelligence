"""Rebuild private derived data after an evidenced source-unit correction.

Never reads or changes raw assets. The previous canonical audit must match
its fingerprints. New artifacts retain the upstream source identity.
"""

import json
import resource
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pyarrow.compute as pc
import pyarrow.parquet as pq

from football_intelligence.features.pipeline import build_feature_dataset
from football_intelligence.tracking.audit import _feature_summary
from football_intelligence.tracking.lineage import (
    create_lineage_manifest,
    file_sha256,
    write_quality_reports,
)
from football_intelligence.tracking.models import MatchMetadata, RecordingSource
from football_intelligence.tracking.quality import (
    QualityConfig,
    analyze_tracking_quality,
)
from football_intelligence.tracking.review import review_processed_audit
from football_intelligence.tracking.storage import PLAYER_SCHEMA, read_tracking_parquet


def rebuild_speed_units(
    previous: Path, output: Path, *, effective_unit: str, evidence: str
) -> dict[str, Any]:
    """Reverse the old declared-unit scale and regenerate features from tracking."""
    started = time.perf_counter()
    prior = json.loads((previous / "audit.json").read_text())
    units = prior["lineage"]["speed_units"]
    prior_effective = units.get("effective_source", units["source"])
    divisors = {"m/s": 1.0, "kph": 3.6}
    if prior["status"] != "passed" or prior["scope"] != "full":
        raise ValueError("Correction requires a completed full canonical audit")
    if (
        prior_effective not in divisors
        or effective_unit not in divisors
        or not evidence.strip()
    ):
        raise ValueError("Supported speed units and explicit evidence are required")
    if prior_effective == effective_unit:
        raise ValueError("The requested unit is already effective")
    for name in ("frames.parquet", "players.parquet"):
        if (
            file_sha256(previous / "tracking" / name)
            != prior["lineage"]["files"][name]["sha256"]
        ):
            raise ValueError("Upstream tracking fingerprint mismatch")
    if (
        file_sha256(previous / "features/features-v1.0.parquet")
        != prior["feature_sha256"]
    ):
        raise ValueError("Upstream feature fingerprint mismatch")
    output.mkdir(parents=True, exist_ok=False)
    tracking = output / "tracking"
    tracking.mkdir()
    shutil.copyfile(previous / "tracking/frames.parquet", tracking / "frames.parquet")
    factor = divisors[prior_effective] / divisors[effective_unit]
    player_file = pq.ParquetFile(previous / "tracking/players.parquet")
    if not player_file.schema_arrow.equals(PLAYER_SCHEMA, check_metadata=True):
        raise ValueError("Upstream player schema mismatch")
    with pq.ParquetWriter(
        tracking / "players.parquet", PLAYER_SCHEMA, compression="zstd"
    ) as writer:
        index = PLAYER_SCHEMA.get_field_index("speed_mps")
        for batch in player_file.iter_batches(batch_size=65536):
            corrected = batch.set_column(
                index,
                PLAYER_SCHEMA.field(index),
                pc.multiply(batch.column(index), factor),
            )
            if not corrected.remove_column(index).equals(batch.remove_column(index)):
                raise ValueError("Correction changed unrelated player fields")
            writer.write_batch(corrected)
    if (
        file_sha256(tracking / "frames.parquet")
        != prior["lineage"]["files"]["frames.parquet"]["sha256"]
    ):
        raise ValueError("Correction changed frame observations")
    frames = read_tracking_parquet(tracking)
    metadata = MatchMetadata.model_validate(prior["metadata"])
    feature_path = output / "features/features-v1.0.parquet"
    build_feature_dataset(
        frames, metadata, RecordingSource(prior["source"]), feature_path
    )
    del frames
    config = QualityConfig(**prior["quality_config"])
    quality = analyze_tracking_quality(tracking, config)
    manifest = create_lineage_manifest(
        tracking,
        source_description="Evidence-based source speed-unit correction",
        config=config,
        git_commit=None,
    )
    for name in ("source_files", "metadata", "slot_teams", "sample_limit"):
        if name in prior["lineage"]:
            manifest[name] = prior["lineage"][name]
    manifest["speed_units"] = {
        "source": units["source"],
        "effective_source": effective_unit,
        "canonical": "m/s",
        "override_evidence": evidence,
    }
    manifest["upstream_audit_sha256"] = file_sha256(previous / "audit.json")
    manifest["upstream_tracking_files"] = prior["lineage"]["files"]
    manifest["correction_factor"] = factor
    write_quality_reports(quality, manifest, output / "quality")
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {
        **prior,
        "execution_mode": "rebuild_from_validated_canonical",
        "status": "pending_review",
        "lineage": manifest,
        "quality": {
            **quality.to_dict(),
            "ball_coverage_pct": quality.ball_coverage_pct,
        },
        "feature_summary": _feature_summary(feature_path),
        "feature_sha256": file_sha256(feature_path),
        "elapsed_seconds": time.perf_counter() - started,
        "timings": {"rebuild_seconds": time.perf_counter() - started},
        "peak_process_rss_mib": peak / (1024**2 if sys.platform == "darwin" else 1024),
        "upstream_ingestion_elapsed_seconds": prior["elapsed_seconds"],
    }
    report = output / "audit.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    review = review_processed_audit(output)
    if (
        not review["feature_consistency_passed"]
        or not review["parquet_schemas_match"]
        or not all(review["input_fingerprints_match_audit"].values())
    ):
        raise ValueError("Corrected output failed independent feature review")
    (output / "quality-review.json").write_text(json.dumps(review, indent=2) + "\n")
    result["status"] = "passed"
    result["elapsed_seconds"] = time.perf_counter() - started
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result
