#!/usr/bin/env python3
"""CLI tool to load referral data from Excel."""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.loader import load_excel_to_db, preview_excel
from src.config import DB_PATH


def main():
    parser = argparse.ArgumentParser(
        description="Load heart failure referral data from Excel into the database"
    )
    parser.add_argument("excel_file", help="Path to the Excel file")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview file structure without loading",
    )
    parser.add_argument(
        "--sheet",
        default=0,
        help="Sheet name or index (default: 0)",
    )
    parser.add_argument(
        "--db",
        default=str(DB_PATH),
        help=f"Database path (default: {DB_PATH})",
    )

    args = parser.parse_args()

    excel_path = Path(args.excel_file)
    if not excel_path.exists():
        print(f"Error: File not found: {excel_path}")
        sys.exit(1)

    if args.preview:
        print(f"\n=== Preview: {excel_path.name} ===\n")
        info = preview_excel(str(excel_path), args.sheet)

        print(f"Total rows: {info['total_rows']}")
        print(f"\nColumns found ({len(info['columns'])}):")
        for col in info["columns"]:
            print(f"  - {col}")

        print(f"\nMapped to schema ({len(info['column_mappings'])}):")
        for field, col in info["column_mappings"].items():
            print(f"  {field} <- {col}")

        if info["unmapped_columns"]:
            print(f"\nUnmapped columns (will be stored in extra_data):")
            for col in info["unmapped_columns"]:
                print(f"  - {col}")

        print("\nSample data (first 3 rows):")
        for i, row in enumerate(info["sample_data"][:3]):
            print(f"\n  Row {i + 1}:")
            for k, v in list(row.items())[:8]:  # Show first 8 fields
                print(f"    {k}: {v}")
            if len(row) > 8:
                print(f"    ... and {len(row) - 8} more fields")

    else:
        print(f"\n=== Loading: {excel_path.name} ===\n")
        print(f"Database: {args.db}")

        stats = load_excel_to_db(str(excel_path), args.db, args.sheet)

        print(f"\nResults:")
        print(f"  Total rows: {stats['total_rows']}")
        print(f"  Loaded: {stats['loaded']}")
        print(f"  Skipped: {stats['skipped']}")

        if stats["mapped_columns"]:
            print(f"\nColumn mappings used:")
            for field, col in stats["mapped_columns"].items():
                print(f"  {field} <- {col}")

        if stats["unmapped_columns"]:
            print(f"\nUnmapped columns (stored in extra_data):")
            for col in stats["unmapped_columns"][:10]:
                print(f"  - {col}")
            if len(stats["unmapped_columns"]) > 10:
                print(f"  ... and {len(stats['unmapped_columns']) - 10} more")

        if stats["errors"]:
            print(f"\nErrors ({len(stats['errors'])}):")
            for err in stats["errors"][:5]:
                print(f"  - {err}")
            if len(stats["errors"]) > 5:
                print(f"  ... and {len(stats['errors']) - 5} more")

        print(f"\nData loaded to: {args.db}")


if __name__ == "__main__":
    main()
