#!/usr/bin/env python3
"""Heart Failure Referral Assistant - Main CLI."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database import Referral, get_session, init_db
from src.retrieval import generate_referral_embeddings
from src.predictor import suggest_outcome
from src.indexer import load_guideline_index
from src.config import DB_PATH, INDEX_PATH


def query_interactive(db_path: str, index_path: str):
    """Interactive query mode."""
    print("\n=== Heart Failure Referral Assistant ===")
    print("Enter patient data to get outcome suggestions.\n")

    # Try to load guideline index
    try:
        guideline_index = load_guideline_index(index_path)
        print(f"Loaded guideline index with {len(guideline_index.chunks)} chunks.\n")
    except FileNotFoundError:
        print("Warning: No guideline index found. Run index_guidelines.py first.")
        print("Continuing without guideline citations.\n")
        guideline_index = None

    while True:
        print("-" * 50)
        print("Enter referral data (or 'quit' to exit):\n")

        referral_data = {}

        # Collect basic data
        age = input("Age: ").strip()
        if age.lower() == "quit":
            break
        if age:
            referral_data["age"] = int(age)

        sex = input("Sex (M/F): ").strip()
        if sex:
            referral_data["sex"] = sex

        etiology = input("Etiology (e.g., DCM, ICM): ").strip()
        if etiology:
            referral_data["etiology"] = etiology

        nyha = input("NYHA Class (1-4): ").strip()
        if nyha:
            referral_data["nyha_class"] = int(nyha)

        lvef = input("LVEF (%): ").strip()
        if lvef:
            referral_data["lvef"] = float(lvef)

        pvr = input("PVR (Wood units): ").strip()
        if pvr:
            referral_data["pvr"] = float(pvr)

        cr = input("Creatinine: ").strip()
        if cr:
            referral_data["creatinine"] = float(cr)

        intermacs = input("INTERMACS Profile (1-7): ").strip()
        if intermacs:
            referral_data["intermacs_profile"] = int(intermacs)

        bmi = input("BMI: ").strip()
        if bmi:
            referral_data["bmi"] = float(bmi)

        if not referral_data:
            print("\nNo data entered. Please try again.\n")
            continue

        print("\nAnalyzing...")

        # Get suggestion
        suggestion = suggest_outcome(
            referral_data,
            guideline_index=guideline_index,
            db_path=db_path,
        )

        # Display results
        print("\n" + "=" * 50)
        print(suggestion.format_summary())
        print(suggestion.format_similar_cases())

        if suggestion.guideline_citations:
            show_citations = input("Show guideline citations? (y/n): ").strip().lower()
            if show_citations == "y":
                print(suggestion.format_citations())

        print()


def query_case(case_id: str, db_path: str, index_path: str):
    """Query a specific case from the database."""
    init_db(db_path)
    session = get_session(db_path)

    referral = session.query(Referral).filter_by(case_id=case_id).first()
    if not referral:
        print(f"Case not found: {case_id}")
        session.close()
        return

    print(f"\n=== Analyzing Case: {case_id} ===\n")

    # Load guideline index
    try:
        guideline_index = load_guideline_index(index_path)
    except FileNotFoundError:
        guideline_index = None

    suggestion = suggest_outcome(
        referral,
        guideline_index=guideline_index,
        db_path=db_path,
    )

    print(suggestion.format_summary())
    print(suggestion.format_similar_cases())

    if suggestion.guideline_citations:
        print(suggestion.format_citations())

    session.close()


def list_cases(db_path: str, limit: int = 20):
    """List cases in the database."""
    init_db(db_path)
    session = get_session(db_path)

    referrals = session.query(Referral).limit(limit).all()

    print(f"\n=== Cases in Database (showing {len(referrals)}) ===\n")
    print(f"{'Case ID':<15} {'Age':<5} {'Sex':<5} {'Etiology':<15} {'NYHA':<5} {'LVEF':<6}")
    print("-" * 55)

    for r in referrals:
        print(
            f"{r.case_id:<15} {str(r.age or '-'):<5} {str(r.sex or '-'):<5} "
            f"{str(r.etiology or '-')[:15]:<15} {str(r.nyha_class or '-'):<5} "
            f"{str(r.lvef or '-'):<6}"
        )

    total = session.query(Referral).count()
    if total > limit:
        print(f"\n... and {total - limit} more cases")

    session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Heart Failure Transplant Referral Assistant"
    )
    parser.add_argument(
        "--db",
        default=str(DB_PATH),
        help=f"Database path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--index",
        default=str(INDEX_PATH),
        help=f"Guideline index path (default: {INDEX_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Interactive query
    subparsers.add_parser("query", help="Interactive query mode")

    # Query specific case
    case_parser = subparsers.add_parser("case", help="Analyze a specific case")
    case_parser.add_argument("case_id", help="Case ID to analyze")

    # List cases
    list_parser = subparsers.add_parser("list", help="List cases in database")
    list_parser.add_argument(
        "-n", type=int, default=20, help="Number of cases to show"
    )

    # Generate embeddings
    subparsers.add_parser("embed", help="Generate embeddings for all cases")

    args = parser.parse_args()

    if args.command == "query":
        query_interactive(args.db, args.index)
    elif args.command == "case":
        query_case(args.case_id, args.db, args.index)
    elif args.command == "list":
        list_cases(args.db, args.n)
    elif args.command == "embed":
        print("Generating embeddings for referral cases...")
        count = generate_referral_embeddings(args.db)
        print(f"Generated {count} embeddings.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
