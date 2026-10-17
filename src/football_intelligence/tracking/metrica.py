"""Adapter for Metrica EPTS tracking data."""

import re
from pathlib import Path
from typing import Any

import pandas as pd
from kloppy import metrica  # type: ignore[import-untyped]

# Accept either source naming convention:
# 1_x, 1_y, 1_s
# Track_1_x, Track_1_y, Track_1_s
TRACK_COLUMN = re.compile(r"^(?:Track_)?([1-9]\d*)_([xys])$")


def normalize_metrica_columns(
    table: pd.DataFrame,
) -> pd.DataFrame:
    """Convert Kloppy track column names into our canonical input names."""
    if not all(isinstance(name, str) for name in table.columns):
        raise ValueError("Metrica columns must be strings")

    renamed: dict[str, str] = {}

    for name in table.columns:
        match = TRACK_COLUMN.fullmatch(name)

        if match is not None:
            slot, attribute = match.groups()
            renamed[name] = f"{int(slot)}_{attribute}"

    output_columns = [renamed.get(name, name) for name in table.columns]

    if len(output_columns) != len(set(output_columns)):
        raise ValueError("Metrica column normalization produced duplicates")

    return table.rename(columns=renamed)


def load_metrica_epts(
    metadata_path: Path,
    tracking_path: Path,
    *,
    limit: int | None = None,
) -> pd.DataFrame:
    """Load an EPTS pair and return normalized tracking columns."""
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)

    if not tracking_path.is_file():
        raise FileNotFoundError(tracking_path)

    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")

    options: dict[str, Any] = {
        "meta_data": str(metadata_path),
        "raw_data": str(tracking_path),
        "coordinates": "metrica",
    }

    if limit is not None:
        options["limit"] = limit

    dataset = metrica.load_tracking_epts(**options)

    table = dataset.to_df()

    if "frame_id" not in table.columns:
        raise ValueError("EPTS data is missing frame_id")

    return normalize_metrica_columns(table)
