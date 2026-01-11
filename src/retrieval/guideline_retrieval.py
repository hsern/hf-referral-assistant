"""Retrieve relevant guideline citations for a referral."""

from dataclasses import dataclass
from typing import Optional

from src.database import Referral
from src.indexer import GuidelineIndex, load_guideline_index, PDFChunk
from src.config import INDEX_PATH, TOP_K_GUIDELINE_CHUNKS


@dataclass
class GuidelineCitation:
    """A citation from the clinical guidelines."""

    text: str
    source: str
    page: int
    section: Optional[str]
    relevance_score: float
    matched_topic: Optional[str] = None

    def format(self) -> str:
        """Format citation for display."""
        source_short = self.source.replace(".pdf", "")
        section_str = f" - {self.section}" if self.section else ""
        return f"[{source_short}, p.{self.page}{section_str}]\n{self.text}"


def extract_clinical_topics(referral: Referral | dict) -> list[str]:
    """
    Extract searchable clinical topics from a referral.

    Args:
        referral: Referral object or dict

    Returns:
        List of topic strings to search for
    """
    topics = []

    if isinstance(referral, dict):
        data = referral
    else:
        data = {
            "etiology": referral.etiology,
            "nyha_class": referral.nyha_class,
            "lvef": referral.lvef,
            "pvr": referral.pvr,
            "pcwp": referral.pcwp,
            "intermacs_profile": referral.intermacs_profile,
            "creatinine": referral.creatinine,
            "age": referral.age,
            "bmi": referral.bmi,
            "comorbidities": referral.comorbidities,
            "devices": referral.devices,
        }

    # Add etiology-specific topics
    if data.get("etiology"):
        etiology = data["etiology"].lower()
        topics.append(f"heart failure {etiology}")
        if "ischemic" in etiology or "icm" in etiology:
            topics.append("ischemic cardiomyopathy transplant criteria")
        elif "dilated" in etiology or "dcm" in etiology:
            topics.append("dilated cardiomyopathy transplant listing")
        elif "hypertrophic" in etiology or "hcm" in etiology:
            topics.append("hypertrophic cardiomyopathy transplant")

    # NYHA class considerations
    if data.get("nyha_class"):
        nyha = data["nyha_class"]
        if nyha >= 3:
            topics.append("NYHA class III IV heart failure prognosis")
            topics.append("advanced heart failure management")

    # Hemodynamic considerations
    if data.get("pvr"):
        pvr = data["pvr"]
        if pvr > 3:
            topics.append("pulmonary vascular resistance transplant")
            topics.append("pulmonary hypertension heart transplant contraindication")
        if pvr > 5:
            topics.append("fixed pulmonary hypertension")

    if data.get("pcwp"):
        pcwp = data["pcwp"]
        if pcwp > 20:
            topics.append("elevated filling pressures heart failure")

    # INTERMACS profile
    if data.get("intermacs_profile"):
        profile = data["intermacs_profile"]
        topics.append(f"INTERMACS profile {profile}")
        if profile <= 3:
            topics.append("mechanical circulatory support indication")
            topics.append("urgent heart transplant listing")

    # Renal function
    if data.get("creatinine"):
        cr = data["creatinine"]
        if cr > 2.0:
            topics.append("renal dysfunction heart transplant")
            topics.append("cardiorenal syndrome")

    # Age considerations
    if data.get("age"):
        age = data["age"]
        if age > 65:
            topics.append("elderly heart transplant candidate")
            topics.append("age criteria cardiac transplantation")
        if age > 70:
            topics.append("heart transplant age limit contraindication")

    # BMI considerations
    if data.get("bmi"):
        bmi = data["bmi"]
        if bmi > 35:
            topics.append("obesity heart transplant contraindication")
            topics.append("BMI criteria transplant listing")
        if bmi < 18:
            topics.append("cachexia heart failure prognosis")

    # Device therapy
    if data.get("devices"):
        devices = str(data["devices"]).lower()
        if "lvad" in devices or "vad" in devices:
            topics.append("LVAD bridge to transplant")
            topics.append("ventricular assist device outcomes")
        if "icd" in devices:
            topics.append("ICD heart failure")
        if "crt" in devices:
            topics.append("cardiac resynchronization therapy")

    # Comorbidities
    if data.get("comorbidities"):
        comorbidities = data["comorbidities"]
        if isinstance(comorbidities, dict):
            for condition in comorbidities.keys():
                condition_lower = condition.lower()
                if "diabet" in condition_lower:
                    topics.append("diabetes heart transplant")
                if "renal" in condition_lower or "kidney" in condition_lower:
                    topics.append("renal insufficiency transplant contraindication")
                if "stroke" in condition_lower or "cva" in condition_lower:
                    topics.append("prior stroke transplant eligibility")
                if "malignan" in condition_lower or "cancer" in condition_lower:
                    topics.append("malignancy heart transplant contraindication")
                if "smok" in condition_lower or "tobacco" in condition_lower:
                    topics.append("smoking cessation transplant requirement")

    # General transplant topics
    topics.append("heart transplant indication")
    topics.append("transplant listing criteria")

    return topics


def get_guideline_citations(
    referral: Referral | dict | str,
    index: Optional[GuidelineIndex] = None,
    top_k: int = TOP_K_GUIDELINE_CHUNKS,
    index_path: str = str(INDEX_PATH),
) -> list[GuidelineCitation]:
    """
    Get relevant guideline citations for a referral.

    Args:
        referral: Referral object, dict, or text description
        index: Pre-loaded GuidelineIndex (will load from disk if not provided)
        top_k: Number of citations to return
        index_path: Path to guideline index

    Returns:
        List of GuidelineCitation objects
    """
    # Load index if not provided
    if index is None:
        index = load_guideline_index(index_path)

    # Handle text input
    if isinstance(referral, str):
        results = index.search(referral, top_k=top_k)
        return [
            GuidelineCitation(
                text=chunk.text,
                source=chunk.source,
                page=chunk.page,
                section=chunk.section,
                relevance_score=score,
            )
            for chunk, score in results
        ]

    # Extract topics from referral
    topics = extract_clinical_topics(referral)

    # Search for each topic
    results = index.search_by_topic(topics, top_k=2)  # 2 per topic

    # Convert to citations
    citations = []
    seen_texts = set()  # Deduplicate by text content

    for chunk, score, topic in results:
        # Skip near-duplicates
        text_key = chunk.text[:100]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        citations.append(
            GuidelineCitation(
                text=chunk.text,
                source=chunk.source,
                page=chunk.page,
                section=chunk.section,
                relevance_score=score,
                matched_topic=topic,
            )
        )

        if len(citations) >= top_k:
            break

    return citations
