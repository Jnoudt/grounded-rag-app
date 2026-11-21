from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from src.schemas.rag import ChunkOffset, DocumentChunk


def slugify_doc_name(doc_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", doc_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return slug or "document"


class DeterministicChunker:
    def __init__(
        self,
        chunk_size: int = 1200,
        overlap: int = 150,
        section: str | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.section = section

    def chunk(
        self,
        text: str,
        doc_slug: str,
        *,
        pages: Sequence[str] | None = None,
    ) -> list[DocumentChunk]:
        if not text and not pages:
            return []

        page_texts = list(pages) if pages is not None else [text]
        chunks: list[DocumentChunk] = []

        for page_number, page_text in enumerate(page_texts, start=1):
            cleaned = page_text.strip()
            if not cleaned:
                continue

            start = 0
            chunk_index = 1
            while start < len(cleaned):
                end = min(start + self.chunk_size, len(cleaned))
                if end < len(cleaned):
                    whitespace = cleaned.rfind(" ", start, end)
                    if whitespace > start:
                        end = whitespace

                chunk_text = cleaned[start:end].strip()
                if chunk_text:
                    chunk_id = f"{slugify_doc_name(doc_slug)}_p{page_number}_c{chunk_index}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            doc_slug=slugify_doc_name(doc_slug),
                            page_number=page_number,
                            section=self.section,
                            offsets=ChunkOffset(
                                start=start,
                                end=end,
                            ),
                            text=chunk_text,
                        )
                    )

                if end >= len(cleaned):
                    break
                start = max(start + 1, end - self.overlap)
                chunk_index += 1

        return chunks


def chunk_document(
    text: str,
    doc_name: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 150,
    section: str | None = None,
    pages: Sequence[str] | None = None,
) -> list[DocumentChunk]:
    chunker = DeterministicChunker(
        chunk_size=chunk_size,
        overlap=overlap,
        section=section,
    )
    return chunker.chunk(text=text, doc_slug=doc_name, pages=pages)
