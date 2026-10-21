"""User-run local raw speed check. Exports counts/errors only, never records."""

import argparse
import json
from pathlib import Path

import duckdb
from kloppy import metrica

from football_intelligence.tracking.metrica import (
    load_metrica_epts,
    normalize_metrica_columns,
    read_metrica_metadata,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--tracking", type=Path, required=True)
    parser.add_argument("--audit-directory", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=12000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("limit must be positive")
    if not args.output.resolve().is_relative_to(Path("datasets/processed").resolve()):
        parser.error("Output must be under datasets/processed/")
    if args.output.exists():
        parser.error("Output already exists")
    audit = json.loads((args.audit_directory / "audit.json").read_text())
    units = audit["lineage"]["speed_units"]
    override = units.get("effective_source")
    evidence = units.get("override_evidence")
    metadata = read_metrica_metadata(
        args.metadata,
        match_id=audit["metadata"]["match_id"],
        total_frames=args.limit,
        speed_unit_override=override,
        speed_unit_evidence=evidence,
    )
    raw = normalize_metrica_columns(
        metrica.load_tracking_epts(
            meta_data=str(args.metadata),
            raw_data=str(args.tracking),
            coordinates="metrica",
            limit=args.limit,
        ).to_df()
    )
    adapted = load_metrica_epts(
        args.metadata,
        args.tracking,
        limit=args.limit,
        speed_unit_override=override,
        speed_unit_evidence=evidence,
    )
    columns = [f"{slot}_s" for slot in metadata.slot_teams]
    divisor = 3.6 if metadata.effective_speed_unit == "kph" else 1.0
    comparable = raw[columns].notna() & adapted[columns].notna()
    errors = (adapted[columns] - raw[columns] / divisor).abs()
    long = adapted[["frame_id", *columns]].melt(
        id_vars="frame_id", var_name="slot", value_name="speed"
    )
    long["track_slot"] = long["slot"].str.removesuffix("_s").astype(int)
    long["frame"] = long["frame_id"] - 1
    long["match_id"] = metadata.match.match_id
    long["source"] = audit["source"]
    with duckdb.connect(":memory:") as connection:
        connection.register("sample", long)
        connection.read_parquet(
            str(args.audit_directory / "tracking/players.parquet")
        ).create_view("players")
        differences = connection.execute("""
            SELECT COUNT(*) FILTER (WHERE ABS(s.speed-p.speed_mps)>1e-8
                OR (s.speed IS NULL)!=(p.speed_mps IS NULL)) AS mismatches,
                COUNT(*) AS compared, MAX(ABS(s.speed-p.speed_mps)) AS max_error_mps
            FROM sample s JOIN players p USING (match_id,source,frame,track_slot)
        """).fetchone()
    result = {
        "source_unit": metadata.source_speed_unit,
        "effective_source_unit": metadata.effective_speed_unit,
        "canonical_unit": "m/s",
        "sample_frames": len(raw),
        "comparable_speeds": int(comparable.sum().sum()),
        "adapter_conversion_mismatches": int((errors > 1e-8).sum().sum()),
        "missingness_mismatches": int(
            (raw[columns].isna() != adapted[columns].isna()).sum().sum()
        ),
        "stored_sample_comparison": differences,
        "caveat": "Checks declared-unit conversion, not whether the provider declared the true physical unit",
    }
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Speed check failed ({type(exc).__name__}); investigate locally.")
        raise SystemExit(1) from exc
