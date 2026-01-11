# Advanced Heart Failure Referral Assistant

A clinical decision support tool for heart failure physicians considering referral to advanced HF/transplant services. The app assesses referral criteria using the **I NEED HELP** mnemonic, shows historical outcomes from similar cases, and generates referral documentation.

## Features

- **I NEED HELP criteria assessment** - Auto-populated from patient data
- **Similar case matching** - Shows decline rates and reasons from historical referrals
- **Guideline citations** - Retrieves relevant sections from uploaded clinical guidelines
- **Referral documentation** - Generates summary and email draft for transplant team

---

## Quick Start (Streamlit Cloud)

If using the hosted version, you'll need to upload your data files via the sidebar.

---

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/hsern/hf-referral-assistant.git
cd hf-referral-assistant
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## Setting Up Your Data

### Step 1: Upload Referral Data (Excel)

1. Prepare an Excel file (`.xlsx`) with your anonymised referral data
2. Place it in the `data/referrals/` folder
3. The app will auto-detect and prompt you to import

**Required columns** (the app auto-maps common column names):

| Field | Example Column Names |
|-------|---------------------|
| Case ID | `case_id`, `patient_id`, `id` |
| Age | `age`, `age_years` |
| Sex | `sex`, `gender` |
| Etiology | `etiology`, `diagnosis`, `aetiology` |
| NYHA Class | `nyha`, `nyha_class` |
| LVEF | `lvef`, `ef`, `ejection_fraction` |
| Creatinine | `creatinine`, `cr` |
| BNP | `bnp`, `nt_probnp` |
| Decision | `decision`, `outcome_decision` |
| Decline Reason | `decline_reason` |

**Decline reason values** (for the chart):
- `illicit_drug_use`
- `high_bmi`
- `frailty`
- `multi_organ_failure`
- `malignancy`
- `psychosocial`
- `adverse_pvr`
- `other`

### Step 2: Upload Clinical Guidelines (PDF)

1. Place your PDF guidelines in the `data/guidelines/` folder
2. The app will auto-detect and prompt you to index

**Supported guidelines:**
- ESC Heart Failure Guidelines
- ISHLT Guidelines
- Any other relevant PDF documents

### Step 3: Import Data via Sidebar

1. Open the app in your browser
2. Check the **sidebar** on the left
3. If data needs importing:
   - Click **"Index Guidelines"** for PDFs
   - Select Excel file and click **"Import Data"** for referrals
4. Wait for processing to complete (may take a few minutes for large files)

---

## Using the App

### 1. Enter Patient Details

Fill in the left panel:
- Demographics (age, sex, height, weight)
- Etiology and NYHA class
- LVEF (auto-ticks I NEED HELP if ≤35%)
- IV Inotropes status
- Lab values (creatinine, bilirubin, NT-proBNP)
- Diuretic dose
- Clinical concern and medical history

### 2. Review I NEED HELP Criteria

The app auto-populates criteria based on:
- **LVEF ≤35%** → EF criterion ticked
- **NYHA IIIb/IV** → NYHA criterion ticked
- **IV Inotropes = Yes** → Inotropes criterion ticked

Manually tick any additional criteria that apply.

### 3. Click "Check Referral Criteria"

The app displays:
- **Referral recommendation** (based on criteria count)
- **Contraindications** (if any)
- **Historical decline rate** from similar cases
- **Reasons for decline** chart
- **Relevant guideline citations**

### 4. Generate Referral Documentation

Scroll down to find:
- **Summary tab** - Structured referral summary
- **Email tab** - Ready-to-send email draft

Click **Download** to save as text file.

---

## Data Privacy

- Patient data is stored **locally only** in `data/referrals.db`
- Excel files and PDFs are **not uploaded** to any external server
- The `.gitignore` excludes all patient data from version control

---

## Updating Data

The app auto-detects when files change:

| Change | Action |
|--------|--------|
| New/modified Excel file | Sidebar shows warning → Click "Import Data" |
| New/modified PDF | Sidebar shows warning → Click "Index Guidelines" |

---

## File Structure

```
hf-referral-assistant/
├── app.py                 # Main Streamlit app
├── data/
│   ├── referrals/         # Place Excel files here
│   ├── guidelines/        # Place PDF files here
│   ├── referrals.db       # SQLite database (auto-created)
│   └── guidelines_index/  # Vector index (auto-created)
├── src/
│   ├── database/          # Data models and loading
│   ├── indexer/           # PDF parsing and embeddings
│   ├── retrieval/         # Similar case and guideline search
│   └── predictor/         # Outcome suggestion logic
└── requirements.txt
```

---

## Troubleshooting

**"No similar cases found"**
- Ensure Excel data has been imported (check sidebar)
- Verify the Excel file has the required columns

**"No guidelines indexed"**
- Place PDF files in `data/guidelines/`
- Click "Index Guidelines" in sidebar

**Slow performance**
- First run downloads the embedding model (~90MB)
- Subsequent runs are faster

---

## Disclaimer

This tool is for **clinical decision support only**. It does not replace clinical judgment. Always refer to local pathways and guidelines for referral decisions.

---

## License

MIT License
