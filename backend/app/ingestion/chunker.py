from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.parser import ParsedPage


@dataclass(frozen=True)
class DocumentChunk:
    """A retrieval-ready chunk with page provenance."""

    chunk_index: int
    text: str
    page_number: int
    start_char: int
    end_char: int


class DocumentChunker:
    """
    Deterministically split parsed pages into overlapping chunks.

    Chunking is performed per page so that page provenance is never lost.
    """

    def __init__(
        self,
        *,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, pages: list[ParsedPage]) -> list[DocumentChunk]:
        """Create deterministic chunks from parsed pages."""
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for page in pages:
            text = page.text.strip()

            if not text:
                continue

            page_chunks = self._chunk_page(
                text=text,
                page_number=page.page_number,
            )

            for chunk in page_chunks:
                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_index,
                        text=chunk.text,
                        page_number=chunk.page_number,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                    )
                )
                chunk_index += 1

        return chunks

    def _chunk_page(
        self,
        *,
        text: str,
        page_number: int,
    ) -> list[DocumentChunk]:
        if len(text) <= self.chunk_size:
            return [
                DocumentChunk(
                    chunk_index=0,
                    text=text,
                    page_number=page_number,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        chunks: list[DocumentChunk] = []

        start = 0
        local_index = 0

        while start < len(text):
            end = min(
                start + self.chunk_size,
                len(text),
            )

            if end < len(text):
                boundary = self._find_boundary(
                    text,
                    start,
                    end,
                )

                if boundary > start:
                    end = boundary

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        chunk_index=local_index,
                        text=chunk_text,
                        page_number=page_number,
                        start_char=start,
                        end_char=end,
                    )
                )

                local_index += 1

            if end >= len(text):
                break

            next_start = end - self.chunk_overlap

            if next_start <= start:
                next_start = end

            start = next_start

        return chunks

    @staticmethod
    def _find_boundary(
        text: str,
        start: int,
        end: int,
    ) -> int:
        """
        Prefer natural boundaries.

        Priority:
        1. Paragraph boundary
        2. Newline
        3. Sentence boundary
        4. Word boundary
        """
        window = text[start:end]

        paragraph_boundary = window.rfind("\n\n")

        if paragraph_boundary > 0:
            return start + paragraph_boundary + 2

        newline_boundary = window.rfind("\n")

        if newline_boundary > 0:
            return start + newline_boundary + 1

        sentence_boundary = max(
            window.rfind(". "),
            window.rfind("? "),
            window.rfind("! "),
        )

        if sentence_boundary > 0:
            return start + sentence_boundary + 2

        word_boundary = window.rfind(" ")

        if word_boundary > 0:
            return start + word_boundary

        return end