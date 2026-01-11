"""Index for storing and searching guideline chunks."""

import json
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import numpy as np

from .pdf_parser import PDFChunk, process_guidelines_directory
from .embeddings import embed_texts, cosine_similarity_matrix, embed_text
from src.config import INDEX_PATH, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_GUIDELINE_CHUNKS


class GuidelineIndex:
    """Vector index for guideline chunks."""

    def __init__(self, index_path: str | Path = INDEX_PATH):
        self.index_path = Path(index_path)
        self.chunks: list[PDFChunk] = []
        self.embeddings: Optional[np.ndarray] = None

    def build(
        self,
        guidelines_dir: str | Path,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> dict:
        """
        Build index from PDF files in directory.

        Args:
            guidelines_dir: Directory containing PDF guidelines
            chunk_size: Size of text chunks
            overlap: Overlap between chunks

        Returns:
            Statistics about the indexing
        """
        guidelines_dir = Path(guidelines_dir)

        # Process all PDFs
        print(f"Processing PDFs in {guidelines_dir}...")
        self.chunks = process_guidelines_directory(guidelines_dir, chunk_size, overlap)

        if not self.chunks:
            return {"error": "No chunks extracted from PDFs"}

        # Generate embeddings
        print(f"\nGenerating embeddings for {len(self.chunks)} chunks...")
        texts = [chunk.text for chunk in self.chunks]
        self.embeddings = embed_texts(texts)

        # Get stats by source
        sources = {}
        for chunk in self.chunks:
            sources[chunk.source] = sources.get(chunk.source, 0) + 1

        stats = {
            "total_chunks": len(self.chunks),
            "embedding_dim": self.embeddings.shape[1],
            "sources": sources,
        }

        return stats

    def save(self) -> None:
        """Save index to disk."""
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Save chunks metadata
        chunks_data = [asdict(chunk) for chunk in self.chunks]
        with open(self.index_path / "chunks.json", "w") as f:
            json.dump(chunks_data, f)

        # Save embeddings
        if self.embeddings is not None:
            np.save(self.index_path / "embeddings.npy", self.embeddings)

        print(f"Index saved to {self.index_path}")

    def load(self) -> bool:
        """Load index from disk. Returns True if successful."""
        chunks_path = self.index_path / "chunks.json"
        embeddings_path = self.index_path / "embeddings.npy"

        if not chunks_path.exists() or not embeddings_path.exists():
            return False

        with open(chunks_path) as f:
            chunks_data = json.load(f)
            self.chunks = [PDFChunk(**data) for data in chunks_data]

        self.embeddings = np.load(embeddings_path)

        return True

    def search(
        self,
        query: str,
        top_k: int = TOP_K_GUIDELINE_CHUNKS,
        source_filter: Optional[str] = None,
    ) -> list[tuple[PDFChunk, float]]:
        """
        Search for relevant guideline chunks.

        Args:
            query: Search query text
            top_k: Number of results to return
            source_filter: Optional filter by PDF source name

        Returns:
            List of (chunk, similarity_score) tuples
        """
        if self.embeddings is None or not self.chunks:
            raise ValueError("Index not loaded. Call load() or build() first.")

        # Generate query embedding
        query_embedding = embed_text(query)

        # Compute similarities
        similarities = cosine_similarity_matrix(query_embedding, self.embeddings)

        # Apply source filter if specified
        if source_filter:
            mask = np.array([source_filter.lower() in c.source.lower() for c in self.chunks])
            similarities = np.where(mask, similarities, -1)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Skip filtered out results
                results.append((self.chunks[idx], float(similarities[idx])))

        return results

    def search_by_topic(
        self,
        topics: list[str],
        top_k: int = TOP_K_GUIDELINE_CHUNKS,
    ) -> list[tuple[PDFChunk, float, str]]:
        """
        Search for chunks relevant to multiple topics.

        Args:
            topics: List of topic strings to search for
            top_k: Number of results per topic

        Returns:
            List of (chunk, score, matched_topic) tuples, deduplicated
        """
        seen_chunks = set()
        results = []

        for topic in topics:
            topic_results = self.search(topic, top_k=top_k)
            for chunk, score in topic_results:
                chunk_key = (chunk.source, chunk.page, chunk.chunk_id)
                if chunk_key not in seen_chunks:
                    seen_chunks.add(chunk_key)
                    results.append((chunk, score, topic))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        return results


def build_guideline_index(
    guidelines_dir: str | Path,
    index_path: str | Path = INDEX_PATH,
) -> GuidelineIndex:
    """
    Build and save a guideline index.

    Args:
        guidelines_dir: Directory containing PDF guidelines
        index_path: Where to save the index

    Returns:
        The built GuidelineIndex
    """
    index = GuidelineIndex(index_path)
    stats = index.build(guidelines_dir)

    print(f"\nIndex statistics:")
    print(f"  Total chunks: {stats.get('total_chunks', 0)}")
    print(f"  Embedding dimension: {stats.get('embedding_dim', 0)}")
    print(f"  Sources:")
    for source, count in stats.get("sources", {}).items():
        print(f"    - {source}: {count} chunks")

    index.save()
    return index


def load_guideline_index(index_path: str | Path = INDEX_PATH) -> GuidelineIndex:
    """Load an existing guideline index."""
    index = GuidelineIndex(index_path)
    if not index.load():
        raise FileNotFoundError(f"No index found at {index_path}")
    return index
