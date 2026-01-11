#!/usr/bin/env python3
"""CLI tool to index PDF guidelines."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.indexer import build_guideline_index
from src.config import GUIDELINES_DIR, INDEX_PATH


def main():
    parser = argparse.ArgumentParser(
        description="Index PDF clinical guidelines for retrieval"
    )
    parser.add_argument(
        "--guidelines-dir",
        default=str(GUIDELINES_DIR),
        help=f"Directory containing PDF guidelines (default: {GUIDELINES_DIR})",
    )
    parser.add_argument(
        "--index-path",
        default=str(INDEX_PATH),
        help=f"Where to save the index (default: {INDEX_PATH})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Size of text chunks in characters (default: 500)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Overlap between chunks (default: 50)",
    )

    args = parser.parse_args()

    guidelines_dir = Path(args.guidelines_dir)
    if not guidelines_dir.exists():
        print(f"Error: Directory not found: {guidelines_dir}")
        sys.exit(1)

    pdf_files = list(guidelines_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"Error: No PDF files found in {guidelines_dir}")
        sys.exit(1)

    print(f"\n=== Indexing Guidelines ===\n")
    print(f"Directory: {guidelines_dir}")
    print(f"PDF files found: {len(pdf_files)}")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")

    print(f"\nBuilding index...")
    build_guideline_index(
        guidelines_dir,
        index_path=args.index_path,
    )

    print(f"\nDone! Index saved to: {args.index_path}")


if __name__ == "__main__":
    main()
