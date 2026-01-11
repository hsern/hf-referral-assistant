"""Find similar referral cases using embeddings."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from src.database import Referral, Outcome, get_session, init_db
from src.indexer.embeddings import (
    embed_text,
    embed_texts,
    embedding_to_bytes,
    bytes_to_embedding,
    cosine_similarity_matrix,
)
from src.config import TOP_K_SIMILAR_CASES, DB_PATH


@dataclass
class SimilarCase:
    """A similar case with its details."""

    referral: Referral
    outcome: Optional[Outcome]
    similarity: float


def generate_referral_embeddings(db_path: str = str(DB_PATH)) -> int:
    """
    Generate embeddings for all referrals that don't have them.

    Returns:
        Number of embeddings generated
    """
    init_db(db_path)
    session = get_session(db_path)

    # Get referrals without embeddings
    referrals = session.query(Referral).filter(Referral.embedding.is_(None)).all()

    if not referrals:
        print("All referrals already have embeddings.")
        session.close()
        return 0

    print(f"Generating embeddings for {len(referrals)} referrals...")

    # Generate text representations
    texts = [r.to_text() for r in referrals]

    # Generate embeddings in batch
    embeddings = embed_texts(texts)

    # Store embeddings
    for referral, embedding in zip(referrals, embeddings):
        referral.embedding = embedding_to_bytes(embedding)

    session.commit()
    session.close()

    print(f"Generated {len(referrals)} embeddings.")
    return len(referrals)


def find_similar_cases(
    query_referral: Referral | dict | str,
    top_k: int = TOP_K_SIMILAR_CASES,
    exclude_id: Optional[int] = None,
    db_path: str = str(DB_PATH),
) -> list[SimilarCase]:
    """
    Find similar cases to a given referral.

    Args:
        query_referral: Referral object, dict with referral data, or text description
        top_k: Number of similar cases to return
        exclude_id: Referral ID to exclude (e.g., the query referral itself)
        db_path: Path to database

    Returns:
        List of SimilarCase objects sorted by similarity
    """
    session = get_session(db_path)

    # Generate query embedding
    if isinstance(query_referral, str):
        query_text = query_referral
    elif isinstance(query_referral, dict):
        # Build text from dict
        parts = []
        for key, val in query_referral.items():
            if val is not None:
                parts.append(f"{key}: {val}")
        query_text = ". ".join(parts)
    else:
        query_text = query_referral.to_text()

    query_embedding = embed_text(query_text)

    # Get all referrals with embeddings
    query = session.query(Referral).filter(Referral.embedding.isnot(None))
    if exclude_id:
        query = query.filter(Referral.id != exclude_id)

    referrals = query.all()

    if not referrals:
        session.close()
        return []

    # Build embedding matrix
    embeddings = np.vstack([bytes_to_embedding(r.embedding) for r in referrals])

    # Compute similarities
    similarities = cosine_similarity_matrix(query_embedding, embeddings)

    # Get top-k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Build results
    results = []
    for idx in top_indices:
        referral = referrals[idx]
        outcome = session.query(Outcome).filter_by(referral_id=referral.id).first()
        results.append(
            SimilarCase(
                referral=referral,
                outcome=outcome,
                similarity=float(similarities[idx]),
            )
        )

    session.close()
    return results


def get_outcome_distribution(cases: list[SimilarCase]) -> dict:
    """
    Analyze outcome distribution from similar cases.

    Args:
        cases: List of similar cases

    Returns:
        Dictionary with outcome statistics
    """
    decisions = {}
    final_outcomes = {}
    total_with_outcome = 0

    for case in cases:
        if case.outcome:
            total_with_outcome += 1
            decision = case.outcome.decision
            decisions[decision] = decisions.get(decision, 0) + 1

            if case.outcome.final_outcome:
                final = case.outcome.final_outcome
                final_outcomes[final] = final_outcomes.get(final, 0) + 1

    return {
        "total_cases": len(cases),
        "cases_with_outcome": total_with_outcome,
        "decision_distribution": decisions,
        "final_outcome_distribution": final_outcomes,
    }
