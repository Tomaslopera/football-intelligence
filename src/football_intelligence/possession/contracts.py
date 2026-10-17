"""Competition-safe possession contracts.

The competition states H/A/D/X are kept distinct from tracking TeamSide.
Internal spell intervals are half-open: [start_frame, end_frame).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PossessionState(StrEnum):
    HOME = "H"
    AWAY = "A"
    DEAD = "D"
    UNKNOWN = "X"


class FramePrediction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str = Field(min_length=1)
    frame: int = Field(ge=0)
    state: PossessionState


class PossessionSpell(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str = Field(min_length=1)
    state: PossessionState
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_interval(self) -> "PossessionSpell":
        if self.state not in (PossessionState.HOME, PossessionState.AWAY):
            raise ValueError("Only H and A form possession spells")
        if self.end_frame <= self.start_frame:
            raise ValueError("Spell end_frame must exceed start_frame")
        return self

    @property
    def duration_frames(self) -> int:
        return self.end_frame - self.start_frame
