"""Inspect an authorized Metrica EPTS sample locally."""

import argparse
from pathlib import Path

from football_intelligence.tracking.metrica import (
    load_metrica_epts,
)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--tracking",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    table = load_metrica_epts(
        args.metadata,
        args.tracking,
        limit=100,
    )

    print(f"Rows: {len(table)}")
    print(f"Columns: {len(table.columns)}")

    print("\nColumn names:")
    for column in table.columns:
        print(f"  {column}")

    print("\nFrame range:")
    print(table["frame_id"].head())

    print("\nTracking sample:")
    print(table.head(3).to_string())


if __name__ == "__main__":
    main()
