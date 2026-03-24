import re
from io import BytesIO

from pypdf import PdfReader

from src.core.config import settings
from src.core.embeddings import embed_texts
from src.database.models import Document, Paragraph


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_pages_text(pdf_bytes: bytes) -> list[str]:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
    return pages


def chunk_text(pages: list[str], max_chars: int = 900) -> list[str]:
    merged = "\n\n".join(_normalize_whitespace(page) for page in pages if page and page.strip())
    if not merged:
        return []

    raw_parts = [part.strip() for part in re.split(r"\n\n+", merged) if part.strip()]
    if not raw_parts:
        raw_parts = [merged]

    chunks: list[str] = []
    current = ""
    for part in raw_parts:
        candidate = f"{current} {part}".strip() if current else part
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(part) <= max_chars:
            current = part
            continue

        start = 0
        while start < len(part):
            chunks.append(part[start:start + max_chars].strip())
            start += max_chars

    if current:
        chunks.append(current)

    return [chunk for chunk in chunks if chunk]


def index_document_bytes(db, document: Document, pdf_bytes: bytes) -> tuple[int, int]:
    pages = extract_pdf_pages_text(pdf_bytes)
    chunks = chunk_text(pages)

    db.query(Paragraph).filter(Paragraph.document_id == document.id).delete()

    if not chunks:
        document.page_count = len(pages)
        document.status = "ready"
        db.commit()
        return len(pages), 0

    vectors = embed_texts(chunks)

    if any(len(vector) != settings.embedding_dimensions for vector in vectors):
        raise ValueError("Embedding dimension mismatch during indexing")

    records = [
        Paragraph(
            document_id=document.id,
            text=chunk,
            chunk_index=index,
            embedding=vector,
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    db.add_all(records)

    document.page_count = len(pages)
    document.status = "ready"
    db.commit()

    return len(pages), len(chunks)
