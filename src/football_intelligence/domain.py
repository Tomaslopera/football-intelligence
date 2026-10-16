from enum import StrEnum

from pydantic import BaseModel, Field


class PossessionState(StrEnum):
    HOME = "H"
    AWAY = "A"
    DEAD_BALL = "D"
    UNKNOWN = "X"


class PossessionPrediction(BaseModel):
    frame: int = Field(ge=0)
    label: PossessionState
    model_version: str
    confidence: float | None = Field(default=None, ge=0, le=1)
