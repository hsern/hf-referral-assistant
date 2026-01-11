"""Database models for heart failure referrals."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    LargeBinary,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Referral(Base):
    """A heart failure transplant referral case."""

    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # Demographics
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sex: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    bmi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Clinical parameters
    etiology: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nyha_class: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lvef: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Left ventricular ejection fraction
    lvedd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # LV end-diastolic diameter

    # Hemodynamics
    cardiac_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pcwp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Pulmonary capillary wedge pressure
    pvr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Pulmonary vascular resistance
    mean_pap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Mean pulmonary artery pressure

    # Lab values
    creatinine: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bilirubin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sodium: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bnp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hemoglobin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Risk scores
    intermacs_profile: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hfss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Heart Failure Survival Score
    shfm_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Seattle HF Model score

    # Comorbidities and history (stored as JSON)
    comorbidities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    medications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    devices: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # ICD, CRT, etc.

    # Free text clinical summary
    clinical_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional data (flexible storage for extra columns)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Embedding for similarity search
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    # Metadata
    referral_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship to outcome
    outcome: Mapped[Optional["Outcome"]] = relationship(back_populates="referral")

    def to_text(self) -> str:
        """Convert referral to text representation for embedding."""
        parts = []
        if self.age:
            parts.append(f"Age: {self.age}")
        if self.sex:
            parts.append(f"Sex: {self.sex}")
        if self.etiology:
            parts.append(f"Etiology: {self.etiology}")
        if self.nyha_class:
            parts.append(f"NYHA Class: {self.nyha_class}")
        if self.lvef is not None:
            parts.append(f"LVEF: {self.lvef}%")
        if self.cardiac_index:
            parts.append(f"Cardiac Index: {self.cardiac_index}")
        if self.pcwp:
            parts.append(f"PCWP: {self.pcwp}")
        if self.pvr:
            parts.append(f"PVR: {self.pvr}")
        if self.creatinine:
            parts.append(f"Creatinine: {self.creatinine}")
        if self.bnp:
            parts.append(f"BNP: {self.bnp}")
        if self.intermacs_profile:
            parts.append(f"INTERMACS Profile: {self.intermacs_profile}")
        if self.comorbidities:
            parts.append(f"Comorbidities: {', '.join(self.comorbidities.keys())}")
        if self.clinical_summary:
            parts.append(f"Summary: {self.clinical_summary}")
        return ". ".join(parts)


class Outcome(Base):
    """Outcome of a referral case."""

    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    referral_id: Mapped[int] = mapped_column(ForeignKey("referrals.id"), unique=True)

    # Decision pathway
    decision: Mapped[str] = mapped_column(String(50))  # listed, declined, deferred, bridge_to_decision
    decision_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decision_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decline_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Reason if declined

    # Final outcome
    final_outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # transplanted, lvad, medical, deceased
    outcome_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Survival data
    days_on_waitlist: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    survival_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    referral: Mapped["Referral"] = relationship(back_populates="outcome")
