"""Causal motion and temporal features from canonical tracking frames.

Only current and preceding frames are used. Missing or skipped
frames do not produce invented ball movement.
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from statistics import mean

from football_intelligence.features.geometry import (
    GeometricFeatures,
    extract_geometric_features,
    pitch_distance_m,
)
from football_intelligence.tracking.models import (
    MatchMetadata,
    PlayerObservation,
    RecordingSource,
    TrackingFrame,
)


@dataclass(frozen=True)
class TemporalFeatures:
    """Geometric and causal temporal information for one frame."""

    geometric: GeometricFeatures
    ball_displacement_m: float | None
    ball_speed_estimate_mps: float | None
    home_mean_speed_mps: float | None
    away_mean_speed_mps: float | None
    ball_missing_streak_frames: int
    distance_advantage_change_m: float | None


def _mean_player_speed(
    players: list[PlayerObservation],
) -> float | None:
    """Average reported speeds of visible players with known speeds."""
    speeds = [
        player.speed_mps
        for player in players
        if player.position is not None and player.speed_mps is not None
    ]

    return mean(speeds) if speeds else None


def extract_temporal_features(
    frames: Iterable[TrackingFrame],
    metadata: MatchMetadata,
) -> Iterator[TemporalFeatures]:
    """Produce causal features in chronological order.

    Frame gaps reset consecutive-frame calculations.
    All frames must belong to the same match and recording source.
    """
    previous: TrackingFrame | None = None
    previous_geometric: GeometricFeatures | None = None
    source: RecordingSource | None = None
    missing_streak = 0

    for current in frames:
        geometric = extract_geometric_features(current, metadata)

        if source is None:
            source = current.source
        elif current.source != source:
            raise ValueError("Tracking sequence must use one recording source")

        if previous is not None and current.frame <= previous.frame:
            raise ValueError("Tracking frames must be strictly increasing")

        consecutive = previous is not None and current.frame == previous.frame + 1

        if not consecutive:
            missing_streak = 0

        ball_displacement: float | None = None
        ball_speed: float | None = None
        advantage_change: float | None = None

        current_ball = current.ball.position

        if current_ball is None:
            missing_streak += 1
        else:
            missing_streak = 0

        if consecutive and previous is not None:
            previous_ball = previous.ball.position

            if current_ball is not None and previous_ball is not None:
                ball_displacement = pitch_distance_m(
                    previous_ball,
                    current_ball,
                    metadata,
                )

                ball_speed = ball_displacement * metadata.fps

            if previous_geometric is not None:
                current_advantage = geometric.distance_advantage_m
                previous_advantage = previous_geometric.distance_advantage_m

                if current_advantage is not None and previous_advantage is not None:
                    advantage_change = current_advantage - previous_advantage

        home_players = [
            player for player in current.players if player.team.value == "H"
        ]
        away_players = [
            player for player in current.players if player.team.value == "A"
        ]

        yield TemporalFeatures(
            geometric=geometric,
            ball_displacement_m=ball_displacement,
            ball_speed_estimate_mps=ball_speed,
            home_mean_speed_mps=_mean_player_speed(home_players),
            away_mean_speed_mps=_mean_player_speed(away_players),
            ball_missing_streak_frames=missing_streak,
            distance_advantage_change_m=advantage_change,
        )

        previous = current
        previous_geometric = geometric
