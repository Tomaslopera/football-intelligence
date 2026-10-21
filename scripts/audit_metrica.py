"""Run locally after checking enrollment terms. Prints no source records."""

import argparse
from pathlib import Path

from football_intelligence.tracking.audit import audit_metrica
from football_intelligence.tracking.models import RecordingSource


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--tracking", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--match-id", default="BAR-ATH")
    parser.add_argument("--source", choices=("tactical", "broadcast"), required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--limit", type=int, default=100)
    group.add_argument("--full", action="store_true")
    parser.add_argument("--expected-frames", type=int)
    parser.add_argument("--git-commit")
    parser.add_argument("--speed-unit-override", choices=("m/s", "kph"))
    parser.add_argument("--speed-unit-evidence")
    args = parser.parse_args()
    output = args.output.resolve()
    processed = Path("datasets/processed").resolve()
    if output == processed or not output.is_relative_to(processed):
        parser.error("Output must be a new directory beneath datasets/processed/")
    # Reject paths before reading assets or creating any output.
    for path in (args.metadata.resolve(), args.tracking.resolve()):
        if path.is_relative_to(output):
            parser.error("Output must not contain source assets")
    try:
        result = audit_metrica(
            args.metadata,
            args.tracking,
            output,
            match_id=args.match_id,
            source=RecordingSource(args.source),
            limit=None if args.full else args.limit,
            expected_frames=args.expected_frames,
            git_commit=args.git_commit,
            speed_unit_override=args.speed_unit_override,
            speed_unit_evidence=args.speed_unit_evidence,
        )
    except Exception as exc:
        print(f"Audit failed ({type(exc).__name__}). Inspect local output if created.")
        raise SystemExit(1) from exc
    print(f"Audit passed: {result['processed_frames']} frames ({result['scope']}).")
    print(f"Private aggregate report: {output / 'audit.json'}")


if __name__ == "__main__":
    main()
