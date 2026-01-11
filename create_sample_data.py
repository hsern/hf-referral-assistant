#!/usr/bin/env python3
"""Generate sample referral data for testing."""

import random
from pathlib import Path
import pandas as pd

random.seed(42)

# Sample data distributions based on typical HF referral populations
ETIOLOGIES = [
    ("Dilated Cardiomyopathy", 0.35),
    ("Ischemic Cardiomyopathy", 0.40),
    ("Hypertrophic Cardiomyopathy", 0.05),
    ("Restrictive Cardiomyopathy", 0.03),
    ("Viral Cardiomyopathy", 0.05),
    ("Chemotherapy-induced", 0.04),
    ("Peripartum Cardiomyopathy", 0.02),
    ("Valvular Heart Disease", 0.04),
    ("Congenital Heart Disease", 0.02),
]

DECISIONS = [
    ("listed", 0.45),
    ("declined", 0.25),
    ("deferred", 0.15),
    ("bridge_to_decision", 0.10),
    ("palliative", 0.05),
]

FINAL_OUTCOMES = [
    ("transplanted", 0.50),
    ("lvad", 0.25),
    ("medical_management", 0.15),
    ("deceased", 0.10),
]

# Decline reasons with weights
DECLINE_REASONS = [
    ("illicit_drug_use", 0.15),
    ("high_bmi", 0.12),
    ("frailty", 0.15),
    ("multi_organ_failure", 0.18),
    ("malignancy", 0.12),
    ("psychosocial", 0.10),
    ("adverse_pvr", 0.10),
    ("other", 0.08),
]

DEVICES = ["None", "ICD", "CRT-D", "CRT-P", "Pacemaker", "LVAD"]

COMORBIDITIES = [
    "Diabetes", "Hypertension", "Atrial Fibrillation", "COPD",
    "Chronic Kidney Disease", "Prior Stroke", "Peripheral Vascular Disease",
    "Obesity", "Sleep Apnea", "Depression", "Prior Malignancy"
]


def weighted_choice(options):
    """Choose from weighted options."""
    items, weights = zip(*options)
    return random.choices(items, weights=weights, k=1)[0]


def generate_referral(case_num: int) -> dict:
    """Generate a single referral case."""
    age = random.gauss(55, 12)
    age = max(18, min(75, int(age)))

    sex = random.choice(["M", "F"])
    if sex == "M":
        bmi = random.gauss(28, 5)
    else:
        bmi = random.gauss(27, 5)
    bmi = max(16, min(45, round(bmi, 1)))

    etiology = weighted_choice(ETIOLOGIES)

    # NYHA class - skewed toward III/IV for transplant referrals
    nyha = random.choices([2, 3, 4], weights=[0.1, 0.5, 0.4], k=1)[0]

    # LVEF - typically low for transplant candidates
    lvef = random.gauss(20, 8)
    lvef = max(5, min(40, int(lvef)))

    # Hemodynamics
    cardiac_index = round(random.gauss(1.9, 0.4), 2)
    cardiac_index = max(1.0, min(3.0, cardiac_index))

    pcwp = random.gauss(24, 8)
    pcwp = max(8, min(40, int(pcwp)))

    # PVR - important for transplant eligibility
    pvr = random.gauss(3.0, 1.5)
    pvr = max(0.5, min(8, round(pvr, 1)))

    mean_pap = random.gauss(35, 10)
    mean_pap = max(15, min(60, int(mean_pap)))

    # Labs
    creatinine = random.gauss(1.4, 0.5)
    creatinine = max(0.6, min(4.0, round(creatinine, 2)))

    bilirubin = random.gauss(1.2, 0.8)
    bilirubin = max(0.3, min(5.0, round(bilirubin, 2)))

    sodium = random.gauss(136, 4)
    sodium = max(125, min(145, int(sodium)))

    bnp = random.gauss(2000, 1500)
    bnp = max(100, min(10000, int(bnp)))

    hemoglobin = random.gauss(12, 2)
    hemoglobin = max(7, min(16, round(hemoglobin, 1)))

    # INTERMACS profile
    intermacs = random.choices([1, 2, 3, 4, 5, 6, 7],
                                weights=[0.05, 0.15, 0.25, 0.25, 0.15, 0.10, 0.05], k=1)[0]

    # Device
    device = random.choice(DEVICES)

    # Comorbidities (0-4 conditions)
    num_comorbidities = random.choices([0, 1, 2, 3, 4], weights=[0.1, 0.25, 0.35, 0.2, 0.1], k=1)[0]
    patient_comorbidities = random.sample(COMORBIDITIES, num_comorbidities)

    # Decision based on risk factors
    base_decision = weighted_choice(DECISIONS)

    # Adjust decision based on risk factors
    if pvr > 5 or creatinine > 2.5 or bmi > 38:
        if random.random() < 0.6:
            base_decision = random.choice(["declined", "deferred", "bridge_to_decision"])

    # Decline reason (only for declined cases)
    decline_reason = None
    if base_decision == "declined":
        # Make decline reason correlate with patient characteristics
        if bmi > 35:
            decline_reason = "high_bmi" if random.random() < 0.7 else weighted_choice(DECLINE_REASONS)
        elif pvr > 5:
            decline_reason = "adverse_pvr" if random.random() < 0.7 else weighted_choice(DECLINE_REASONS)
        elif creatinine > 2.5 or bilirubin > 3:
            decline_reason = "multi_organ_failure" if random.random() < 0.6 else weighted_choice(DECLINE_REASONS)
        elif age > 68:
            decline_reason = "frailty" if random.random() < 0.5 else weighted_choice(DECLINE_REASONS)
        elif "Prior Malignancy" in patient_comorbidities:
            decline_reason = "malignancy" if random.random() < 0.7 else weighted_choice(DECLINE_REASONS)
        else:
            decline_reason = weighted_choice(DECLINE_REASONS)

    # Final outcome (only for listed/bridge patients)
    final_outcome = None
    if base_decision in ["listed", "bridge_to_decision"]:
        final_outcome = weighted_choice(FINAL_OUTCOMES)
    elif base_decision == "declined":
        if random.random() < 0.3:
            final_outcome = "deceased"
        else:
            final_outcome = "medical_management"

    # Generate clinical summary
    summaries = [
        f"{age}yo {sex} with {etiology.lower()}, NYHA class {nyha}",
        f"Referred for advanced HF therapy evaluation",
        f"LVEF {lvef}%, on optimal medical therapy",
    ]
    if pvr > 4:
        summaries.append("Elevated PVR requiring vasodilator challenge")
    if creatinine > 2:
        summaries.append("Concern for cardiorenal syndrome")
    if intermacs <= 3:
        summaries.append("Inotrope dependent")
    if device == "LVAD":
        summaries.append("Currently on LVAD support as bridge to transplant")

    clinical_summary = ". ".join(summaries) + "."

    # Decision rationale
    rationales = {
        "listed": "Meets criteria for transplant listing. Acceptable end-organ function and psychosocial support.",
        "declined": f"Does not meet transplant criteria. Primary reason: {decline_reason.replace('_', ' ') if decline_reason else 'unspecified'}.",
        "deferred": "Requires optimization of medical therapy and reassessment.",
        "bridge_to_decision": "Listed for MCS as bridge to transplant candidacy.",
        "palliative": "Focus on comfort care and quality of life per patient preference.",
    }

    return {
        "case_id": f"HF-{case_num:04d}",
        "age": age,
        "sex": sex,
        "bmi": bmi,
        "etiology": etiology,
        "nyha_class": nyha,
        "lvef": lvef,
        "cardiac_index": cardiac_index,
        "pcwp": pcwp,
        "pvr": pvr,
        "mean_pap": mean_pap,
        "creatinine": creatinine,
        "bilirubin": bilirubin,
        "sodium": sodium,
        "bnp": bnp,
        "hemoglobin": hemoglobin,
        "intermacs_profile": intermacs,
        "device": device,
        "comorbidities": ", ".join(patient_comorbidities) if patient_comorbidities else None,
        "clinical_summary": clinical_summary,
        "decision": base_decision,
        "decline_reason": decline_reason,
        "decision_rationale": rationales.get(base_decision),
        "final_outcome": final_outcome,
    }


def main():
    # Generate 200 sample cases
    cases = [generate_referral(i + 1) for i in range(200)]

    df = pd.DataFrame(cases)

    output_path = Path("data/referrals/sample_referrals.xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(output_path, index=False)

    print(f"Generated {len(cases)} sample referrals")
    print(f"Saved to: {output_path}")
    print(f"\nSample distribution:")
    print(f"  Decisions: {df['decision'].value_counts().to_dict()}")
    print(f"  Etiologies: {df['etiology'].value_counts().head(5).to_dict()}")
    print(f"  Age range: {df['age'].min()} - {df['age'].max()}")
    print(f"  LVEF range: {df['lvef'].min()} - {df['lvef'].max()}%")

    # Show decline reasons
    declined = df[df['decision'] == 'declined']
    if len(declined) > 0:
        print(f"\nDecline reasons ({len(declined)} cases):")
        print(f"  {declined['decline_reason'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
