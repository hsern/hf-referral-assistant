"""Utility functions for checking data freshness."""

import os
from pathlib import Path
from typing import Optional


def get_latest_mtime(directory: Path, pattern: str) -> Optional[float]:
    """Get the most recent modification time of files matching pattern."""
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(f.stat().st_mtime for f in files)


def get_file_mtime(filepath: Path) -> Optional[float]:
    """Get modification time of a file."""
    if filepath.exists():
        return filepath.stat().st_mtime
    return None


def check_guidelines_freshness(guidelines_dir: Path, index_path: Path) -> dict:
    """
    Check if guideline index is up to date.

    Returns:
        dict with 'needs_update', 'pdf_count', 'index_exists', 'message'
    """
    pdf_files = list(guidelines_dir.glob("*.pdf"))
    pdf_count = len(pdf_files)

    index_file = index_path / "embeddings.npy"

    if not index_file.exists():
        return {
            "needs_update": True,
            "pdf_count": pdf_count,
            "index_exists": False,
            "message": f"{pdf_count} PDFs found but not indexed"
        }

    if pdf_count == 0:
        return {
            "needs_update": False,
            "pdf_count": 0,
            "index_exists": True,
            "message": "No PDFs in guidelines folder"
        }

    latest_pdf_mtime = get_latest_mtime(guidelines_dir, "*.pdf")
    index_mtime = get_file_mtime(index_file)

    if latest_pdf_mtime and index_mtime and latest_pdf_mtime > index_mtime:
        return {
            "needs_update": True,
            "pdf_count": pdf_count,
            "index_exists": True,
            "message": "Guidelines have been modified since last index"
        }

    return {
        "needs_update": False,
        "pdf_count": pdf_count,
        "index_exists": True,
        "message": f"{pdf_count} guidelines indexed"
    }


def check_referrals_freshness(referrals_dir: Path, db_path: Path) -> dict:
    """
    Check if referral database is up to date.

    Returns:
        dict with 'needs_update', 'excel_count', 'db_exists', 'message'
    """
    excel_files = list(referrals_dir.glob("*.xlsx")) + list(referrals_dir.glob("*.xls"))
    excel_count = len(excel_files)

    if not db_path.exists():
        return {
            "needs_update": True,
            "excel_count": excel_count,
            "db_exists": False,
            "message": f"{excel_count} Excel file(s) found but database not created"
        }

    if excel_count == 0:
        return {
            "needs_update": False,
            "excel_count": 0,
            "db_exists": True,
            "message": "No Excel files in referrals folder"
        }

    latest_excel_mtime = max(
        get_latest_mtime(referrals_dir, "*.xlsx") or 0,
        get_latest_mtime(referrals_dir, "*.xls") or 0
    )
    db_mtime = get_file_mtime(db_path)

    if latest_excel_mtime and db_mtime and latest_excel_mtime > db_mtime:
        return {
            "needs_update": True,
            "excel_count": excel_count,
            "db_exists": True,
            "message": "Excel data has been modified since last import"
        }

    return {
        "needs_update": False,
        "excel_count": excel_count,
        "db_exists": True,
        "message": "Referral data up to date"
    }
