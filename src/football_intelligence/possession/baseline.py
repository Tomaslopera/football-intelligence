"""Simple, deterministic synthetic-safe proximity baseline.

No claim is made that proximity establishes true ball control, dead-ball status,
or competition-level accuracy. This baseline emits X for insufficient evidence.
"""

from dataclasses import dataclass

from football_intelligence.possession.contracts import FramePrediction, PossessionState
from football_intelligence.possession.features import ProximityFeatures


@dataclass(frozen=True, slots=True)
class ProximityBaselineConfig:
    max_control_distance_m: float = 2.0
    minimum_margin_m: float = 0.5

    def __post_init__(self) -> None:
        if self.max_control_distance_m <= 0 or self.minimum_margin_m < 0:
            raise ValueError("Distance threshold must be positive and margin nonnegative")


def predict_proximity(
    features: ProximityFeatures,
    config: ProximityBaselineConfig = ProximityBaselineConfig(),
) -> FramePrediction:
    """Emit H/A only with clear proximity evidence; otherwise X.

    D requires an independent dead-ball signal, which tracking proximity alone
    cannot establish. This limitation is intentional.
    """
    home = features.home_min_distance_m
    away = features.away_min_distance_m
    state = PossessionState.UNKNOWN
    if home is not None and away is not None:
        if home <= config.max_control_distance_m and away - home >= config.minimum_margin_m:
            state = PossessionState.HOME
        elif away <= config.max_control_distance_m and home - away >= config.minimum_margin_m:
            state = PossessionState.AWAY
    return FramePrediction(match_id=features.match_id, frame=features.frame, state=state)
