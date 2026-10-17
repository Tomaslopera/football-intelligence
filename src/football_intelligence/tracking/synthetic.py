"""Deterministic synthetic football tracking fixtures."""

import math

import pandas as pd


def generate_tracking_table(
    n_frames: int = 100,
    *,
    missing_ball_every: int = 5,
) -> pd.DataFrame:
    """Create Metrica-shaped synthetic tracking rows.

    Two track slots are used to keep the initial fixture small.
    This is not an attempt to simulate a realistic full match.
    """
    if n_frames <= 0:
        raise ValueError("n_frames must be positive")

    if missing_ball_every <= 0:
        raise ValueError("missing_ball_every must be positive")

    rows = []

    for index in range(n_frames):
        time = index / 25.0
        ball_missing = index % missing_ball_every == 0

        rows.append(
            {
                "frame_id": index + 1,
                "ball_x": (math.nan if ball_missing else 0.5 + 0.1 * math.sin(time)),
                "ball_y": (math.nan if ball_missing else 0.5 + 0.1 * math.cos(time)),
                "1_x": 0.30 + 0.05 * math.sin(time),
                "1_y": 0.40,
                "1_s": 3.2,
                "2_x": 0.70 + 0.05 * math.cos(time),
                "2_y": 0.60,
                "2_s": 2.8,
            }
        )

    return pd.DataFrame(rows)
