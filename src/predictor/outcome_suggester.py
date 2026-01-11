"""Suggest likely outcome pathway based on similar cases and guidelines."""

from dataclasses import dataclass, field
from typing import Optional

from src.database import Referral
from src.retrieval.case_search import find_similar_cases, SimilarCase, get_outcome_distribution
from src.retrieval.guideline_retrieval import get_guideline_citations, GuidelineCitation
from src.indexer import GuidelineIndex
from src.config import TOP_K_SIMILAR_CASES, TOP_K_GUIDELINE_CHUNKS


@dataclass
class OutcomeSuggestion:
    """Suggested outcome pathway with supporting evidence."""

    # Primary suggestion
    suggested_decision: str
    confidence: float  # 0-1 based on agreement among similar cases

    # Supporting evidence
    similar_cases: list[SimilarCase] = field(default_factory=list)
    guideline_citations: list[GuidelineCitation] = field(default_factory=list)

    # Outcome distribution from similar cases
    outcome_distribution: dict = field(default_factory=dict)

    # Risk factors and considerations
    risk_factors: list[str] = field(default_factory=list)
    favorable_factors: list[str] = field(default_factory=list)

    # Alternative pathways
    alternative_decisions: list[tuple[str, float]] = field(default_factory=list)

    def format_summary(self) -> str:
        """Format a summary of the suggestion."""
        lines = []

        lines.append(f"SUGGESTED PATHWAY: {self.suggested_decision.upper()}")
        lines.append(f"Confidence: {self.confidence:.0%}")
        lines.append("")

        # Outcome distribution
        if self.outcome_distribution.get("decision_distribution"):
            lines.append("Similar Case Decisions:")
            for decision, count in self.outcome_distribution["decision_distribution"].items():
                pct = count / self.outcome_distribution["cases_with_outcome"] * 100
                lines.append(f"  - {decision}: {count} ({pct:.0f}%)")
            lines.append("")

        # Risk factors
        if self.risk_factors:
            lines.append("Risk Factors:")
            for factor in self.risk_factors:
                lines.append(f"  - {factor}")
            lines.append("")

        # Favorable factors
        if self.favorable_factors:
            lines.append("Favorable Factors:")
            for factor in self.favorable_factors:
                lines.append(f"  + {factor}")
            lines.append("")

        # Alternatives
        if self.alternative_decisions:
            lines.append("Alternative Pathways to Consider:")
            for decision, prob in self.alternative_decisions:
                lines.append(f"  - {decision}: {prob:.0%} of similar cases")
            lines.append("")

        return "\n".join(lines)

    def format_citations(self) -> str:
        """Format guideline citations."""
        if not self.guideline_citations:
            return "No guideline citations available."

        lines = ["RELEVANT GUIDELINE CITATIONS:", ""]
        for i, citation in enumerate(self.guideline_citations, 1):
            lines.append(f"{i}. {citation.format()}")
            if citation.matched_topic:
                lines.append(f"   (Matched: {citation.matched_topic})")
            lines.append("")

        return "\n".join(lines)

    def format_similar_cases(self) -> str:
        """Format similar case summaries."""
        if not self.similar_cases:
            return "No similar cases found."

        lines = ["SIMILAR CASES:", ""]
        for i, case in enumerate(self.similar_cases, 1):
            r = case.referral
            lines.append(f"{i}. Case {r.case_id} (similarity: {case.similarity:.2f})")
            lines.append(f"   Age: {r.age}, NYHA: {r.nyha_class}, LVEF: {r.lvef}%")
            if r.etiology:
                lines.append(f"   Etiology: {r.etiology}")
            if case.outcome:
                lines.append(f"   Decision: {case.outcome.decision}")
                if case.outcome.final_outcome:
                    lines.append(f"   Final Outcome: {case.outcome.final_outcome}")
                if case.outcome.decision_rationale:
                    lines.append(f"   Rationale: {case.outcome.decision_rationale[:100]}...")
            lines.append("")

        return "\n".join(lines)


def identify_risk_factors(referral: Referral | dict) -> tuple[list[str], list[str]]:
    """
    Identify risk and favorable factors from referral data.

    Returns:
        Tuple of (risk_factors, favorable_factors)
    """
    risks = []
    favorable = []

    if isinstance(referral, dict):
        data = referral
    else:
        data = {
            "age": referral.age,
            "bmi": referral.bmi,
            "lvef": referral.lvef,
            "pvr": referral.pvr,
            "creatinine": referral.creatinine,
            "bilirubin": referral.bilirubin,
            "intermacs_profile": referral.intermacs_profile,
            "nyha_class": referral.nyha_class,
            "sodium": referral.sodium,
        }

    # Age
    if data.get("age"):
        if data["age"] > 70:
            risks.append(f"Advanced age ({data['age']} years)")
        elif data["age"] > 65:
            risks.append(f"Age >65 ({data['age']} years)")
        elif data["age"] < 65:
            favorable.append(f"Age <65 ({data['age']} years)")

    # BMI
    if data.get("bmi"):
        if data["bmi"] > 35:
            risks.append(f"Obesity (BMI {data['bmi']:.1f})")
        elif data["bmi"] > 30:
            risks.append(f"Elevated BMI ({data['bmi']:.1f})")
        elif 18 <= data["bmi"] <= 30:
            favorable.append(f"Acceptable BMI ({data['bmi']:.1f})")
        elif data["bmi"] < 18:
            risks.append(f"Cachexia (BMI {data['bmi']:.1f})")

    # PVR
    if data.get("pvr"):
        if data["pvr"] > 5:
            risks.append(f"Severe pulmonary hypertension (PVR {data['pvr']:.1f})")
        elif data["pvr"] > 3:
            risks.append(f"Elevated PVR ({data['pvr']:.1f} Wood units)")
        elif data["pvr"] <= 3:
            favorable.append(f"Acceptable PVR ({data['pvr']:.1f})")

    # Creatinine
    if data.get("creatinine"):
        if data["creatinine"] > 2.5:
            risks.append(f"Significant renal dysfunction (Cr {data['creatinine']:.1f})")
        elif data["creatinine"] > 2.0:
            risks.append(f"Renal impairment (Cr {data['creatinine']:.1f})")
        elif data["creatinine"] <= 1.5:
            favorable.append(f"Preserved renal function (Cr {data['creatinine']:.1f})")

    # Bilirubin
    if data.get("bilirubin"):
        if data["bilirubin"] > 2.0:
            risks.append(f"Hepatic congestion (Bili {data['bilirubin']:.1f})")

    # INTERMACS
    if data.get("intermacs_profile"):
        profile = data["intermacs_profile"]
        if profile <= 2:
            risks.append(f"Critical status (INTERMACS {profile})")
        elif profile <= 3:
            risks.append(f"Declining on inotropes (INTERMACS {profile})")
        elif profile >= 5:
            favorable.append(f"Ambulatory status (INTERMACS {profile})")

    # Sodium
    if data.get("sodium"):
        if data["sodium"] < 130:
            risks.append(f"Hyponatremia (Na {data['sodium']:.0f})")
        elif data["sodium"] >= 135:
            favorable.append(f"Normal sodium ({data['sodium']:.0f})")

    return risks, favorable


def suggest_outcome(
    referral: Referral | dict,
    guideline_index: Optional[GuidelineIndex] = None,
    top_k_cases: int = TOP_K_SIMILAR_CASES,
    top_k_citations: int = TOP_K_GUIDELINE_CHUNKS,
    db_path: Optional[str] = None,
) -> OutcomeSuggestion:
    """
    Generate outcome suggestion for a referral.

    Args:
        referral: Referral object or dict with referral data
        guideline_index: Pre-loaded guideline index
        top_k_cases: Number of similar cases to retrieve
        top_k_citations: Number of guideline citations to retrieve
        db_path: Path to database

    Returns:
        OutcomeSuggestion with prediction and supporting evidence
    """
    # Find similar cases
    kwargs = {"top_k": top_k_cases}
    if db_path:
        kwargs["db_path"] = db_path
    if isinstance(referral, Referral):
        kwargs["exclude_id"] = referral.id

    similar_cases = find_similar_cases(referral, **kwargs)

    # Get outcome distribution
    outcome_dist = get_outcome_distribution(similar_cases)

    # Determine suggested decision
    decisions = outcome_dist.get("decision_distribution", {})
    if decisions:
        # Find most common decision
        sorted_decisions = sorted(decisions.items(), key=lambda x: x[1], reverse=True)
        suggested_decision = sorted_decisions[0][0]
        top_count = sorted_decisions[0][1]
        total = outcome_dist["cases_with_outcome"]
        confidence = top_count / total if total > 0 else 0

        # Get alternatives
        alternatives = [(d, c / total) for d, c in sorted_decisions[1:] if c / total >= 0.1]
    else:
        suggested_decision = "insufficient_data"
        confidence = 0
        alternatives = []

    # Get guideline citations
    try:
        citations = get_guideline_citations(
            referral,
            index=guideline_index,
            top_k=top_k_citations,
        )
    except FileNotFoundError:
        citations = []

    # Identify risk factors
    risk_factors, favorable_factors = identify_risk_factors(referral)

    return OutcomeSuggestion(
        suggested_decision=suggested_decision,
        confidence=confidence,
        similar_cases=similar_cases,
        guideline_citations=citations,
        outcome_distribution=outcome_dist,
        risk_factors=risk_factors,
        favorable_factors=favorable_factors,
        alternative_decisions=alternatives,
    )
