"""Load referral data from Excel files into the database."""

import json
from pathlib import Path
from typing import Optional
import pandas as pd
from sqlalchemy.orm import Session

from .models import Referral, Outcome
from .connection import init_db, get_session


# Column name mappings - maps possible Excel column names to our schema
COLUMN_MAPPINGS = {
    # Case ID
    "case_id": ["case_id", "id", "patient_id", "ref_id", "referral_id", "case"],
    # Demographics
    "age": ["age", "age_years", "patient_age"],
    "sex": ["sex", "gender", "patient_sex"],
    "bmi": ["bmi", "body_mass_index"],
    # Clinical
    "etiology": ["etiology", "diagnosis", "hf_etiology", "primary_diagnosis", "aetiology"],
    "nyha_class": ["nyha", "nyha_class", "nyha_functional_class"],
    "lvef": ["lvef", "ef", "ejection_fraction", "lv_ef"],
    "lvedd": ["lvedd", "lv_edd", "lv_end_diastolic_diameter"],
    # Hemodynamics
    "cardiac_index": ["ci", "cardiac_index", "cardiac_output_index"],
    "pcwp": ["pcwp", "pawp", "wedge", "pulmonary_wedge"],
    "pvr": ["pvr", "pulmonary_vascular_resistance"],
    "mean_pap": ["mpap", "mean_pap", "pa_mean", "pap_mean"],
    # Labs
    "creatinine": ["creatinine", "cr", "creat", "serum_creatinine"],
    "bilirubin": ["bilirubin", "bili", "total_bilirubin"],
    "sodium": ["sodium", "na", "serum_sodium"],
    "bnp": ["bnp", "nt_probnp", "ntprobnp", "pro_bnp"],
    "hemoglobin": ["hemoglobin", "hb", "hgb"],
    # Scores
    "intermacs_profile": ["intermacs", "intermacs_profile", "intermacs_level"],
    "hfss": ["hfss", "heart_failure_survival_score"],
    "shfm_score": ["shfm", "seattle_hf_score", "shfm_score"],
    # Other
    "devices": ["devices", "device", "icd", "crt", "implanted_devices"],
    "clinical_summary": ["summary", "clinical_summary", "notes", "clinical_notes", "presentation"],
    "referral_date": ["referral_date", "ref_date", "date_referred", "date"],
    # Outcomes
    "decision": ["decision", "outcome_decision", "listing_decision", "mdm_decision"],
    "final_outcome": ["final_outcome", "outcome", "result", "final_result"],
    "decision_rationale": ["rationale", "decision_rationale", "reason", "decision_reason"],
    "decline_reason": ["decline_reason", "reason_declined", "rejection_reason"],
}


def normalize_column_name(col: str) -> str:
    """Normalize column name for matching."""
    return col.lower().strip().replace(" ", "_").replace("-", "_")


def find_matching_column(df: pd.DataFrame, field: str) -> Optional[str]:
    """Find a DataFrame column that matches a schema field."""
    normalized_cols = {normalize_column_name(c): c for c in df.columns}

    # Check direct match first
    if field in normalized_cols:
        return normalized_cols[field]

    # Check aliases
    for alias in COLUMN_MAPPINGS.get(field, []):
        if alias in normalized_cols:
            return normalized_cols[alias]

    return None


def parse_comorbidities(value) -> Optional[dict]:
    """Parse comorbidities from various formats."""
    if pd.isna(value):
        return None

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        # Handle comma-separated list
        if "," in value:
            items = [item.strip() for item in value.split(",")]
            return {item: True for item in items if item}
        # Handle JSON string
        if value.startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        # Single value
        return {value: True}

    return None


def safe_float(value) -> Optional[float]:
    """Safely convert value to float."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value) -> Optional[int]:
    """Safely convert value to int."""
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_str(value) -> Optional[str]:
    """Safely convert value to string."""
    if pd.isna(value):
        return None
    return str(value).strip() or None


def load_excel_to_db(
    excel_path: str,
    db_path: str = "data/referrals.db",
    sheet_name: int | str = 0,
) -> dict:
    """
    Load referral data from Excel file into the database.

    Args:
        excel_path: Path to the Excel file
        db_path: Path to the SQLite database
        sheet_name: Sheet name or index to read

    Returns:
        Dictionary with loading statistics
    """
    # Initialize database
    init_db(db_path)
    session = get_session(db_path)

    # Read Excel file
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    stats = {
        "total_rows": len(df),
        "loaded": 0,
        "skipped": 0,
        "errors": [],
        "mapped_columns": {},
        "unmapped_columns": [],
    }

    # Build column mapping
    col_map = {}
    for field in COLUMN_MAPPINGS.keys():
        matched = find_matching_column(df, field)
        if matched:
            col_map[field] = matched
            stats["mapped_columns"][field] = matched

    # Track unmapped columns
    mapped_excel_cols = set(col_map.values())
    stats["unmapped_columns"] = [c for c in df.columns if c not in mapped_excel_cols]

    # Process each row
    for idx, row in df.iterrows():
        try:
            # Get or generate case ID
            case_id_col = col_map.get("case_id")
            if case_id_col and not pd.isna(row[case_id_col]):
                case_id = str(row[case_id_col])
            else:
                case_id = f"CASE_{idx:04d}"

            # Check if case already exists
            existing = session.query(Referral).filter_by(case_id=case_id).first()
            if existing:
                stats["skipped"] += 1
                continue

            # Create referral object
            referral = Referral(
                case_id=case_id,
                age=safe_int(row.get(col_map.get("age"))),
                sex=safe_str(row.get(col_map.get("sex"))),
                bmi=safe_float(row.get(col_map.get("bmi"))),
                etiology=safe_str(row.get(col_map.get("etiology"))),
                nyha_class=safe_int(row.get(col_map.get("nyha_class"))),
                lvef=safe_float(row.get(col_map.get("lvef"))),
                lvedd=safe_float(row.get(col_map.get("lvedd"))),
                cardiac_index=safe_float(row.get(col_map.get("cardiac_index"))),
                pcwp=safe_float(row.get(col_map.get("pcwp"))),
                pvr=safe_float(row.get(col_map.get("pvr"))),
                mean_pap=safe_float(row.get(col_map.get("mean_pap"))),
                creatinine=safe_float(row.get(col_map.get("creatinine"))),
                bilirubin=safe_float(row.get(col_map.get("bilirubin"))),
                sodium=safe_float(row.get(col_map.get("sodium"))),
                bnp=safe_float(row.get(col_map.get("bnp"))),
                hemoglobin=safe_float(row.get(col_map.get("hemoglobin"))),
                intermacs_profile=safe_int(row.get(col_map.get("intermacs_profile"))),
                hfss=safe_float(row.get(col_map.get("hfss"))),
                shfm_score=safe_float(row.get(col_map.get("shfm_score"))),
                devices=safe_str(row.get(col_map.get("devices"))),
                clinical_summary=safe_str(row.get(col_map.get("clinical_summary"))),
            )

            # Store unmapped columns as extra_data
            extra = {}
            for col in stats["unmapped_columns"]:
                val = row.get(col)
                if not pd.isna(val):
                    extra[col] = val if not isinstance(val, pd.Timestamp) else str(val)
            if extra:
                referral.extra_data = extra

            # Parse referral date
            date_col = col_map.get("referral_date")
            if date_col:
                date_val = row.get(date_col)
                if pd.notna(date_val):
                    if isinstance(date_val, pd.Timestamp):
                        referral.referral_date = date_val.to_pydatetime()

            session.add(referral)

            # Handle outcome if present
            decision_col = col_map.get("decision")
            if decision_col and pd.notna(row.get(decision_col)):
                outcome = Outcome(
                    referral=referral,
                    decision=safe_str(row.get(decision_col)),
                    final_outcome=safe_str(row.get(col_map.get("final_outcome"))),
                    decision_rationale=safe_str(row.get(col_map.get("decision_rationale"))),
                    decline_reason=safe_str(row.get(col_map.get("decline_reason"))),
                )
                session.add(outcome)

            stats["loaded"] += 1

        except Exception as e:
            stats["errors"].append(f"Row {idx}: {str(e)}")
            stats["skipped"] += 1

    session.commit()
    session.close()

    return stats


def preview_excel(excel_path: str, sheet_name: int | str = 0, rows: int = 5) -> dict:
    """
    Preview Excel file structure and sample data.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Sheet name or index
        rows: Number of sample rows to show

    Returns:
        Dictionary with file info and column mappings
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    info = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "column_mappings": {},
        "unmapped_columns": [],
        "sample_data": df.head(rows).to_dict(orient="records"),
    }

    # Check which columns map to our schema
    for field in COLUMN_MAPPINGS.keys():
        matched = find_matching_column(df, field)
        if matched:
            info["column_mappings"][field] = matched

    mapped_cols = set(info["column_mappings"].values())
    info["unmapped_columns"] = [c for c in df.columns if c not in mapped_cols]

    return info
