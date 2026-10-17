"""Canonical tracking contracts, independent of source format."""

from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class TrackingModel(BaseModel):
    """Base configuration for validated tracking contracts."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class TeamSide(StrEnum):
    HOME = "H"
    AWAY = "A"


class RecordingSource(StrEnum):
    TACTICAL = "tactical"
    BROADCAST = "broadcast"
    SYNTHETIC = "synthetic"


class PitchPosition(TrackingModel):
    """Normalized pitch coordinates.

    Coordinates outside [0, 1] are retained for quality analysis.
    Non-finite values are rejected at this canonical layer.
    """

    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)


class Velocity(TrackingModel):
    """Optional velocity components in metres per second."""

    vx: float = Field(allow_inf_nan=False)
    vy: float = Field(allow_inf_nan=False)


class PlayerObservation(TrackingModel):
    """One tracked slot, not a stable player identity."""

    track_slot: int = Field(ge=1)
    team: TeamSide
    position: PitchPosition | None = None

    speed_mps: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )


class BallObservation(TrackingModel):
    """Ball observation, including missing detections."""

    position: PitchPosition | None = None

    speed_mps: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )


class MatchMetadata(TrackingModel):
    match_id: str = Field(min_length=1)
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)

    fps: float = Field(gt=0, allow_inf_nan=False)
    total_frames: int = Field(gt=0)

    pitch_length_m: float = Field(gt=0, allow_inf_nan=False)
    pitch_width_m: float = Field(gt=0, allow_inf_nan=False)


class TrackingFrame(TrackingModel):
    """One canonical video frame with available observations."""

    match_id: str = Field(min_length=1)
    source: RecordingSource
    frame: int = Field(ge=0)

    players: list[PlayerObservation] = Field(
        default_factory=list,
    )
    ball: BallObservation = Field(
        default_factory=BallObservation,
    )

    @model_validator(mode="after")
    def validate_unique_track_slots(self):
        slots = [player.track_slot for player in self.players]

        if len(slots) != len(set(slots)):
            raise ValueError("Duplicate track slots in the same frame")

        return self

    def timestamp_seconds(self, fps: float) -> float:
        if fps <= 0:
            raise ValueError("fps must be positive")

        return self.frame / fps

    @property
    def ball_visible(self) -> bool:
        return self.ball.position is not None

    @property
    def tracked_player_count(self) -> int:
        return sum(player.position is not None for player in self.players)
