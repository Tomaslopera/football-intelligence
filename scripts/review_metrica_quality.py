"""Review processed Parquet locally; export sanitized aggregates only."""

import argparse
import json
from pathlib import Path

from football_intelligence.tracking.review import review_processed_audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    processed = Path("datasets/processed").resolve()
    if not args.output.resolve().is_relative_to(processed):
        parser.error("Review output must be under datasets/processed/")
    if args.output.exists():
        parser.error("Review output already exists")
    result = review_processed_audit(args.audit_directory)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
