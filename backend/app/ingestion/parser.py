from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


class DocumentParseError(Exception):
    """Raised when a document cannot be parsed."""


@dataclass(frozen=True)
class ParsedPage:
    """Text extracted from a single document page."""

    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    """Result of parsing a document."""

    file_path: str
    page_count: int
    pages: list[ParsedPage]


class PDFParser:
    """Extract text from PDF documents while preserving page boundaries."""

    def parse(self, file_path: str | Path) -> ParsedDocument:
        path = Path(file_path)

        if not path.exists():
            raise DocumentParseError(f"Document does not exist: {path}")

        if not path.is_file():
            raise DocumentParseError(f"Document is not a file: {path}")

        if path.suffix.lower() != ".pdf":
            raise DocumentParseError(
                f"Unsupported document type: {path.suffix or '<none>'}"
            )

        try:
            document = fitz.open(path)
        except Exception as exc:
            raise DocumentParseError(
                f"Unable to open PDF: {path}"
            ) from exc

        try:
            pages = [
                ParsedPage(
                    page_number=index + 1,
                    text=page.get_text("text"),
                )
                for index, page in enumerate(document)
            ]

            return ParsedDocument(
                file_path=str(path),
                page_count=len(pages),
                pages=pages,
            )
        finally:
            document.close()