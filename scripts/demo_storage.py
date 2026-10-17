from pathlib import Path

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


def main() -> None:
    table = generate_tracking_table(n_frames=100)

    frames = list(
        iter_tracking_frames(
            table,
            match_id="DEMO-001",
            source=RecordingSource.SYNTHETIC,
            slot_teams={
                1: TeamSide.HOME,
                2: TeamSide.AWAY,
            },
        )
    )

    output = Path("datasets/generated/demo")

    write_tracking_parquet(frames, output)

    summary = tracking_summary(output)

    for name, value in summary.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()
