import pandas as pd
import pytest

from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
)
from football_intelligence.tracking.metrica import (
    load_metrica_epts,
    normalize_metrica_columns,
)
from football_intelligence.tracking.models import (
    RecordingSource,
    TeamSide,
)


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
