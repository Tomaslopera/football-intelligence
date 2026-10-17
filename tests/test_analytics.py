from football_intelligence.tracking.analytics import (
    tracking_summary,
)
from football_intelligence.tracking.ingestion import (
    iter_tracking_frames,
)
from football_intelligence.tracking.models import (
    RecordingSource,
    TeamSide,
)
from football_intelligence.tracking.storage import (
    write_tracking_parquet,
)
from football_intelligence.tracking.synthetic import (
    generate_tracking_table,
)


def test_tracking_summary(tmp_path):
    table = generate_tracking_table(
        n_frames=10,
        missing_ball_every=5,
    )

    frames = list(
        iter_tracking_frames(
            table,
            match_id="DEMO",
            source=RecordingSource.SYNTHETIC,
            slot_teams={
                1: TeamSide.HOME,
                2: TeamSide.AWAY,
            },
        )
    )

    write_tracking_parquet(frames, tmp_path)

    summary = tracking_summary(tmp_path)

    assert summary["total_frames"] == 10
    assert summary["ball_visible_frames"] == 8
    assert summary["missing_ball_frames"] == 2
    assert summary["tracked_player_observations"] == 20
