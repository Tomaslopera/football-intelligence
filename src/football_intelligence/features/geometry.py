"""Frame-level geometric features for football possession inference."""

import math
from dataclasses import dataclass

from football_intelligence.tracking.models import (
    MatchMetadata,
    PitchPosition,
    PlayerObservation,
    TeamSide,
    TrackingFrame,
)


@dataclass(frozen=True)
class GeometricFeatures:
    """Model-independent spatial features for one tracking frame."""

    match_id: str
    frame: int
    ball_visible: bool
    home_players_visible: int
    away_players_visible: int
    nearest_home_distance_m: float | None
    nearest_away_distance_m: float | None
    nearest_home_speed_mps: float | None
    nearest_away_speed_mps: float | None
    distance_advantage_m: float | None


def pitch_distance_m(
    first: PitchPosition,
    second: PitchPosition,
    metadata: MatchMetadata,
) -> float:
    """Calculate Euclidean distance on a rectangular pitch in metres."""
    dx = (first.x - second.x) * metadata.pitch_length_m
    dy = (first.y - second.y) * metadata.pitch_width_m

    return math.hypot(dx, dy)


def _nearest_player(
    players: list[PlayerObservation],
    ball: PitchPosition,
    metadata: MatchMetadata,
) -> tuple[float | None, float | None]:
    """Return distance and speed of the nearest visible player."""
    nearest_distance: float | None = None
    nearest_speed: float | None = None

    for player in players:
        if player.position is None:
            continue

        distance = pitch_distance_m(
            player.position,
            ball,
            metadata,
        )

        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_speed = player.speed_mps

    return nearest_distance, nearest_speed


def extract_geometric_features(
    tracking_frame: TrackingFrame,
    metadata: MatchMetadata,
) -> GeometricFeatures:
    """Build spatial features from one canonical tracking frame.

    This function does not predict possession.
    """
    if tracking_frame.match_id != metadata.match_id:
        raise ValueError("Tracking frame and match metadata do not match")

    if tracking_frame.frame >= metadata.total_frames:
        raise ValueError("Tracking frame exceeds match frame bounds")

    home_players = [
        player
        for player in tracking_frame.players
        if player.team == TeamSide.HOME and player.position is not None
    ]

    away_players = [
        player
        for player in tracking_frame.players
        if player.team == TeamSide.AWAY and player.position is not None
    ]

    ball_position = tracking_frame.ball.position

    home_distance: float | None = None
    away_distance: float | None = None
    home_speed: float | None = None
    away_speed: float | None = None
    advantage: float | None = None

    if ball_position is not None:
        home_distance, home_speed = _nearest_player(
            home_players,
            ball_position,
            metadata,
        )

        away_distance, away_speed = _nearest_player(
            away_players,
            ball_position,
            metadata,
        )

        if home_distance is not None and away_distance is not None:
            # Positive: home player is closer.
            # Negative: away player is closer.
            advantage = away_distance - home_distance

    return GeometricFeatures(
        match_id=tracking_frame.match_id,
        frame=tracking_frame.frame,
        ball_visible=ball_position is not None,
        home_players_visible=len(home_players),
        away_players_visible=len(away_players),
        nearest_home_distance_m=home_distance,
        nearest_away_distance_m=away_distance,
        nearest_home_speed_mps=home_speed,
        nearest_away_speed_mps=away_speed,
        distance_advantage_m=advantage,
    )
