import math

import pytest

from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
    normalize_record,
    optional_position,
)
from football_intelligence.tracking.models import (
    RecordingSource,
    TeamSide,
)
from football_intelligence.tracking.synthetic import generate_tracking_table

SLOT_TEAMS = {
    1: TeamSide.HOME,
    2: TeamSide.AWAY,
}


def test_synthetic_ingestion_end_to_end():
    table = generate_tracking_table(n_frames=10)

    frames = list(
        iter_tracking_frames(
            table,
            match_id="SYNTHETIC-001",
            source=RecordingSource.SYNTHETIC,
            slot_teams=SLOT_TEAMS,
        )
    )

    assert len(frames) == 10
    assert frames[0].frame == 0
    assert frames[-1].frame == 9
    assert frames[0].ball_visible is False
    assert frames[1].ball_visible is True
    assert frames[1].tracked_player_count == 2


def test_missing_ball_normalization():
    position = optional_position(math.nan, math.nan)
    assert position is None


def test_incomplete_position_rejected():
    with pytest.raises(ValueError):
        optional_position(0.5, math.nan)


def test_missing_team_mapping_rejected():
    table = generate_tracking_table(n_frames=2)

    with pytest.raises(ValueError, match="Missing team"):
        list(
            iter_tracking_frames(
                table,
                match_id="SYNTHETIC-001",
                source=RecordingSource.SYNTHETIC,
                slot_teams={1: TeamSide.HOME},
            )
        )


def test_frame_gap_rejected():
    table = generate_tracking_table(n_frames=4)
    table.loc[2, "frame_id"] = 8

    with pytest.raises(ValueError, match="sequential"):
        list(
            iter_tracking_frames(
                table,
                match_id="SYNTHETIC-001",
                source=RecordingSource.SYNTHETIC,
                slot_teams=SLOT_TEAMS,
            )
        )


def test_normalize_single_record():
    row = {
        "frame_id": 11186,
        "ball_x": 0.5,
        "ball_y": 0.6,
        "1_x": 0.4,
        "1_y": 0.3,
        "1_s": 2.5,
    }

    frame = normalize_record(
        row,
        match_id="BAR-ATH",
        source=RecordingSource.TACTICAL,
        slot_teams={1: TeamSide.HOME},
    )

    assert frame.frame == 11185
    assert frame.ball_visible
    assert len(frame.players) == 1
