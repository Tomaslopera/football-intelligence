"""Adapter for Metrica EPTS tracking data."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd
from kloppy import metrica  # type: ignore[import-untyped]

from football_intelligence.tracking.models import MatchMetadata, TeamSide

# Accept either source naming convention:
# 1_x, 1_y, 1_s
# Track_1_x, Track_1_y, Track_1_s
TRACK_COLUMN = re.compile(r"^(?:Track_)?([1-9]\d*)_([xys])$")

BAR_ATH_TACTICAL_SPEED_EVIDENCE = (
    "https://github.com/metrica-sports/more-than-a-hack-2027/blob/"
    "3de6b60aeabd2475d95879a651d38b72bc4fba00/DATA.md#automatic-tracking-data-atd"
    " — official BAR-ATH documentation defines Kloppy EPTS speeds in m/s;"
    " corroborated by full-match motion diagnostics"
)


@dataclass(frozen=True)
class MetricaMetadata:
    """Explicit source metadata; slots are observation channels, not people."""

    match: MatchMetadata
    slot_teams: dict[int, TeamSide]
    source_speed_unit: str | None = None
    effective_speed_unit: str | None = None
    speed_unit_evidence: str | None = None


def _effective_speed_unit(
    declared: str | None, override: str | None, evidence: str | None
) -> str | None:
    """Permit a documented source correction without changing generic defaults."""
    if override is None:
        if evidence is not None:
            raise ValueError("Speed-unit evidence requires an override")
        return declared
    if (
        declared is None
        or override not in {"m/s", "kph"}
        or not evidence
        or not evidence.strip()
    ):
        raise ValueError(
            "Speed-unit override requires supported units and explicit evidence"
        )
    return override


def _speed_unit(metadata: ET.Element) -> str | None:
    """Resolve a single explicit speed unit, or no speed channel at all."""
    units = {
        channel.findtext("Unit")
        for channel in metadata.findall(
            "Devices/Device/Sensors/Sensor/Channels/Channel"
        )
        if channel.get("id") == "s"
    }
    if not units:
        return None
    if len(units) != 1 or not units <= {"m/s", "kph"}:
        raise ValueError(
            "Unsupported or ambiguous EPTS speed units; expected m/s or kph"
        )
    return units.pop()


def read_metrica_metadata(
    path: Path,
    *,
    match_id: str,
    total_frames: int,
    speed_unit_override: str | None = None,
    speed_unit_evidence: str | None = None,
) -> MetricaMetadata:
    """Read normalized EPTS metadata without guessing home/away or units.

    Unlike Kloppy's missing-Score fallback, XML team order is not evidence
    of team side. Unsupported conventions require explicit investigation.
    """
    root = ET.parse(path).getroot()
    metadata = root.find("Metadata")
    if metadata is None:
        raise ValueError("Missing EPTS Metadata")
    score = metadata.find("Sessions/Session/MatchParameters/Score")
    if score is None:
        raise ValueError("Explicit home/away team metadata is required")
    home_id = score.get("idLocalTeam")
    away_id = score.get("idVisitingTeam")
    if not home_id or not away_id or home_id == away_id:
        raise ValueError("Invalid explicit home/away team IDs")
    sides = {home_id: TeamSide.HOME, away_id: TeamSide.AWAY}
    teams = metadata.findall("Teams/Team")
    names = {team.get("id"): team.findtext("Name", "") for team in teams}
    if len(teams) != 2 or len(names) != 2 or set(names) != set(sides):
        raise ValueError("Team definitions disagree with explicit home/away IDs")

    sensors = metadata.findall("Devices/Device/Sensors/Sensor")
    position_units = {
        channel.findtext("Unit")
        for sensor in sensors
        if sensor.get("id") == "position"
        for channel in sensor.findall("Channels/Channel")
        if channel.get("id") in {"x", "y"}
    }
    speed_unit = _speed_unit(metadata)
    effective_unit = _effective_speed_unit(
        speed_unit, speed_unit_override, speed_unit_evidence
    )
    if position_units != {"normalized"}:
        raise ValueError("EPTS positions must explicitly use normalized units")

    slots: dict[int, TeamSide] = {}
    for player in metadata.findall("Players/Player"):
        identifier = player.get("id", "")
        match = re.fullmatch(r"(?:Track_)?([1-9]\d*)", identifier)
        if match is None:
            raise ValueError("Unsupported EPTS track identifier")
        slot = int(match.group(1))
        team_id = player.get("teamId", "")
        if slot in slots or team_id not in sides:
            raise ValueError("Duplicate slot or unknown source team")
        slots[slot] = sides[team_id]
    if not slots or set(slots.values()) != {TeamSide.HOME, TeamSide.AWAY}:
        raise ValueError("Expected track metadata for both teams")

    return MetricaMetadata(
        match=MatchMetadata(
            match_id=match_id,
            home_team=names[home_id],
            away_team=names[away_id],
            fps=float(metadata.findtext("GlobalConfig/FrameRate", "nan")),
            total_frames=total_frames,
            pitch_length_m=float(
                metadata.findtext("Sessions/Session/FieldSize/Width", "nan")
            ),
            pitch_width_m=float(
                metadata.findtext("Sessions/Session/FieldSize/Height", "nan")
            ),
        ),
        slot_teams=slots,
        source_speed_unit=speed_unit,
        effective_speed_unit=effective_unit,
        speed_unit_evidence=speed_unit_evidence,
    )


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
    speed_unit_override: str | None = None,
    speed_unit_evidence: str | None = None,
) -> pd.DataFrame:
    """Load EPTS tracking with normalized coordinates and speeds in m/s.

    Kloppy 3.19.1 preserves EPTS speed values, regardless of declared units.
    Convert actual kph here once, before canonical ingestion. A documented
    override handles exports whose declared unit conflicts with provider docs.
    """
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)

    if not tracking_path.is_file():
        raise FileNotFoundError(tracking_path)

    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")

    metadata = ET.parse(metadata_path).getroot().find("Metadata")
    if metadata is None:
        raise ValueError("Missing EPTS Metadata")
    speed_unit = _speed_unit(metadata)
    speed_unit = _effective_speed_unit(
        speed_unit, speed_unit_override, speed_unit_evidence
    )

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

    table = normalize_metrica_columns(table)
    speed_columns = [
        name
        for name in table.columns
        if name == "ball_speed"
        or ((match := TRACK_COLUMN.fullmatch(name)) is not None and match[2] == "s")
    ]
    if speed_unit is None and table[speed_columns].notna().any().any():
        raise ValueError("Missing EPTS speed units for observed speeds")
    if speed_unit == "kph":
        table[speed_columns] = table[speed_columns] / 3.6
    return table
