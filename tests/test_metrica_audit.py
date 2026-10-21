"""Full local orchestration tested exclusively with synthetic EPTS."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from epts_fixture import write_epts_pair

from football_intelligence.tracking.audit import audit_metrica, scan_frame_ids
from football_intelligence.tracking.models import RecordingSource


@pytest.mark.parametrize(
    "source", [RecordingSource.TACTICAL, RecordingSource.BROADCAST]
)
@pytest.mark.parametrize("limit", [2, None])
def test_epts_to_features_and_quality(tmp_path, source, limit):
    xml, txt = write_epts_pair(tmp_path)
    before = (xml.read_bytes(), txt.read_bytes())
    output = tmp_path / "processed"
    result = audit_metrica(
        xml,
        txt,
        output,
        match_id="SYNTHETIC",
        source=source,
        limit=limit,
        expected_frames=3,
    )
    assert result["processed_frames"] == (limit or 3)
    assert result["canonical_frame_range"] == [0, (limit or 3) - 1]
    assert result["quality"]["missing_ball_frames"] == 1
    assert result["quality"]["missing_player_positions"] == 1
    assert result["feature_summary"]["ball_displacement_m"]["present"] == 0
    assert result["feature_summary"]["nearest_home_distance_m"]["missing"] == 1
    assert result["feature_summary"]["nearest_home_distance_m"]["min"] == pytest.approx(
        10.5
    )
    assert result["feature_summary"]["distance_advantage_m"]["max"] == pytest.approx(
        21.0
    )
    assert result["feature_summary"]["distance_advantage_m"]["min"] == pytest.approx(
        21.0 if limit == 2 else 18.9
    )
    assert (output / "quality" / "quality.json").is_file()
    assert json.loads((output / "audit.json").read_text())["status"] == "passed"
    assert (xml.read_bytes(), txt.read_bytes()) == before
    with pytest.raises(FileExistsError):
        audit_metrica(xml, txt, output, match_id="SYNTHETIC", source=source)


@pytest.mark.parametrize(("unit", "speeds"), [("kph", (36, 72)), ("m/s", (10, 20))])
def test_speed_units_through_storage_features_and_quality(tmp_path, unit, speeds):
    xml, txt = write_epts_pair(tmp_path, speed_unit=unit, speeds=speeds)
    result = audit_metrica(
        xml,
        txt,
        tmp_path / "output",
        match_id="SYNTHETIC",
        source=RecordingSource.TACTICAL,
        limit=None,
    )
    assert result["lineage"]["speed_units"] == {"source": unit, "canonical": "m/s"}
    assert result["feature_summary"]["nearest_home_speed_mps"]["min"] == 20
    assert result["feature_summary"]["nearest_away_speed_mps"]["min"] == 10
    assert result["feature_summary"]["home_mean_speed_mps"]["max"] == 20
    assert result["feature_summary"]["away_mean_speed_mps"]["max"] == 10
    assert result["quality_config"]["max_player_speed_mps"] == 15
    assert result["quality"]["suspicious_player_speeds"] == 3


@pytest.mark.parametrize("ids", [(1, 3), (1, 1), (2, 3), (1, 3, 3)])
def test_raw_continuity_checks_every_prefix(tmp_path, ids):
    path = tmp_path / "synthetic.txt"
    path.write_text("".join(f"{frame}:synthetic\n" for frame in ids))
    with pytest.raises(ValueError, match="Nonsequential"):
        scan_frame_ids(path)


def test_truncated_kloppy_load_is_rejected(tmp_path):
    xml, txt = write_epts_pair(tmp_path)
    xml.write_text(xml.read_text().replace('endFrame="3"', 'endFrame="2"'))
    with pytest.raises(ValueError, match="fewer frames"):
        audit_metrica(
            xml,
            txt,
            tmp_path / "output",
            match_id="SYNTHETIC",
            source=RecordingSource.TACTICAL,
            limit=None,
        )
    assert (tmp_path / "output" / "failure.txt").is_file()


def test_inspection_does_not_print_tracking_rows(tmp_path):
    xml, txt = write_epts_pair(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_metrica.py",
            "--metadata",
            str(xml),
            "--tracking",
            str(txt),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Rows: 3" in result.stdout
    assert "0.21" not in result.stdout
    assert "Tracking sample" not in result.stdout


def test_cli_rejects_output_outside_processed(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_metrica.py",
            "--metadata",
            "missing.xml",
            "--tracking",
            "missing.txt",
            "--source",
            "tactical",
            "--output",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "beneath datasets/processed" in result.stderr


def test_dataset_directories_are_gitignored():
    for directory in ("raw", "processed", "generated"):
        result = subprocess.run(
            ["git", "check-ignore", str(Path("datasets") / directory / "probe")],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
