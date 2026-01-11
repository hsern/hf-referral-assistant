"""Parse PDF guidelines and extract text with metadata."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import fitz  # pymupdf


@dataclass
class PDFChunk:
    """A chunk of text from a PDF with source metadata."""

    text: str
    source: str  # PDF filename
    page: int
    chunk_id: int
    section: str | None = None


def extract_text_from_pdf(pdf_path: str | Path) -> list[tuple[int, str]]:
    """
    Extract text from PDF, returning list of (page_number, text) tuples.
    """
    pdf_path = Path(pdf_path)
    pages = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            # Clean up text
            text = re.sub(r"\n{3,}", "\n\n", text)  # Reduce excessive newlines
            text = re.sub(r" {2,}", " ", text)  # Reduce multiple spaces
            pages.append((page_num, text.strip()))

    return pages


def detect_section_header(text: str) -> str | None:
    """Attempt to detect section headers in text."""
    lines = text.split("\n")[:5]  # Check first 5 lines

    for line in lines:
        line = line.strip()
        # Common header patterns
        if re.match(r"^\d+\.?\s+[A-Z]", line):  # "1. Introduction" or "1 METHODS"
            return line[:100]
        if re.match(r"^[A-Z][A-Z\s]{5,}$", line):  # "INTRODUCTION"
            return line[:100]
        if re.match(r"^(Chapter|Section)\s+\d+", line, re.IGNORECASE):
            return line[:100]

    return None


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping chunks, trying to break at sentence boundaries.
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If not at the end, try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            search_start = max(start + chunk_size - 100, start)
            search_region = text[search_start:end + 50]

            # Find last sentence boundary in search region
            best_break = None
            for pattern in [r"\.\s+", r"\?\s+", r"!\s+", r"\n\n"]:
                for match in re.finditer(pattern, search_region):
                    best_break = search_start + match.end()

            if best_break and best_break > start + chunk_size // 2:
                end = best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks


def process_pdf(
    pdf_path: str | Path,
    chunk_size: int = 500,
    overlap: int = 50,
) -> Iterator[PDFChunk]:
    """
    Process a PDF file into chunks with metadata.

    Args:
        pdf_path: Path to PDF file
        chunk_size: Target size for each chunk in characters
        overlap: Number of characters to overlap between chunks

    Yields:
        PDFChunk objects
    """
    pdf_path = Path(pdf_path)
    source = pdf_path.name
    pages = extract_text_from_pdf(pdf_path)

    chunk_id = 0
    current_section = None

    for page_num, page_text in pages:
        if not page_text.strip():
            continue

        # Try to detect section header
        detected = detect_section_header(page_text)
        if detected:
            current_section = detected

        # Chunk the page text
        chunks = chunk_text(page_text, chunk_size, overlap)

        for chunk_text_content in chunks:
            yield PDFChunk(
                text=chunk_text_content,
                source=source,
                page=page_num,
                chunk_id=chunk_id,
                section=current_section,
            )
            chunk_id += 1


def process_guidelines_directory(
    directory: str | Path,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[PDFChunk]:
    """
    Process all PDF files in a directory.

    Args:
        directory: Path to directory containing PDFs
        chunk_size: Target chunk size
        overlap: Chunk overlap

    Returns:
        List of all PDFChunk objects from all PDFs
    """
    directory = Path(directory)
    all_chunks = []

    for pdf_path in sorted(directory.glob("*.pdf")):
        print(f"Processing: {pdf_path.name}")
        chunks = list(process_pdf(pdf_path, chunk_size, overlap))
        all_chunks.extend(chunks)
        print(f"  -> {len(chunks)} chunks")

    return all_chunks
