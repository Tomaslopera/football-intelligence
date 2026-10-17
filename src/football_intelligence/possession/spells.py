"""Extract H/A possession spells from contiguous frame predictions."""

from collections.abc import Sequence

from football_intelligence.possession.contracts import (
    FramePrediction,
    PossessionSpell,
    PossessionState,
)


def extract_spells(predictions: Sequence[FramePrediction]) -> list[PossessionSpell]:
    """Return half-open intervals; D/X and frame gaps terminate spells.

    Inputs must belong to one match and be strictly increasing in frame number.
    This is a product-facing convention, not an official evaluator clone.
    """
    spells: list[PossessionSpell] = []
    if not predictions:
        return spells

    match_id = predictions[0].match_id
    previous_frame = -1
    active_state: PossessionState | None = None
    start_frame = 0

    def finish(end_frame: int) -> None:
        if active_state is not None:
            spells.append(
                PossessionSpell(
                    match_id=match_id,
                    state=active_state,
                    start_frame=start_frame,
                    end_frame=end_frame,
                )
            )

    for prediction in predictions:
        if prediction.match_id != match_id:
            raise ValueError("Predictions must belong to one match")
        if prediction.frame <= previous_frame:
            raise ValueError("Frames must be strictly increasing")
        eligible = prediction.state in (PossessionState.HOME, PossessionState.AWAY)
        if prediction.frame != previous_frame + 1 or prediction.state != active_state:
            finish(previous_frame + 1)
            active_state = prediction.state if eligible else None
            start_frame = prediction.frame
        previous_frame = prediction.frame
    finish(previous_frame + 1)
    return spells
