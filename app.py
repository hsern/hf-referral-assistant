#!/usr/bin/env python3
"""Heart Failure Referral Assistant - For General HF Physicians."""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd

from src.database import Referral, get_session, init_db
from src.predictor import suggest_outcome
from src.indexer import load_guideline_index
from src.config import DB_PATH, INDEX_PATH, GUIDELINES_DIR, REFERRALS_DIR
from src.utils import check_guidelines_freshness, check_referrals_freshness


st.set_page_config(
    page_title="Advanced HF Referral Assistant",
    page_icon="❤️",
    layout="wide",
)


def load_index():
    try:
        return load_guideline_index(INDEX_PATH)
    except FileNotFoundError:
        return None


def init_database():
    init_db(str(DB_PATH))
    return str(DB_PATH)


# Decline reason labels for display
DECLINE_REASON_LABELS = {
    "illicit_drug_use": "Illicit Drug Use",
    "high_bmi": "High BMI",
    "frailty": "Frailty",
    "multi_organ_failure": "Multi-organ Failure",
    "malignancy": "Malignancy",
    "psychosocial": "Psychosocial Factors",
    "adverse_pvr": "Adverse PVR",
    "other": "Other",
}


# Sidebar for data management
with st.sidebar:
    st.header("Data Status")

    # Check guidelines status
    guidelines_status = check_guidelines_freshness(GUIDELINES_DIR, INDEX_PATH)
    referrals_status = check_referrals_freshness(REFERRALS_DIR, DB_PATH)

    # Guidelines section
    st.subheader("Guidelines")
    if guidelines_status["needs_update"]:
        st.warning(guidelines_status["message"])
        if st.button("Index Guidelines", key="index_btn"):
            with st.spinner("Indexing PDFs..."):
                result = subprocess.run(
                    [sys.executable, "index_guidelines.py"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    st.success("Guidelines indexed!")
                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.error(f"Error: {result.stderr}")
    else:
        st.success(guidelines_status["message"])

    st.divider()

    # Referrals section
    st.subheader("Referral Data")
    if referrals_status["needs_update"]:
        st.warning(referrals_status["message"])

        # Find Excel files
        excel_files = list(REFERRALS_DIR.glob("*.xlsx")) + list(REFERRALS_DIR.glob("*.xls"))

        if excel_files:
            selected_file = st.selectbox(
                "Select file to import",
                excel_files,
                format_func=lambda x: x.name
            )

            if st.button("Import Data", key="import_btn"):
                with st.spinner("Importing data..."):
                    # Load data
                    result = subprocess.run(
                        [sys.executable, "load_data.py", str(selected_file)],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        # Generate embeddings
                        result2 = subprocess.run(
                            [sys.executable, "assistant.py", "embed"],
                            capture_output=True,
                            text=True
                        )
                        st.success("Data imported!")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error(f"Error: {result.stderr}")
    else:
        st.success(referrals_status["message"])

        # Show case count
        try:
            db_path = init_database()
            session = get_session(db_path)
            count = session.query(Referral).count()
            session.close()
            st.caption(f"{count} cases in database")
        except:
            pass

    st.divider()
    st.caption("Place PDFs in `data/guidelines/`")
    st.caption("Place Excel in `data/referrals/`")


# Initialize resources
db_path = init_database()
guideline_index = load_index()


# Header
st.title("Advanced Heart Failure Referral Assistant")

st.divider()

# Two columns
col_input, col_results = st.columns([1, 2])

with col_input:
    st.subheader("Patient Details")

    # Basic demographics
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("Age", min_value=18, max_value=80, value=55)
    with c2:
        sex = st.selectbox("Sex", ["M", "F"])

    # Height, weight, BMI
    c1, c2 = st.columns(2)
    with c1:
        height = st.number_input("Height (cm)", min_value=120, max_value=220, value=170)
    with c2:
        weight = st.number_input("Weight (kg)", min_value=30, max_value=200, value=75)

    bmi = weight / ((height / 100) ** 2)
    st.markdown(f"**BMI: {bmi:.1f} kg/m²**")

    etiology = st.selectbox("Etiology", [
        "Ischaemic Cardiomyopathy",
        "Dilated Cardiomyopathy",
        "Hypertrophic Cardiomyopathy",
        "Valvular Heart Disease",
        "Chemotherapy-induced",
        "Other/Unknown",
    ])

    c1, c2 = st.columns(2)
    with c1:
        lvef = st.number_input("LVEF (%)", min_value=5, max_value=55, value=25)
    with c2:
        nyha = st.selectbox("NYHA Class", ["I", "II", "IIIa", "IIIb", "IV"], index=3)

    on_inotropes = st.selectbox(
        "IV Inotropes",
        ["No", "Yes"],
        help="Current or prior need for IV inotropic support"
    )

    st.divider()

    # I NEED HELP criteria - some auto-populated based on patient details
    st.subheader("I NEED HELP Criteria")
    st.caption("Check all that apply (some auto-populated from patient details)")

    # Auto-populate based on patient details
    auto_inotropes = on_inotropes == "Yes"
    auto_nyha = nyha in ["IIIb", "IV"]
    auto_ef = lvef <= 35

    i_inotropes = st.checkbox(
        "**I** - IV Inotropes",
        value=auto_inotropes,
        disabled=auto_inotropes,
        help="Current or prior need for IV inotropic support"
    )

    n_nyha = st.checkbox(
        "**N** - NYHA IIIb/IV",
        value=auto_nyha,
        disabled=auto_nyha,
        help="Persistent NYHA class IIIb or IV symptoms despite therapy"
    )

    e_ef = st.checkbox(
        "**E** - EF ≤35%",
        value=auto_ef,
        disabled=auto_ef,
        help="Left ventricular ejection fraction ≤35%"
    )

    e_endorgan = st.checkbox(
        "**E** - End-organ dysfunction",
        help="Rising creatinine, liver dysfunction, or weight loss"
    )

    d_defib = st.checkbox(
        "**D** - Defibrillator shocks",
        help="Recurrent appropriate ICD shocks"
    )

    h_hosp = st.checkbox(
        "**H** - Hospitalisations >1 in 12 months",
        help="More than one HF hospitalisation in the past year"
    )

    e_edema = st.checkbox(
        "**E** - Escalating diuretics",
        help="Persistent congestion despite increasing diuretic doses"
    )

    l_lowbp = st.checkbox(
        "**L** - Low BP / Low sodium",
        help="SBP consistently ≤90 mmHg or sodium <134 mmol/L"
    )

    p_peak = st.checkbox(
        "**P** - Peak VO₂ <14 or med intolerance",
        help="Peak VO₂ <14 mL/kg/min or inability to tolerate guideline-directed therapy"
    )

    st.divider()

    # Additional context
    st.subheader("Additional Information")

    c1, c2 = st.columns(2)
    with c1:
        creatinine = st.number_input("Creatinine (μmol/L)", min_value=50, max_value=500, value=120)
    with c2:
        bilirubin = st.number_input("Bilirubin (μmol/L)", min_value=2, max_value=200, value=15)

    c1, c2 = st.columns(2)
    with c1:
        bnp = st.number_input("NT-proBNP (pg/mL)", min_value=100, max_value=50000, value=2000)
    with c2:
        furosemide_dose = st.number_input(
            "Furosemide equiv. (mg/day)",
            min_value=0, max_value=1000, value=80,
            help="Bumetanide 1mg = Furosemide 40mg"
        )

    devices = st.multiselect(
        "Current devices",
        ["None", "Pacemaker", "ICD", "CRT-P", "CRT-D"],
        default=["None"]
    )

    clinical_concern = st.text_area(
        "Clinical concern / reason for referral",
        placeholder="e.g., Declining despite optimal therapy, recurrent admissions...",
        height=80
    )

    medical_history = st.text_area(
        "Medical, Surgical and Social History of note?",
        placeholder="e.g., Previous cardiac surgery, diabetes, smoking history, social support...",
        height=80
    )

    analyze = st.button("Check Referral Criteria", type="primary", use_container_width=True)


# Results
with col_results:
    if analyze:
        # Count I NEED HELP criteria met
        criteria_met = sum([
            i_inotropes, n_nyha, e_ef, e_endorgan, d_defib,
            h_hosp, e_edema, l_lowbp, p_peak
        ])

        criteria_list = []
        if i_inotropes: criteria_list.append("IV Inotropes")
        if n_nyha: criteria_list.append("NYHA IIIb/IV")
        if e_ef: criteria_list.append("EF ≤35%")
        if e_endorgan: criteria_list.append("End-organ dysfunction")
        if d_defib: criteria_list.append("Defibrillator shocks")
        if h_hosp: criteria_list.append("Recurrent hospitalisations")
        if e_edema: criteria_list.append("Escalating diuretics")
        if l_lowbp: criteria_list.append("Low BP/sodium")
        if p_peak: criteria_list.append("Low peak VO₂/med intolerance")

        # Recommendation based on criteria
        st.subheader("Referral Assessment")

        # Check for contraindications
        contraindications = []
        if bmi > 35:
            contraindications.append(f"BMI >35 ({bmi:.1f})")

        if contraindications:
            st.warning("**Potential contraindications identified:**")
            for c in contraindications:
                st.markdown(f"- {c}")
            st.markdown("*Discuss with transplant team before referral*")
            st.markdown("---")

        if criteria_met >= 2:
            st.success(f"**Referral recommended** — {criteria_met} of 9 criteria met")
            st.markdown("This patient meets multiple I NEED HELP criteria suggesting benefit from advanced HF evaluation.")
        elif criteria_met == 1:
            st.warning(f"**Consider referral** — {criteria_met} criterion met")
            st.markdown("Single criterion met. Consider referral if clinical trajectory concerning.")
        else:
            st.info("**Optimise current therapy** — No criteria currently met")
            st.markdown("Continue guideline-directed medical therapy with close monitoring.")

        if criteria_list:
            st.markdown("**Criteria present:**")
            for c in criteria_list:
                st.markdown(f"- {c}")

        st.divider()

        # Build referral for similarity search
        nyha_map = {"I": 1, "II": 2, "IIIa": 3, "IIIb": 3, "IV": 4}
        device_str = ", ".join(d for d in devices if d != "None")

        referral_data = {
            "age": age,
            "sex": sex,
            "bmi": bmi,
            "etiology": etiology,
            "nyha_class": nyha_map.get(nyha, 3),
            "lvef": lvef,
            "creatinine": creatinine / 88.4,
            "bilirubin": bilirubin / 17.1,
            "bnp": bnp,
            "devices": device_str,
            "clinical_summary": clinical_concern,
        }

        with st.spinner("Finding similar cases..."):
            suggestion = suggest_outcome(
                referral_data,
                guideline_index=guideline_index,
                db_path=db_path,
            )

        # Similar cases - show only decline rate and reasons
        st.subheader("Historical Referral Outcomes")
        st.caption("Based on similar cases from the transplant centre")

        if suggestion.similar_cases:
            # Calculate decline stats
            total_cases = len(suggestion.similar_cases)
            cases_with_outcome = sum(1 for c in suggestion.similar_cases if c.outcome)
            declined_cases = [c for c in suggestion.similar_cases if c.outcome and c.outcome.decision == "declined"]
            decline_count = len(declined_cases)

            if cases_with_outcome > 0:
                decline_pct = decline_count / cases_with_outcome * 100

                # Show decline rate prominently
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric(
                        "Decline Rate",
                        f"{decline_pct:.0f}%",
                        help=f"{decline_count} of {cases_with_outcome} similar referrals were declined"
                    )

                # Show decline reasons chart
                with col2:
                    if declined_cases:
                        # Collect decline reasons
                        reasons = {}
                        for case in declined_cases:
                            reason = case.outcome.decline_reason if case.outcome.decline_reason else "other"
                            label = DECLINE_REASON_LABELS.get(reason, reason.replace("_", " ").title())
                            reasons[label] = reasons.get(label, 0) + 1

                        if reasons:
                            # Create bar chart
                            df_reasons = pd.DataFrame({
                                "Reason": list(reasons.keys()),
                                "Count": list(reasons.values())
                            })
                            df_reasons = df_reasons.sort_values("Count", ascending=True)

                            st.markdown("**Reasons for Decline**")
                            st.bar_chart(df_reasons.set_index("Reason"), horizontal=True)
        else:
            st.info("No similar cases found in database.")

        st.divider()

        # Guideline references
        st.subheader("Relevant Guidelines")

        if suggestion.guideline_citations:
            for citation in suggestion.guideline_citations[:4]:
                source = citation.source.replace(".pdf", "")
                if "ehab368" in source:
                    source = "ESC 2021 HF Guidelines"
                elif "2024" in source:
                    source = "ISHLT 2024"
                elif "1520" in source:
                    source = "Bonser et al."

                with st.expander(f"{source} — p.{citation.page}"):
                    st.markdown(citation.text)
        else:
            st.info("No guidelines indexed. Use sidebar to index PDFs.")

        st.divider()

        # Generate referral summary and email
        st.subheader("Referral Documentation")

        # Build summary
        criteria_text = ", ".join(criteria_list) if criteria_list else "None"
        contra_text = ", ".join(contraindications) if contraindications else "None identified"

        referral_summary = f"""HEART FAILURE TRANSPLANT REFERRAL

PATIENT DETAILS
Age: {age} years | Sex: {sex}
Height: {height} cm | Weight: {weight} kg | BMI: {bmi:.1f} kg/m²
Etiology: {etiology}
NYHA Class: {nyha} | LVEF: {lvef}%
IV Inotropes: {on_inotropes}

INVESTIGATIONS
Creatinine: {creatinine} μmol/L
Bilirubin: {bilirubin} μmol/L
NT-proBNP: {bnp} pg/mL

CURRENT THERAPY
Diuretic dose: Furosemide {furosemide_dose} mg/day equivalent
Devices: {device_str if device_str else "None"}

I NEED HELP CRITERIA ({criteria_met}/9 met)
{criteria_text}

POTENTIAL CONTRAINDICATIONS
{contra_text}

CLINICAL CONCERN
{clinical_concern if clinical_concern else "Not specified"}

MEDICAL, SURGICAL AND SOCIAL HISTORY
{medical_history if medical_history else "Not specified"}

RECOMMENDATION
{"Referral recommended" if criteria_met >= 2 else "Consider referral" if criteria_met == 1 else "Optimise current therapy"}
"""

        email_body = f"""Dear Transplant Team,

I would like to refer this patient for advanced heart failure assessment.

{referral_summary}
I would be grateful if you could review this patient for suitability for advanced heart failure therapies.

Please contact me if you require any additional information.

Kind regards,
[Referring Physician]
[Hospital/Contact details]
"""

        # Display in tabs
        tab1, tab2 = st.tabs(["Summary", "Email Draft"])

        with tab1:
            st.text_area("Referral Summary", referral_summary, height=400)
            st.download_button(
                "Download Summary",
                referral_summary,
                file_name="hf_referral_summary.txt",
                mime="text/plain"
            )

        with tab2:
            st.text_area("Email to Transplant Centre", email_body, height=450)
            st.download_button(
                "Download Email",
                email_body,
                file_name="hf_referral_email.txt",
                mime="text/plain"
            )

            st.markdown("*Copy the text above and paste into your email client*")

    else:
        # Instructions when no analysis yet
        st.markdown("### How to use this tool")
        st.markdown("""
        1. Enter the patient's basic details on the left
        2. Check all applicable **I NEED HELP** criteria
        3. Add any additional clinical information
        4. Click **Check Referral Criteria**

        The tool will:
        - Assess whether referral criteria are met
        - Flag potential contraindications
        - Show historical decline rates and reasons
        - Provide relevant guideline excerpts
        - **Generate a referral summary and email draft**
        """)

        st.info("""
        **I NEED HELP** is a validated mnemonic for identifying patients
        who may benefit from referral to advanced heart failure services.
        Meeting ≥2 criteria suggests timely referral is appropriate.
        """)


# Footer
st.divider()
st.caption("For clinical decision support only. Does not replace clinical judgment. "
           "Refer to local pathways for referral process.")
