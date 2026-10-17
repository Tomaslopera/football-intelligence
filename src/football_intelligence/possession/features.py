"""Deterministic P0 possession features from canonical tracking frames.

Canonical positions are normalized to [0, 1] relative to pitch dimensions.
Player slots are not assumed to be persistent identities.
"""

from dataclasses import dataclass
from math import hypot

from football_intelligence.tracking.models import (
    MatchMetadata,
    PitchPosition,
    TeamSide,
    TrackingFrame,
)


@dataclass(frozen=True, slots=True)
class ProximityFeatures:
    match_id: str
    frame: int
    ball_available: bool
    home_observed_count: int
    away_observed_count: int
    home_min_distance_m: float | None
    away_min_distance_m: float | None
    proximity_margin_m: float | None
    ball_speed_mps: float | None


def _distance_m(
    ball: PitchPosition,
    player: PitchPosition,
    metadata: MatchMetadata,
) -> float:
    return hypot(
        (ball.x - player.x) * metadata.pitch_length_m,
        (ball.y - player.y) * metadata.pitch_width_m,
    )


def extract_proximity_features(
    frame: TrackingFrame,
    metadata: MatchMetadata,
) -> ProximityFeatures:
    """Compute nearest-team distance without imputing absent observations."""
    if frame.match_id != metadata.match_id:
        raise ValueError("Frame match_id differs from match metadata")

    home_positions = [
        player.position
        for player in frame.players
        if player.team == TeamSide.HOME and player.position is not None
    ]
    away_positions = [
        player.position
        for player in frame.players
        if player.team == TeamSide.AWAY and player.position is not None
    ]
    ball = frame.ball.position

    home_min = (
        min(_distance_m(ball, p, metadata) for p in home_positions)
        if ball is not None and home_positions
        else None
    )
    away_min = (
        min(_distance_m(ball, p, metadata) for p in away_positions)
        if ball is not None and away_positions
        else None
    )
    margin = away_min - home_min if home_min is not None and away_min is not None else None

    return ProximityFeatures(
        match_id=frame.match_id,
        frame=frame.frame,
        ball_available=ball is not None,
        home_observed_count=len(home_positions),
        away_observed_count=len(away_positions),
        home_min_distance_m=home_min,
        away_min_distance_m=away_min,
        proximity_margin_m=margin,
        ball_speed_mps=frame.ball.speed_mps,
    )
