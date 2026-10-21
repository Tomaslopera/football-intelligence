"""Independent feature review using synthetic observations only."""

import json
import subprocess
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from epts_fixture import write_epts_pair

from football_intelligence.tracking.audit import audit_metrica
from football_intelligence.tracking.models import RecordingSource
from football_intelligence.tracking.review import review_processed_audit


def test_independent_recomputation_and_corruption_detection(tmp_path):
    xml, txt = write_epts_pair(tmp_path)
    txt.write_text(
        "1:0.2,0.4,2;0.6,0.4,3:0.5,0.4\n"
        "2:1.2,0.4,2;0.6,0.4,3:1.1,0.4\n"
        "3:0.2,0.4,2;0.6,0.4,3:,\n"
    )
    output = tmp_path / "audit"
    audit_metrica(
        xml,
        txt,
        output,
        match_id="SYNTHETIC",
        source=RecordingSource.TACTICAL,
        limit=None,
    )
    result = review_processed_audit(output)
    assert result["feature_consistency_passed"]
    assert not any(result["feature_mismatch_counts"].values())
    assert result["ball_speed_anomalies"]["above_50_mps"] == 1
    assert result["ball_speed_anomalies"]["invalid_motion_context"] == 0
    assert result["bounds"]["out_of_bounds_ball_retained_in_features"] == 1
    assert result["bounds"]["player_out_of_bounds"] == 1
    assert all(result["input_fingerprints_match_audit"].values())
    assert result["parquet_schemas_match"]
    assert result["longest_missing_intervals"][0]["start_frame"] == 2
    assert result["longest_missing_intervals"][0]["end_frame_exclusive"] == 3
    path = output / "features/features-v1.0.parquet"
    table = pq.read_table(path)
    records = table.to_pylist()
    records[1]["ball_speed_estimate_mps"] = None
    pq.write_table(type(table).from_pylist(records, schema=table.schema), path)
    result = review_processed_audit(output)
    assert not result["feature_consistency_passed"]
    assert result["feature_mismatch_counts"]["ball_speed_estimate_mps"] == 1
    assert not result["input_fingerprints_match_audit"]["features"]


def test_missing_intervals_and_motion_context(tmp_path):
    xml, txt = write_epts_pair(tmp_path)
    output = tmp_path / "audit"
    audit_metrica(
        xml,
        txt,
        output,
        match_id="SYNTHETIC",
        source=RecordingSource.TACTICAL,
        limit=None,
    )
    result = review_processed_audit(output)
    assert result["feature_consistency_passed"]
    assert result["ball_speed_anomalies"]["above_50_mps"] == 0
    assert result["longest_missing_intervals"][0]["frames"] == 1
    assert result["longest_missing_intervals"][0]["seconds"] == pytest.approx(0.04)
    json.dumps(result, allow_nan=False)


def test_user_run_source_check_with_synthetic_epts(tmp_path):
    xml, txt = write_epts_pair(tmp_path, speed_unit="kph", speeds=(36, 72))
    output = tmp_path / "audit"
    audit_metrica(
        xml,
        txt,
        output,
        match_id="SYNTHETIC",
        source=RecordingSource.TACTICAL,
        limit=None,
    )
    reports = tmp_path / "datasets/processed"
    reports.mkdir(parents=True)
    script = (
        Path(__file__).resolve().parents[1] / "scripts/check_metrica_speed_sample.py"
    )
    process = subprocess.run(
        [
            sys.executable,
            str(script),
            "--metadata",
            str(xml),
            "--tracking",
            str(txt),
            "--audit-directory",
            str(output),
            "--limit",
            "3",
            "--output",
            str(reports / "check.json"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(process.stdout)
    assert result["adapter_conversion_mismatches"] == 0
    assert result["missingness_mismatches"] == 0
    assert result["comparable_speeds"] == 6
    assert result["stored_sample_comparison"] == [0, 6, 0.0]
