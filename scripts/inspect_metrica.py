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
    parser.add_argument("--limit", type=int, default=100)

    args = parser.parse_args()

    try:
        table = load_metrica_epts(
            args.metadata,
            args.tracking,
            limit=args.limit,
        )
    except Exception as exc:
        print(f"Inspection failed ({type(exc).__name__}); investigate locally.")
        raise SystemExit(1) from exc

    print(f"Rows: {len(table)}")
    print(f"Columns: {len(table.columns)}")

    print("\nColumn names:")
    for column in table.columns:
        print(f"  {column}")

    print("\nFrame range:")
    print(f"{table['frame_id'].min()} .. {table['frame_id'].max()}")
    print("\nMissing values per column:")
    for column, count in table.isna().sum().items():
        print(f"  {column}: {count}")


if __name__ == "__main__":
    main()
