from xml.etree import ElementTree as ET

import pandas as pd
import pytest
from epts_fixture import write_epts_pair
from kloppy import metrica

from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
)
from football_intelligence.tracking.metrica import (
    load_metrica_epts,
    normalize_metrica_columns,
    read_metrica_metadata,
)
from football_intelligence.tracking.models import (
    RecordingSource,
    TeamSide,
)


@pytest.mark.parametrize("unit", ["kph", "m/s"])
def test_kloppy_preserves_epts_speed_values(tmp_path, unit):
    """Dependency behavior guard: fail if Kloppy starts converting units."""
    xml, txt = write_epts_pair(tmp_path, speed_unit=unit, speeds=(36, 72))
    dataset = metrica.load_tracking_epts(
        meta_data=str(xml), raw_data=str(txt), coordinates="metrica"
    )
    table = dataset.to_df()
    assert table["Track_1_s"].tolist() == [36, 36, 36]
    assert table["Track_7_s"].tolist() == [72, 72, 72]


@pytest.mark.parametrize(("unit", "speeds"), [("kph", (36, 72)), ("m/s", (10, 20))])
def test_loader_normalizes_speed_once_and_preserves_missingness(tmp_path, unit, speeds):
    xml, txt = write_epts_pair(tmp_path, speed_unit=unit, speeds=speeds)
    # Missing and zero are different observations, including after conversion.
    txt.write_text(
        txt.read_text()
        .replace(f"2:0.21,0.4,{speeds[0]}", "2:0.21,0.4,")
        .replace(f"3:0.22,0.4,{speeds[0]}", "3:0.22,0.4,0")
    )
    original = (xml.read_bytes(), txt.read_bytes())
    metadata = read_metrica_metadata(xml, match_id="SYNTHETIC", total_frames=3)
    assert metadata.source_speed_unit == unit
    for limit in (None, 2):
        table = load_metrica_epts(xml, txt, limit=limit)
        frames = list(
            iter_tracking_frames(
                table,
                match_id="SYNTHETIC",
                source=RecordingSource.TACTICAL,
                slot_teams=metadata.slot_teams,
            )
        )
        assert frames[0].players[0].speed_mps == pytest.approx(10)
        assert frames[0].players[1].speed_mps == pytest.approx(20)
        assert frames[1].players[0].speed_mps is None
        if limit is None:
            assert frames[2].players[0].speed_mps == 0
    assert (xml.read_bytes(), txt.read_bytes()) == original


@pytest.mark.parametrize("unit", ["km/h", "mph", "", "missing", "ambiguous"])
def test_metadata_and_loader_reject_unknown_or_ambiguous_speed_units(tmp_path, unit):
    xml, txt = write_epts_pair(tmp_path, speed_unit=unit)
    tree = ET.parse(xml)
    channel = tree.getroot().find(
        "Metadata/Devices/Device/Sensors/Sensor[@id='speed']/Channels/Channel"
    )
    assert channel is not None
    if unit == "missing":
        channel.remove(channel.find("Unit"))
    elif unit == "ambiguous":
        channel.find("Unit").text = "kph"
        channels = tree.getroot().find(
            "Metadata/Devices/Device/Sensors/Sensor[@id='speed']/Channels"
        )
        duplicate = ET.SubElement(channels, "Channel", id="s")
        ET.SubElement(duplicate, "Unit").text = "m/s"
    tree.write(xml)
    with pytest.raises(ValueError, match="speed units"):
        read_metrica_metadata(xml, match_id="SYNTHETIC", total_frames=3)
    with pytest.raises(ValueError, match="speed units"):
        load_metrica_epts(xml, txt)


def test_normalizes_metrica_track_columns():
    table = pd.DataFrame(
        {
            "frame_id": [1, 2],
            "ball_x": [0.5, None],
            "ball_y": [0.6, None],
            "Track_1_x": [0.3, 0.31],
            "Track_1_y": [0.4, 0.41],
            "Track_1_s": [2.0, 2.1],
        }
    )

    normalized = normalize_metrica_columns(table)

    assert "1_x" in normalized.columns
    assert "1_y" in normalized.columns
    assert "1_s" in normalized.columns
    assert "Track_1_x" not in normalized.columns


def test_metrica_adapter_integrates_with_ingestion():
    table = pd.DataFrame(
        {
            "frame_id": [1, 2],
            "ball_x": [0.5, None],
            "ball_y": [0.6, None],
            "Track_1_x": [0.3, 0.31],
            "Track_1_y": [0.4, 0.41],
            "Track_1_s": [2.0, 2.1],
        }
    )

    normalized = normalize_metrica_columns(table)

    frames = list(
        iter_tracking_frames(
            normalized,
            match_id="EPTS-TEST",
            source=RecordingSource.TACTICAL,
            slot_teams={1: TeamSide.HOME},
        )
    )

    assert len(frames) == 2
    assert frames[0].frame == 0
    assert frames[1].frame == 1
    assert frames[0].players[0].team == TeamSide.HOME
    assert frames[1].ball.position is None


def test_duplicate_normalized_columns_rejected():
    table = pd.DataFrame(
        {
            "frame_id": [1],
            "1_x": [0.3],
            "Track_1_x": [0.4],
        }
    )

    with pytest.raises(ValueError, match="duplicates"):
        normalize_metrica_columns(table)


def test_missing_epts_files_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_metrica_epts(
            tmp_path / "missing.xml",
            tmp_path / "missing.txt",
        )


def test_real_kloppy_parser_with_synthetic_epts(tmp_path):
    xml, txt = write_epts_pair(tmp_path)
    metadata = read_metrica_metadata(xml, match_id="SYNTHETIC", total_frames=3)
    assert metadata.slot_teams == {1: TeamSide.AWAY, 7: TeamSide.HOME}
    assert metadata.match.fps == 25
    assert metadata.match.pitch_length_m == 105
    table = load_metrica_epts(xml, txt)
    frames = list(
        iter_tracking_frames(
            table,
            match_id="SYNTHETIC",
            source=RecordingSource.TACTICAL,
            slot_teams=metadata.slot_teams,
        )
    )
    assert [frame.frame for frame in frames] == [0, 1, 2]
    assert frames[0].players[0].team == TeamSide.AWAY
    assert frames[0].players[0].speed_mps == 2
    assert frames[1].ball.position is None
    assert frames[1].players[1].position is None
    assert len(load_metrica_epts(xml, txt, limit=2)) == 2


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        ('idLocalTeam="home"', 'idLocalTeam="away"', "team IDs"),
        ("<Score ", "<NoScore ", "home/away"),
        ('teamId="away"', 'teamId="unknown"', "unknown source team"),
        ("<Unit>normalized</Unit>", "<Unit>m</Unit>", "normalized units"),
        ("<Unit>m/s</Unit>", "<Unit>km/h</Unit>", "speed units"),
    ],
)
def test_ambiguous_metadata_rejected(tmp_path, before, after, message):
    xml, _ = write_epts_pair(tmp_path)
    text = (
        xml.read_text()
        .replace(before, after)
        .replace("</Score>", "</NoScore>" if "NoScore" in after else "</Score>")
    )
    xml.write_text(text)
    with pytest.raises(ValueError, match=message):
        read_metrica_metadata(xml, match_id="SYNTHETIC", total_frames=3)
