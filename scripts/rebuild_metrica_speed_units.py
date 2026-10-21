"""Rebuild corrected derived artifacts into a fresh private directory."""

import argparse
from pathlib import Path

from football_intelligence.tracking.correction import rebuild_speed_units


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--effective-unit", choices=("m/s", "kph"), required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    processed = Path("datasets/processed").resolve()
    if not args.output.resolve().is_relative_to(processed):
        parser.error("Output must be a new directory beneath datasets/processed/")
    result = rebuild_speed_units(
        args.previous,
        args.output,
        effective_unit=args.effective_unit,
        evidence=args.evidence,
    )
    print(
        f"Corrected {result['processed_frames']} frames; independent feature review passed."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Rebuild failed ({type(exc).__name__}); investigate locally.")
        raise SystemExit(1) from exc
